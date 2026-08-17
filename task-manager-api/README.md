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
- **`POST /login` devolve um `token` de verdade.** O valor anterior era `'fake-jwt-token-<id>'`,
  previsível e que nenhuma rota verificava; agora é assinado, expira e é exigido pelas rotas protegidas.
- **Senhas passam a usar hash com salt** (era MD5 puro). As credenciais antigas continuam funcionando:
  o login detecta o formato legado e regrava no formato novo.
- **Erros seguem um formato único** (`{"error": "..."}`), produzido pelo error handler central.

## Autenticação

18 das 22 rotas **exigem credencial**, e não há configuração que desligue a verificação — a versão
anterior desta refatoração deixava os decorators atrás de `AUTH_ENABLED=false`, o que na prática
mantinha a API aberta.

`POST /login` devolve um token assinado com HMAC-SHA256 sobre a `SECRET_KEY` (`middlewares/auth.py`,
sem dependência nova). Envie-o em `Authorization: Bearer <token>`.

```bash
TOKEN=$(curl -s -X POST localhost:5000/login \
        -H 'Content-Type: application/json' \
        -d '{"email":"joao@email.com","password":"1234"}' | jq -r .token)

curl localhost:5000/reports/summary -H "Authorization: Bearer $TOKEN"
```

| Acesso | Endpoints |
|---|---|
| Público | `GET /`, `GET /health`, `POST /login`, `POST /users` |
| Autenticado | todo o `/tasks*`, `GET/PUT /users/<id>`, `GET /users/<id>/tasks`, `GET /categories` |
| `admin` ou `manager` | `POST/PUT/DELETE /categories`, `GET /reports/summary`, `GET /reports/user/<id>` |
| `admin` | `GET /users`, `DELETE /users/<id>` |

Sem credencial essas rotas respondem **401**; com papel insuficiente, **403**. É aqui que a coluna
`role` — presente no schema desde o início e nunca consultada — passa a ter efeito.

Fora de escopo, e registrados no relatório: revogação de token, refresh token e autorização por dono do
recurso (hoje qualquer usuário autenticado edita qualquer task).
