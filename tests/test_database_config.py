import unittest

from sqlalchemy import create_engine

from app.config import database_uri


class DatabaseConfigTest(unittest.TestCase):
    def test_railway_urls_load_installed_driver_without_connecting(self):
        for scheme in ("postgres", "postgresql"):
            with self.subTest(scheme=scheme):
                # Keep escaped credentials, port and connection options intact.
                suffix = "user:p%40ss@localhost:5432/news?sslmode=require"
                uri = database_uri(f"{scheme}://{suffix}")
                self.assertEqual(uri, f"postgresql+psycopg2://{suffix}")
                engine = create_engine(uri)
                self.assertEqual(engine.dialect.driver, "psycopg2")
                self.assertEqual(engine.dialect.dbapi.__name__, "psycopg2")
                engine.dispose()

    def test_sqlite_and_explicit_drivers_are_preserved(self):
        for uri in ("sqlite://", "sqlite:///dev.db", "postgresql+psycopg2://user@localhost/news", "postgresql+psycopg://user@localhost/news"):
            with self.subTest(uri=uri):
                self.assertEqual(database_uri(uri), uri)


if __name__ == "__main__":
    unittest.main()
