import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

from flask import template_rendered
from bs4 import BeautifulSoup
from app import create_app
from app.config import Config
from app.models import db, Category, Post, SiteSetting, User


@contextmanager
def rendered_context(app):
    contexts = []
    def record(sender, template, context, **extra):
        contexts.append(context)
    template_rendered.connect(record, app)
    try:
        yield contexts
    finally:
        template_rendered.disconnect(record, app)


class HomeCalendarTest(unittest.TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        with patch.multiple(Config, SQLALCHEMY_DATABASE_URI='sqlite://', MEDIA_ROOT=self.media.name, AUTO_SYNC_INTERVAL=0):
            self.app = create_app()
        self.app.config.update(TESTING=True, SECRET_KEY='calendar-test-only')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.session.execute(db.text('DELETE FROM post_categories'))
        Post.query.delete()
        db.session.commit()
        self.today = datetime(2026, 10, 2, 13, 0)
        self.clock = patch('app.routes._now_brazil', return_value=self.today)
        self.admin_clock = patch('app.admin._now_brazil', return_value=self.today)
        self.clock.start()
        self.admin_clock.start()
        categories = Category.query.limit(3).all()
        # Enough old items to exercise hero, queue, latest and lower category sections.
        for i in range(24):
            item = Post(title=f'Antiga {i}', slug=f'antiga-{i}', published_at=datetime(2026, 9, 8, 23, 59, 59, 999999)-timedelta(hours=i), categories=[categories[i % 3]])
            db.session.add(item)
        for slug, published in [('posterior', datetime(2026, 9, 9)), ('atual', self.today-timedelta(minutes=1)), ('agendada', self.today+timedelta(hours=1)), ('rascunho', None)]:
            db.session.add(Post(title=slug, slug=slug, published_at=published, categories=categories))
        db.session.commit()
        self.client = self.app.test_client()
        self.admin_id = User.query.filter_by(is_admin=True).first().id

    def tearDown(self):
        self.clock.stop()
        self.admin_clock.stop()
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self.media.cleanup()

    def login(self, user_id=None):
        with self.client.session_transaction() as session:
            session['_user_id'] = str(user_id or self.admin_id)
            session['_fresh'] = True

    def submit(self, data):
        response = self.client.get('/admin/calendario-home')
        token = BeautifulSoup(response.data, 'html.parser').find('input', {'name': 'csrf_token'})['value']
        return self.client.post('/admin/calendario-home', data={'csrf_token': token, **data})

    def set_mode(self, enabled, day='2026-09-08'):
        SiteSetting.query.filter_by(key='home_calendar_enabled').first().value = enabled
        SiteSetting.query.filter_by(key='home_calendar_date').first().value = day
        db.session.commit()

    def test_all_home_sections_and_rendered_links_respect_day_end(self):
        self.set_mode('1')
        with rendered_context(self.app) as contexts:
            response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        context = contexts[-1]
        self.assertEqual(context['lead_post'].slug, 'antiga-0')
        self.assertTrue(context['category_sections'])
        posts = [context['lead_post']]
        for key in ['latest', 'latest_queue', 'brasil_posts', 'selected_posts', 'popular_posts']:
            posts.extend(context[key])
        for section in context['category_sections']:
            posts.extend(section['posts'])
        cutoff = datetime(2026, 9, 8, 23, 59, 59, 999999)
        self.assertTrue(all(post.published_at <= cutoff for post in posts))
        links = [a['href'] for a in BeautifulSoup(response.data, 'html.parser').select('a[href^="/p/"]')]
        self.assertTrue(links)
        self.assertTrue(all('/p/antiga-' in link for link in links))
        # Public article and search routes remain accessible.
        self.assertEqual(self.client.get('/p/posterior').status_code, 200)
        self.assertIn(b'/p/posterior', self.client.get('/buscar?q=posterior').data)

    def test_enable_persists_for_public_visitors_and_disable_restores_latest(self):
        self.login()
        self.assertEqual(self.submit({'home_calendar_enabled': 'y', 'home_calendar_date': '2026-09-08'}).status_code, 302)
        public = self.app.test_client()
        self.assertNotIn(b'/p/atual', public.get('/').data)
        # Dedicated disable button needs no date and retains the previous selection.
        self.assertEqual(self.submit({}).status_code, 302)
        html = public.get('/').data
        self.assertIn(b'/p/atual', html)
        self.assertNotIn(b'/p/agendada', html)
        self.assertNotIn(b'/p/rascunho', html)
        self.assertEqual(SiteSetting.query.filter_by(key='home_calendar_date').first().value, '2026-09-08')

    def test_invalid_missing_future_dates_and_csrf_do_not_change_saved_settings(self):
        self.login()
        for day in ['2026-02-30', '', '2026-10-03']:
            response = self.submit({'home_calendar_enabled': 'y', 'home_calendar_date': day})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(SiteSetting.query.filter_by(key='home_calendar_enabled').first().value, '0')
        response = self.client.post('/admin/calendario-home', data={'home_calendar_enabled': 'y', 'home_calendar_date': '2026-09-08'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(SiteSetting.query.filter_by(key='home_calendar_enabled').first().value, '0')

    def test_only_admin_can_change_calendar(self):
        self.assertEqual(self.client.get('/admin/calendario-home').status_code, 302)
        self.assertEqual(self.client.post('/admin/calendario-home').status_code, 302)
        user = User(email='editor@example.test', password_hash='unused', is_admin=False)
        db.session.add(user)
        db.session.commit()
        self.login(user.id)
        self.assertEqual(self.client.post('/admin/calendario-home', data={'home_calendar_enabled': 'y', 'home_calendar_date': '2026-09-08'}).status_code, 302)
        self.assertEqual(SiteSetting.query.filter_by(key='home_calendar_enabled').first().value, '0')

    def test_empty_history_and_corrupt_setting_are_safe(self):
        self.set_mode('1', '2000-01-01')
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'/p/', response.data)
        self.set_mode('1', 'invalid')
        self.assertIn(b'/p/atual', self.client.get('/').data)

    def test_today_does_not_reveal_scheduled_posts(self):
        self.set_mode('1', '2026-10-02')
        html = self.client.get('/').data
        self.assertIn(b'/p/atual', html)
        self.assertNotIn(b'/p/agendada', html)


if __name__ == '__main__':
    unittest.main()
