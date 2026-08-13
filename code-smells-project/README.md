# code-smells-project

API de E-commerce em Python/Flask. Projeto refatorado para MVC pela skill `refactor-arch`
(relatório da auditoria em [`../reports/audit-project-1.md`](../reports/audit-project-1.md)).

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env          # ajuste SECRET_KEY antes de usar em qualquer ambiente real
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000` (configurável por `HOST`/`PORT`). O banco SQLite
(`loja.db`) é criado na inicialização, já com produtos e usuários de exemplo — as senhas de
exemplo são gravadas com hash.

Sem um `.env`, a aplicação roda com padrões de desenvolvimento e gera uma `SECRET_KEY` efêmera
por boot, registrando um aviso no log.

## Estrutura

```
app.py                        composition root — cria a app, liga as camadas
scripts/reset_db.py           reset do banco (substitui o antigo POST /admin/reset-db)
src/
├── config/                   settings (env) e logging
├── database/                 conexão por requisição, schema e carga inicial
├── models/                   acesso a dados por domínio, queries parametrizadas
├── controllers/              regras de negócio e orquestração
├── views/                    blueprints + DTOs de saída
├── validators/               validação de entrada compartilhada entre POST e PUT
├── services/                 efeitos colaterais (notificações) atrás de interface
├── middlewares/              exceções de domínio, error handler, ponto de extensão de auth
└── constants.py              constantes de domínio
```

O fluxo é `views → controllers → models`: rotas não contêm SQL nem regra de negócio, controllers
não conhecem HTTP, models não montam resposta.

## Endpoints

| Método | Path | Descrição |
|---|---|---|
| GET | `/` | índice da API |
| GET | `/health` | status e contagens |
| GET | `/produtos` | lista produtos (`?limit=&offset=`) |
| GET | `/produtos/busca` | busca (`?q=&categoria=&preco_min=&preco_max=`) |
| GET | `/produtos/<id>` | detalhe |
| POST | `/produtos` | cria |
| PUT | `/produtos/<id>` | atualiza |
| DELETE | `/produtos/<id>` | remove |
| GET | `/usuarios` | lista usuários (sem expor senha) |
| GET | `/usuarios/<id>` | detalhe |
| POST | `/usuarios` | cria |
| POST | `/login` | autentica |
| POST | `/pedidos` | cria pedido (transacional, com baixa de estoque) |
| GET | `/pedidos` | lista pedidos com itens |
| GET | `/pedidos/usuario/<id>` | pedidos de um usuário |
| PUT | `/pedidos/<id>/status` | altera status |
| GET | `/relatorios/vendas` | relatório consolidado |

### Removidos na refatoração

- `POST /admin/query` — executava SQL arbitrário vindo do corpo da requisição, sem autenticação.
- `POST /admin/reset-db` — apagava todas as tabelas sem autenticação. Substituído por
  `python scripts/reset_db.py --confirmar`.

## Autenticação

A API não possui autenticação — isso já era verdade antes da refatoração e implementá-la é
funcionalidade nova, não refatoração. O que existe é o ponto de extensão pronto em
`src/middlewares/auth.py` (`@requer_autenticacao`, `@requer_papel`), inativo enquanto
`AUTH_ENABLED=false`.
