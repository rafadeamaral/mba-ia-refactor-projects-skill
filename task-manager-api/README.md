# task-manager-api

API de Task Manager em Python/Flask + SQLAlchemy. Projeto refatorado para MVC pela skill
`refactor-arch` (relatório da auditoria em [`../reports/audit-project-3.md`](../reports/audit-project-3.md)).

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env          # ajuste SECRET_KEY antes de usar em qualquer ambiente real
python scripts/init_db.py     # cria o schema (antes acontecia sozinho, no import)
python seed.py                # opcional: popula com dados de exemplo
python app.py
```

A API sobe em `http://127.0.0.1:5000` (configurável por `HOST`/`PORT`).

## Estrutura

O projeto já vinha com `models/`, `routes/`, `services/` e `utils/` — a refatoração **manteve essa
árvore** e adicionou as camadas que faltavam, em vez de renomear o que já existia.

```
app.py                     composition root — create_app() + init_schema()
scripts/init_db.py         criação de schema explícita
seed.py                    carga de exemplo (usa a factory)
config/                    NOVO — settings (env) e logging
models/                    entidades e regras de domínio (sem serialização)
controllers/               NOVO — fluxo dos casos de uso
routes/                    handlers finos
├── dto/                   NOVO — serialização de saída com allowlist
├── task_routes.py
├── user_routes.py
├── category_routes.py     NOVO — extraído de report_routes
├── report_routes.py
└── system_routes.py       NOVO — / e /health
validators/                NOVO — validação compartilhada entre POST e PUT
services/                  notificações, com remetente injetado
middlewares/               NOVO — exceções de domínio, error handler, auth
utils/                     helpers efetivamente usados + datetime_utils
```

O fluxo é `routes → controllers → models`. Nenhum handler passa de 12 linhas; antes o maior tinha 90.

## Endpoints

Os 22 endpoints originais foram preservados.

| Método | Path | | Método | Path |
|---|---|---|---|---|
| GET | `/` | | GET | `/users` |
| GET | `/health` | | GET | `/users/<id>` |
| GET | `/tasks` | | POST | `/users` |
| GET | `/tasks/<id>` | | PUT | `/users/<id>` |
| POST | `/tasks` | | DELETE | `/users/<id>` |
| PUT | `/tasks/<id>` | | GET | `/users/<id>/tasks` |
| DELETE | `/tasks/<id>` | | POST | `/login` |
| GET | `/tasks/search` | | GET | `/reports/summary` |
| GET | `/tasks/stats` | | GET | `/reports/user/<id>` |
| GET | `/categories` | | POST | `/categories` |
| PUT | `/categories/<id>` | | DELETE | `/categories/<id>` |

As listagens aceitam `?limit=` e `?offset=` (padrão 50, teto 200).

### Mudanças de comportamento

- **`password` não aparece mais em nenhuma resposta.** Era devolvido em `GET /users/<id>`,
  `POST /users`, `PUT /users/<id>` e no login, porque a serialização vinha do `to_dict()` do model.
- **`POST /login` não devolve mais `token`.** O valor era `'fake-jwt-token-<id>'` e nenhuma rota o
  verificava — devolver credencial simulada é pior que não devolver nenhuma.
- **Senhas passam a usar hash com salt** (era MD5 puro). As credenciais antigas continuam funcionando:
  o login detecta o formato legado e regrava no formato novo.
- **Erros seguem um formato único** (`{"error": "..."}`), produzido pelo error handler central.

## Autenticação

A API não possui autenticação — isso já era verdade antes, e implementá-la é funcionalidade nova. O
ponto de extensão está pronto em `middlewares/auth.py` (`@requer_autenticacao`, `@requer_papel`),
inativo enquanto `AUTH_ENABLED=false`.
