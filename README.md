# Fronteira 360 Oeste

Portal de notícias em Flask pronto para implantação em um novo projeto do Railway.

## Implantação

1. Crie um repositório novo no GitHub e envie todo o conteúdo desta pasta.
2. No Railway, crie um projeto a partir do repositório.
3. Adicione um PostgreSQL e configure `DATABASE_URL` com a referência fornecida pelo Railway.
4. Configure `SECRET_KEY` com uma chave forte.
5. Para uploads persistentes, monte um volume em `/data` (o projeto usa `/data/uploads`).
6. O comando de inicialização já está definido no `Procfile`.

## Primeiro acesso ao painel

- URL: `/admin/login`
- E-mail: `admin@admin.com`
- Senha: `senha123`

Altere a senha no painel logo após o primeiro acesso.

## Publicidade configurada

- Cabeçalho: 728 × 90 px
- Após a manchete principal: 728 × 180 px
- Centro da home: 970 × 180 px
- Final das matérias: 970 × 180 px
- Laterais internas: 460 × 320 px

O painel aceita múltiplos banners por posição e faz rotação automática.

## Conteúdo inicial

Em uma instalação com banco vazio, o sistema cria automaticamente categorias e matérias iniciais recentes para a home não ficar vazia. Elas podem ser editadas ou removidas normalmente no painel.

## Calendário Home

No painel, abra **Calendário Home** (`/admin/calendario-home`), escolha a data, marque **Ativar Calendário Home** e salve. A home pública inteira passa a selecionar matérias publicadas até o fim desse dia (horário de Brasília), incluindo dias anteriores, da mais recente para a mais antiga. Destaques, últimas notícias e blocos por categoria respeitam o mesmo limite.

Para restaurar a home atual, use **Desativar e voltar às notícias atuais**, ou desmarque a ativação e salve. O controle é exclusivo de administradores e afeta todos os visitantes da home; matérias individuais, busca e páginas de categoria continuam funcionando normalmente.

O calendário filtra as publicações existentes; não restaura versões antigas de textos, banners, layout, cotação ou previsão do tempo. Não exige migração de tabelas: as configurações usam `SiteSetting`, com o recurso desativado por padrão.

Teste de regressão: `python -m unittest discover -s tests -v`.
