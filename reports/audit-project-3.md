```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.12.0
Framework:     Flask 3.0.0
Dependencies:  flask-sqlalchemy 3.1.1, sqlalchemy 2.0.52, flask-cors 4.0.0,
               marshmallow 3.20.1 (declarada, nunca importada),
               python-dotenv 1.0.0 (declarada, nunca importada)
Domain:        API de Task Manager (tasks, users, categories, relatórios de produtividade)
Architecture:  Separação NOMINAL — existem models/, routes/, services/ e utils/, mas as
               responsabilidades vazam entre elas; services/ e metade de utils/ são código morto
Source files:  15 files analyzed | ~1.158 lines of code
Persistence:   SQLite via Flask-SQLAlchemy (ORM)
DB tables:     tasks, users, categories
Endpoints:     22 endpoints mapeados
================================
```

### Inventário de endpoints — contrato a preservar

| # | Método | Path | Handler | Observação |
|---|---|---|---|---|
| 1 | GET | `/` | `app.py:27` `index` | |
| 2 | GET | `/health` | `app.py:23` `health` | |
| 3 | GET | `/tasks` | `tasks.get_tasks` | N+1; sem paginação |
| 4 | GET | `/tasks/<id>` | `tasks.get_task` | |
| 5 | POST | `/tasks` | `tasks.create_task` | handler de 70 linhas |
| 6 | PUT | `/tasks/<id>` | `tasks.update_task` | validação duplicada do POST |
| 7 | DELETE | `/tasks/<id>` | `tasks.delete_task` | |
| 8 | GET | `/tasks/search` | `tasks.search_tasks` | |
| 9 | GET | `/tasks/stats` | `tasks.task_stats` | |
| 10 | GET | `/users` | `users.get_users` | |
| 11 | GET | `/users/<id>` | `users.get_user` | **devolve hash da senha** |
| 12 | POST | `/users` | `users.create_user` | **devolve hash da senha** |
| 13 | PUT | `/users/<id>` | `users.update_user` | **devolve hash da senha** |
| 14 | DELETE | `/users/<id>` | `users.delete_user` | apaga tasks em laço |
| 15 | GET | `/users/<id>/tasks` | `users.get_user_tasks` | |
| 16 | POST | `/login` | `users.login` | **token falso; devolve hash da senha** |
| 17 | GET | `/reports/summary` | `reports.summary_report` | 12 COUNT + N+1 |
| 18 | GET | `/reports/user/<id>` | `reports.user_report` | |
| 19 | GET | `/categories` | `reports.get_categories` | **CRUD de categoria no blueprint de relatórios** |
| 20 | POST | `/categories` | `reports.create_category` | idem |
| 21 | PUT | `/categories/<id>` | `reports.update_category` | idem |
| 22 | DELETE | `/categories/<id>` | `reports.delete_category` | idem |

> **Observação da Fase 1:** o simples `import app` para inventariar as rotas **criou o arquivo
> `instance/tasks.db`**. A criação do schema é efeito colateral do import (`app.py:30-31`), não de um
> comando de inicialização — ver finding #7.

---

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: task-manager-api
Stack:   Python 3.12 + Flask 3.0 + SQLAlchemy 2.0
Files:   15 analyzed | ~1.158 lines of code
Date:    2026-08-13
```

## Summary

**CRITICAL: 4 | HIGH: 5 | MEDIUM: 9 | LOW: 6**

Este projeto é o caso mais enganoso dos três: ele **parece** organizado. Tem `models/`, `routes/`,
`services/` e `utils/` — e ainda assim viola MVC de ponta a ponta. As rotas concentram validação, regra
de negócio, acesso a dados e serialização em funções de até 90 linhas; `services/` não é importado por
nenhum arquivo; e três implementações da mesma regra de negócio convivem, sendo que a "oficial" (o
método do model) é justamente a que ninguém chama. A separação existe no sistema de arquivos, não no
fluxo de execução. Sobre isso, a camada de dados devolve o hash da senha diretamente na resposta HTTP —
consequência direta de não haver fronteira entre model e apresentação.

## Findings

### #1 [CRITICAL] Hash de senha vazado na resposta da API (SEC-04)
**File:** `models/user.py:16-25` (`to_dict`), servido em `routes/user_routes.py:33,85-86,129,209`
**Description:** `User.to_dict()` inclui `'password': self.password` e é o serializador usado em
`GET /users/<id>`, na resposta de `POST /users`, na de `PUT /users/<id>` e no payload de **login**.
**Impact:** Qualquer visitante anônimo obtém o hash de qualquer usuário — e, como o hash é MD5 sem salt
(finding #2), quebrá-lo offline é questão de segundos. É o exemplo mais claro do custo de não separar
model de apresentação: o campo vaza porque a serialização mora na camada de persistência.
**Recommendation:** DTO de saída com allowlist de campos, na camada de views. (RF-04)

### #2 [CRITICAL] Senhas com MD5 e sem salt (SEC-03)
**File:** `models/user.py:29,32`
**Description:** `hashlib.md5(pwd.encode()).hexdigest()` em `set_password` e `check_password`. Nenhum
salt, nenhum fator de custo.
**Impact:** MD5 é criptograficamente quebrado e extremamente rápido — GPUs comuns testam bilhões de
hashes por segundo. Sem salt, uma única rainbow table reverte todas as senhas de uma vez. O mínimo
exigido é de 4 caracteres (`routes/user_routes.py:64`), o que torna o espaço de busca exaurível em
segundos mesmo sem tabela.
**Recommendation:** `werkzeug.security` (já disponível via Flask) com re-hash no login para a base
existente. (RF-03)

### #3 [CRITICAL] Autenticação simulada; API inteiramente aberta (SEC-06)
**File:** `routes/user_routes.py:210`; ausência de verificação em todas as 22 rotas
**Description:** O login devolve `'token': 'fake-jwt-token-' + str(user.id)` — previsível, não assinado
— e **nenhuma rota verifica qualquer token**. O controle de papel existe modelado
(`User.is_admin()`, `models/user.py:34`) e nunca é invocado.
**Impact:** `DELETE /users/<id>`, `PUT /tasks/<id>`, `/reports/summary` e o CRUD de categorias são
acessíveis anonimamente. A autorização foi projetada e não implementada.
**Recommendation:** Substituir o token falso por uma credencial verificável emitida no login, e exigi-la
nas rotas protegidas com a guarda ativa por padrão. O campo `role`, hoje decorativo, passa a decidir o
acesso às rotas administrativas e de gestão. Emitir e verificar credencial com biblioteca padrão é
correção deste achado, não funcionalidade nova. (RF-19, caso A)

### #4 [CRITICAL] Segredos hardcoded (SEC-01)
**File:** `app.py:13`, `services/notification_service.py:7-10`
**Description:** `app.config['SECRET_KEY'] = 'super-secret-key-123'` e, no serviço de notificação, host,
usuário e senha de SMTP (`'senha123'`) fixos no construtor. O `python-dotenv` está no
`requirements.txt` (linha 6) e nunca é importado.
**Impact:** Segredos versionados permanecem no histórico do Git. Agravante: o `NotificationService`
é código morto (finding #6) — são credenciais expostas sem sequer entregar funcionalidade.
**Recommendation:** Módulo `config/` lendo do ambiente com `.env.example` versionado; a infraestrutura
para isso já é dependência declarada do projeto. (RF-01)

### #5 [HIGH] Camada nominal: rotas como god-functions (ARCH-11)
**File:** `routes/task_routes.py:11-299`, `routes/user_routes.py:10-211`, `routes/report_routes.py:12-223`
**Description:** Existe `routes/`, mas cada handler acumula quatro responsabilidades. `create_task`
(`task_routes.py:85-154`) faz parsing do request, 8 validações de negócio, 2 consultas de integridade
referencial, construção da entidade, persistência com `db.session` e serialização — 70 linhas.
`summary_report` (`report_routes.py:12-101`) tem 90 linhas de agregação estatística dentro do handler
HTTP. Não existe camada de controller/service em uso.
**Impact:** É o achado central: ter pastas de camada não é ter camadas. A regra de negócio está
inacessível fora do contexto HTTP — calcular estatísticas de produtividade em um job noturno exigiria
simular um request. Nenhuma das regras é testável sem subir Flask.
**Recommendation:** Extrair `controllers/` com o fluxo de cada caso de uso; handlers ficam com 3-5
linhas. **Manter a árvore `routes/`/`models/`/`services/` existente** — o projeto já usa essa
convenção e renomeá-la custaria mais do que entrega. (RF-06, RF-07)

### #6 [HIGH] Abstração morta: a camada correta existe e ninguém usa (ARCH-12)
**File:** `models/task.py:50-60`, `utils/helpers.py:31-108,110-116`, `services/notification_service.py:1-48`
**Description:** Verificação por busca de referências em todo o projeto:

| Símbolo | Onde está | Referências |
|---|---|---|
| `Task.is_overdue()` | `models/task.py:50-60` | **0** — a mesma regra é reescrita 6× nas rotas |
| `process_task_data()` | `utils/helpers.py:57-108` | **0** — reimplementa toda a validação de task |
| `NotificationService` | `services/notification_service.py` | **0** — o pacote `services/` não é importado por ninguém |
| `sanitize_string`, `generate_id`, `log_action`, `is_valid_color`, `validate_email` | `utils/helpers.py` | **0** |
| `VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR` | `utils/helpers.py:110-116` | **0** — as rotas repetem os literais |
| `format_date`, `calculate_percentage` | `utils/helpers.py:9-17` | importados em `report_routes.py:7`, **nunca chamados** |
| `marshmallow`, `python-dotenv` | `requirements.txt:4,6` | **0** imports |

**Impact:** Código morto aqui não é sujeira, é diagnóstico: a camada certa foi projetada e o fluxo real
a ignorou. Existem três implementações concorrentes da validação de task e duas do cálculo de
"atrasada", e as versões "oficiais" são exatamente as que ninguém executa.
**Recommendation:** Para cada símbolo, decidir explicitamente: adotar (é a implementação correta e as
cópias somem) ou remover. Nunca manter as duas. (RF-14)

### #7 [HIGH] Configuração e `db.create_all()` como efeito colateral do import (ARCH-07)
**File:** `app.py:9-31`
**Description:** A configuração é inline no módulo (sem factory `create_app`) e
`with app.app_context(): db.create_all()` roda **no import** (`:30-31`).
**Impact:** Verificado na prática durante a Fase 1: um `import app` para listar as rotas criou o arquivo
`instance/tasks.db`. `seed.py:2` importa `app` e sofre o mesmo efeito. Não há como instanciar a
aplicação com banco de teste sem editar o arquivo de produção — é a ausência do composition root.
**Recommendation:** `create_app(config)` como factory; criação de schema em comando explícito. (RF-08)

### #8 [HIGH] `except:` nu engolindo qualquer exceção (QUAL-03)
**File:** `routes/task_routes.py:62,137,204,236`; `routes/user_routes.py:130,149`;
`routes/report_routes.py:186,221`; `utils/helpers.py:46-50` — 12 ocorrências
**Description:** `except:` sem tipo, descartando a exceção original. `get_tasks`
(`task_routes.py:62`) converte qualquer erro em `{'error': 'Erro interno'}` sem log.
**Impact:** `except:` nu captura também `KeyboardInterrupt` e `SystemExit`. Um `AttributeError`
introduzido por refatoração vira 500 silencioso e passa despercebido em produção indefinidamente —
exatamente o cenário em que se está prestes a entrar ao reestruturar este projeto.
**Recommendation:** Exceções de domínio + `@app.errorhandler` central com log da causa. (RF-09)

### #9 [HIGH] Debug ligado e bind em todas as interfaces (SEC-07)
**File:** `app.py:34`
**Description:** `app.run(debug=True, host='0.0.0.0', port=5000)`.
**Impact:** O debugger do Werkzeug expõe console Python interativo na página de erro; combinado com
`0.0.0.0`, fica acessível fora da máquina local.
**Recommendation:** Ambos vindos de configuração, com default seguro. (RF-01)

### #10 [MEDIUM] Consultas N+1 (PERF-01)
**File:** `routes/task_routes.py:42,51`; `routes/report_routes.py:56,163`
**Description:** Em `get_tasks`, dentro do laço de tasks, um `User.query.get()` e um
`Category.query.get()` por task. Em `summary_report`, um `Task.query.filter_by(user_id=...)` por
usuário. Em `get_categories`, um `COUNT` por categoria.
**Impact:** 50 tasks disparam 101 queries onde `joinedload` resolveria em 1. O relatório combina o N+1
com a materialização de todas as tasks (finding #12).
**Recommendation:** `joinedload` para os relacionamentos e `GROUP BY` para as contagens. (RF-11)

### #11 [MEDIUM] Regra de negócio duplicada 6× (QUAL-01)
**File:** `routes/task_routes.py:30-39,71-80,283-287`; `routes/user_routes.py:171-180`;
`routes/report_routes.py:33-37,132-135`
**Description:** O cálculo de "task atrasada" — o mesmo `if` triplo aninhado — aparece em seis lugares,
enquanto `Task.is_overdue()` existe e nunca é chamado. A serialização de task também é reescrita à mão
em `task_routes.py:17-28` e `user_routes.py:162-169`, apesar de `to_dict()` existir.
**Impact:** Mudar a definição de "atrasada" exige encontrar seis cópias. Já há divergência de contrato:
`/tasks` inclui `user_name` e `category_name`, `/users/<id>/tasks` não.
**Recommendation:** Adotar `Task.is_overdue` como fonte única e serializar por DTO. (RF-14, RF-04)

### #12 [MEDIUM] Ausência de paginação (PERF-02)
**File:** `routes/task_routes.py:14,281`; `routes/user_routes.py:13`; `routes/report_routes.py:30,53,56`
**Description:** `Task.query.all()`, `User.query.all()` e `Category.query.all()` sem `LIMIT` nas rotas
de listagem; `summary_report` materializa todas as tasks **e** todos os usuários com suas tasks.
**Impact:** Consumo de memória e tempo de resposta crescem linearmente até o timeout.
**Recommendation:** `limit`/`offset` com teto defensivo. (RF-12)

### #13 [MEDIUM] API deprecated: `Model.query.get()` (DEP-02)
**File:** `routes/task_routes.py:67,117,122,158,188,195,227`; `routes/user_routes.py:29,95,136,155`;
`routes/report_routes.py:105,192,213` — 16 ocorrências
**Description:** `Query.get()` é legado no SQLAlchemy 2.0 e emite `LegacyAPIWarning`. O padrão
`Model.query` como um todo é legado em favor de `db.session.execute(db.select(...))`.
**Impact:** O projeto já roda SQLAlchemy 2.0.52 — está acumulando dívida que quebra na próxima major.
**Recommendation:** `db.session.get(Model, id)`. (RF-16)

### #14 [MEDIUM] Validação duplicada entre POST e PUT (QUAL-02)
**File:** `routes/task_routes.py:96-124` vs `166-198`; `routes/user_routes.py:54-72` vs `102-125`
**Description:** As mesmas regras (tamanho do título, status válido, faixa de prioridade, formato de
e-mail, role válido) escritas duas vezes por recurso. `marshmallow` está declarado no
`requirements.txt` e nunca é importado; `process_task_data()` faz o mesmo trabalho e é código morto.
**Impact:** Três implementações concorrentes da mesma validação, duas delas mortas — a divergência é
questão de tempo.
**Recommendation:** Camada `validators/` compartilhada entre criação e atualização. (RF-13)

### #15 [MEDIUM] 12 queries `COUNT` sequenciais em um único relatório (PERF-03)
**File:** `routes/report_routes.py:15-28`
**Description:** Três contagens de totais, quatro por status e cinco por prioridade — todas variando
apenas a cláusula `WHERE`.
**Impact:** Doze round-trips onde dois `GROUP BY` resolveriam.
**Recommendation:** Agregação com `GROUP BY`. (RF-11)

### #16 [MEDIUM] Blueprint com responsabilidade misturada (ARCH-11)
**File:** `routes/report_routes.py:157-223`
**Description:** O CRUD completo de `/categories` (4 rotas) mora dentro do blueprint de relatórios.
**Impact:** A fronteira de módulo não corresponde ao domínio — sintoma de organização por conveniência
de arquivo, não por recurso. Procurar "onde se cria uma categoria" leva ao arquivo errado.
**Recommendation:** `category_routes.py` próprio. Os paths não mudam. (RF-07)

### #17 [MEDIUM] Tratamento de erro não centralizado (ARCH-10)
**File:** todos os arquivos de `routes/` — 12 blocos `try/except`
**Description:** Cada handler repete o próprio `try/except` devolvendo mensagem genérica; não há
`@app.errorhandler` nem handler 404/500 global.
**Impact:** Boilerplate em todo handler e nenhum ponto único para logar ou padronizar a resposta.
**Recommendation:** Error handler central + exceções de domínio. (RF-09)

### #18 [MEDIUM] Deleção manual de dependentes sem cascade (PERF-05)
**File:** `routes/user_routes.py:140-142`
**Description:** `delete_user` busca as tasks do usuário e as apaga em laço na camada de aplicação. O
relacionamento (`models/task.py:20`) não declara `cascade`.
**Impact:** Regra de integridade implementada na aplicação em vez do schema — qualquer outro caminho de
deleção (script, shell do ORM) deixa tasks órfãs. O laço também não está em transação explícita.
**Recommendation:** `cascade='all, delete-orphan'` no relacionamento. (RF-10)

### #19 [MEDIUM] Serviço de notificação com I/O bloqueante e sem tratamento (ARCH-06)
**File:** `services/notification_service.py:12-25`
**Description:** `send_email` abre conexão SMTP síncrona dentro do fluxo, com credenciais hardcoded, e
captura qualquer exceção devolvendo `False`. As notificações são acumuladas em `self.notifications`,
uma lista em memória que só cresce.
**Impact:** Se fosse chamado — não é (finding #6) — bloquearia a requisição pelo tempo do handshake SMTP
e vazaria memória.
**Recommendation:** Adotar o serviço com cliente injetado e envio assíncrono, ou removê-lo. Decisão
explícita, não omissão. (RF-15)

### #20 [LOW] API deprecated: `datetime.utcnow()` (DEP-01)
**File:** `models/task.py:15,16,52`; `models/user.py:14`; `routes/task_routes.py:31,72,215,285`;
`routes/user_routes.py:172`; `routes/report_routes.py:35,42,45,71,133`; `utils/helpers.py:38`;
`seed.py:66,69,70,74` — 17 ocorrências
**Description:** Deprecado no Python 3.12 (o ambiente roda 3.12.0), com remoção prevista.
**Impact:** Não é só estilo: `utcnow()` devolve um `datetime` *naive* rotulado como UTC. Comparar com
um datetime ciente de fuso levanta `TypeError`, e a comparação com `due_date` — que é o coração da
regra de "atrasada" — fica sujeita a erro silencioso de fuso.
**Recommendation:** `datetime.now(timezone.utc)`. (RF-16)

### #21 [LOW] Imports não utilizados (QUAL-07)
**File:** `app.py:7` (`os, sys, json`), `routes/task_routes.py:7` (`json, os, sys, time`),
`routes/user_routes.py:6` (`hashlib, json`), `routes/report_routes.py:7-8` (`format_date`,
`calculate_percentage`, `json`), `utils/helpers.py:3-7` (`os, json, sys, math, hashlib`),
`models/task.py:3` (`json`)
**Description:** 17 imports mortos em 6 arquivos.
**Impact:** Sugerem dependências que o módulo não tem e poluem a leitura da fronteira de cada arquivo.

### #22 [LOW] Constantes definidas e ignoradas (QUAL-05)
**File:** `utils/helpers.py:110-116` vs literais em `routes/`
**Description:** `VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`,
`MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY` e `DEFAULT_COLOR` existem — e todas as rotas repetem os
literais correspondentes à mão.
**Impact:** A intenção de centralizar existe e foi abandonada; alterar um limite exige caçar literais.

### #23 [LOW] Construções não idiomáticas (QUAL-09)
**File:** `models/user.py:34-38`; `models/task.py:38-48,50-60`; `routes/task_routes.py:141,210`;
`utils/helpers.py:103`
**Description:** `if cond: return True else: return False` em três métodos; `type(x) == list` em vez de
`isinstance`; `to_dict()` montando o dicionário campo a campo.

### #24 [LOW] `print()` como mecanismo de log (QUAL-06)
**File:** `routes/task_routes.py:149,153,219,234`; `routes/user_routes.py:83,89,147`
**Description:** 7 chamadas a `print()` fazendo o papel de log, sem nível nem destino configurável.
**Recommendation:** `logging`. (RF-18)

### #25 [LOW] Política de senha fraca (QUAL-02)
**File:** `routes/user_routes.py:64,116`
**Description:** `if len(password) < 4` — quatro caracteres é o mínimo aceito.
**Impact:** Combinado com MD5 sem salt (finding #2), o espaço de busca é exaurível trivialmente.

## Deprecated APIs

Diferente dos projetos 1 e 2, aqui **há APIs deprecated em uso ativo**:

| API | Local | Deprecated desde | Equivalente moderno |
|---|---|---|---|
| `datetime.utcnow()` | 17 ocorrências em 7 arquivos (ver #20) | Python 3.12 (remoção prevista) | `datetime.now(timezone.utc)` |
| `Model.query.get(id)` | 16 ocorrências em 3 arquivos (ver #13) | SQLAlchemy 2.0 (`LegacyAPIWarning`) | `db.session.get(Model, id)` |
| `Model.query` (padrão geral) | todas as rotas | SQLAlchemy 2.0 | `db.session.execute(db.select(Model))` |

Verificados e **não** encontrados: `@app.before_first_request` (removido no Flask 2.3), `flask.Markup`,
`flask.escape`, `imp`, `distutils`, `locale.getdefaultlocale()`.

## Refactoring Plan

### Estratégia: projeto de nível B (separação nominal)

Diferente dos projetos 1 e 2, que eram monolitos planos, aqui já existe uma árvore de camadas. A
estratégia é **realocar responsabilidade dentro da estrutura existente**, não recriá-la:

- `routes/`, `models/`, `services/` e `utils/` são **mantidos** com os nomes atuais — a convenção do
  projeto já é coerente e renomear `routes/` para `views/` custaria mais do que entrega.
- São **adicionadas** as camadas ausentes: `controllers/`, `validators/`, `config/`, `middlewares/`.
- `services/` deixa de ser código morto: ou é adotado, ou é removido — decisão explícita por símbolo.

### Estrutura proposta

```
task-manager-api/
├── app.py                          composition root — create_app()
├── seed.py                         usa a factory, sem efeito colateral de import
├── scripts/init_db.py              criação de schema explícita
├── .env.example
├── config/settings.py              env, sem segredo literal
├── database.py                     instância do SQLAlchemy (mantido)
├── models/                         (mantido) task, user, category
│   └── + regras de domínio adotadas (is_overdue passa a ser usado)
├── controllers/                    NOVO — fluxo dos casos de uso
│   ├── task_controller.py
│   ├── user_controller.py
│   ├── category_controller.py
│   └── report_controller.py
├── routes/                         (mantido) handlers finos
│   ├── task_routes.py
│   ├── user_routes.py
│   ├── category_routes.py          NOVO — extraído de report_routes
│   ├── report_routes.py
│   ├── system_routes.py            NOVO — / e /health
│   └── dto/                        NOVO — serialização de saída
├── validators/                     NOVO — schemas compartilhados POST/PUT
├── services/notification_service.py (decisão explícita: adotar ou remover)
├── middlewares/                    NOVO — exceptions, error_handler, auth
└── utils/helpers.py                (mantido) só o que for realmente usado
```

### Mapeamento finding → transformação

| Findings | Transformação | Arquivos afetados |
|---|---|---|
| #4, #9 | RF-01 Configuração para o ambiente | `config/settings.py`, `.env.example` |
| #2, #25 | RF-03 Hash de senha seguro | `models/user.py` |
| #1, #11 | RF-04 DTO de saída com allowlist | `routes/dto/*` |
| #5 | RF-06 Extrair controller das rotas | `controllers/*` |
| #16 | RF-07 Separar blueprint de categorias | `routes/category_routes.py` |
| #7 | RF-08 Factory `create_app` + schema explícito | `app.py`, `scripts/init_db.py` |
| #8, #17 | RF-09 Error handler central + exceções de domínio | `middlewares/*` |
| #18 | RF-10 Cascade no relacionamento | `models/task.py` |
| #10, #15 | RF-11 Eliminar N+1 e agregação redundante | `controllers/*` |
| #12 | RF-12 Paginação | `routes/*`, `controllers/*` |
| #14 | RF-13 Camada de validação | `validators/*` |
| #6, #11 | RF-14 Adotar ou remover código morto | `models/`, `utils/`, `services/` |
| #19 | RF-15 Decisão explícita sobre o service | `services/notification_service.py` |
| #13, #20 | RF-16 Substituir APIs deprecated | todos os arquivos |
| #22 | RF-17 Usar as constantes existentes | `utils/helpers.py`, `validators/*` |
| #24 | RF-18 Logging estruturado | `config/logging_config.py` |
| #3 | RF-19 Remover token falso, proteger rotas | `routes/user_routes.py`, `middlewares/auth.py` |
| #21, #23 | Imports mortos e construções idiomáticas | todo o código |

### Contrato preservado

Os **22 endpoints** devem responder com o mesmo método, path, status e formato. Mudanças previstas:

1. **`password` deixa de aparecer** nas respostas de `/users/<id>`, `POST /users`, `PUT /users/<id>` e
   `/login` (finding #1). As demais chaves permanecem.
2. **`/login` deixa de devolver o campo `token`** (finding #3). Devolver um token falso é pior que não
   devolver nenhum: induz o cliente a acreditar que há sessão.
3. **Listagens passam a aceitar `limit`/`offset`** (finding #12), com o envelope atual preservado quando
   os parâmetros não são informados.

### Fora de escopo

- **Revogação de credencial, refresh token e rotação de chave.** A Fase 3 emite e verifica o token
  (correção do finding #3); invalidar um token antes de expirar exige armazenamento de sessão, que é
  decisão de produto. Registrado como resíduo, não como achado fechado.
- **OAuth, MFA e autorização por dono do recurso.** Hoje qualquer usuário autenticado edita qualquer
  task; restringir por dono muda o produto — e está registrado como gap conhecido.
- **Migração de senhas existentes.** MD5 não é reversível: o login faz re-hash quando a senha confere,
  e as contas que nunca logarem permanecem com o hash antigo até um reset.
- **Adoção de `marshmallow`.** Declarado no `requirements.txt` e não usado; a camada `validators/` será
  escrita em Python puro para não introduzir dependência efetiva sem decisão do usuário.
- **Envio real de e-mail.** O `NotificationService` não é chamado por ninguém hoje; a Fase 3 decide
  entre adotar com cliente injetado ou remover, sem passar a enviar e-mail de verdade.

```
================================
Total: 25 findings
================================
```

---

```
================================
PHASE 3: REFACTORING COMPLETE
================================
```

## New Project Structure

A estratégia de nível B foi seguida: `models/`, `routes/`, `services/` e `utils/` **mantiveram os
nomes originais**; as camadas ausentes foram adicionadas.

```
task-manager-api/
├── app.py                       composition root — create_app() + init_schema()
├── seed.py                      usa a factory (antes: from app import app)
├── scripts/init_db.py           NOVO — criação de schema explícita
├── .env.example                 NOVO
├── config/                      NOVO
│   ├── settings.py
│   └── logging_config.py
├── models/                      (mantido) entidades e regras de domínio
│   ├── task.py                  is_overdue agora é usado
│   ├── user.py                  hash com salt; sem to_dict
│   └── category.py
├── controllers/                 NOVO
│   ├── task_controller.py
│   ├── user_controller.py
│   ├── category_controller.py
│   └── report_controller.py
├── routes/                      (mantido) handlers finos
│   ├── task_routes.py
│   ├── user_routes.py
│   ├── category_routes.py       NOVO — extraído de report_routes
│   ├── report_routes.py
│   ├── system_routes.py         NOVO
│   └── dto/                     NOVO
│       ├── task_dto.py
│       ├── user_dto.py
│       └── category_dto.py
├── validators/                  NOVO
│   ├── common.py
│   ├── task_schema.py
│   ├── user_schema.py
│   └── category_schema.py
├── services/notification_service.py   (adotado, com remetente injetado)
├── middlewares/                 NOVO
│   ├── exceptions.py
│   ├── error_handler.py
│   └── auth.py
└── utils/
    ├── helpers.py               só o que passou a ser usado
    └── datetime_utils.py        NOVO — substitui datetime.utcnow()
```

**Antes:** 15 arquivos, 1.158 linhas, camadas nominais.
**Depois:** 30 módulos com responsabilidade única por arquivo.

Indicador direto: o maior handler de rota caiu de **90 linhas** (`summary_report`) para **12**.

## Decisão sobre cada símbolo morto (finding #6)

A regra do playbook é "adotar ou remover, nunca manter as duas versões". Aplicada símbolo a símbolo:

| Símbolo | Decisão | Onde está agora |
|---|---|---|
| `Task.is_overdue()` | **adotado** | propriedade do model, usada pelos 3 DTOs — as 6 cópias nas rotas sumiram |
| `process_task_data()` | **removido** | substituído por `validators/task_schema.py` |
| `NotificationService` | **adotado** | remetente injetado, sem credenciais; `LoggingSender` como padrão; chamado pelo `TaskController` na atribuição |
| `validate_email` | **adotado** | `validators/user_schema.py` |
| `sanitize_string` | **adotado** | os três validators |
| `is_valid_color` | **adotado** | `validators/category_schema.py` |
| `format_date`, `calculate_percentage` | **adotados** | DTOs e `report_controller` |
| `generate_id`, `log_action` | **removidos** | sem uso e sem substituto necessário (logging via `logging`) |
| `VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR` | **adotadas** | fonte única, consumida pelos validators |
| `marshmallow`, `python-dotenv` | mantidos como recomendação | a camada `validators/` foi escrita em Python puro para não introduzir dependência efetiva sem decisão do usuário |

## Findings Resolved

| Severidade | Resolvidos | Total | Observação |
|---|---|---|---|
| CRITICAL | 4/4 | 4 | #3 (autenticação) resolvido com prova de execução: ver "Prova de mitigação" abaixo |
| HIGH | 5/5 | 5 | |
| MEDIUM | 9/9 | 9 | |
| LOW | 5/6 | 6 | #25 (senha mínima de 4 caracteres) **não alterado** — ver abaixo |
| **Total** | **23/24 + 1 deliberadamente não alterado** | **25** | |

**Sobre o finding #25:** elevar o mínimo de senha de 4 para 8 caracteres mudaria o resultado de
requisições que hoje são aceitas — é decisão de política de produto, não refatoração. O risco real
apontado no finding vinha da combinação com MD5 sem salt, que foi corrigida. A constante
`MIN_PASSWORD_LENGTH` agora existe em um único lugar (`utils/helpers.py`), com a recomendação
registrada em comentário; elevá-la passou a ser uma alteração de uma linha.

Verificação por grep após a refatoração:

| Verificação | Resultado |
|---|---|
| `datetime.utcnow()` | 0 (só menções em docstring do `datetime_utils`) |
| `Model.query.get()` | 0 |
| `password` em DTO de resposta | 0 |
| `fake-jwt` | 0 (só menções em comentário) |
| Segredos literais em código | 0 |
| `except:` nu | 0 (só menção em docstring) |
| `try/except` dentro de rotas | 0 |
| `print()` em rotas/controllers/models | 0 |
| Maior handler de rota | 12 linhas (antes: 90) |
| Rota protegida sem decorator de guarda | 0 (18 rotas protegidas: 11 `@requer_autenticacao`, 7 `@requer_papel`) |
| Flag capaz de desligar a autenticação (`AUTH_ENABLED` e similares) | 0 — removida do código e do `.env.example` |

## Validation

Baseline capturado com a versão original (extraída do git), banco semeado pelo `seed.py`;
refatorado exercitado com a mesma sequência, também recém-semeado.

```
  ✓ Application boots without errors
  ✓ 22/22 endpoints registrados (mesma lista da Fase 1)
  ✓ 35/35 status codes idênticos ao baseline
  ✓ 18/18 payloads de leitura idênticos (timestamps normalizados)
  ✓ Caminhos de erro preservados      400 validação · 404 inexistente · 409 email duplicado · 401 login
  ✓ GET /users/1 expõe 'password'     True → False
  ✓ POST /login expõe 'password'      True → False
  ✓ POST /login devolve token real    'fake-jwt-token-1' → token assinado com HMAC, com expiração
  ✓ 22/22 chamadas anônimas a rota protegida negadas (401) — 18 rotas distintas
  ✓ 7/7 rotas de admin/gestão negam papel insuficiente (403)
  ✓ Import puro de app.py cria banco   True → False
  ✓ Cascade de deleção equivalente     original e refatorado: 10 tasks → 7 após DELETE /users/3
  ✓ Zero anti-patterns CRITICAL/HIGH remanescentes
```

**Verificação específica do finding #7.** Durante a Fase 1, um simples `import app` para listar as
rotas criou o arquivo `instance/tasks.db`. Após a refatoração o mesmo import não cria nada — a criação
de schema passou a ser um passo explícito:

```
antes  → banco criado apenas pelo import: True
depois → banco criado apenas pelo import: False
```

**Comparação de payloads.** Os 18 endpoints de leitura foram comparados com os dois lados recém-semeados,
normalizando apenas os campos voláteis por construção (`created_at`, `updated_at`, `due_date`,
`generated_at`, `timestamp`, `days_overdue`) e os campos cuja remoção foi decisão deliberada
(`password`, `token`). Inclui `/reports/summary`, que agrega 12 métricas, e `/tasks/stats` — os dois
pontos onde a substituição de 12 `COUNT` por `GROUP BY` poderia ter mudado resultado. Nenhum mudou.

## Prova de mitigação — finding #3 (autenticação simulada)

Execução na **configuração padrão do projeto**: nenhuma variável exportada além do que o `.env.example`
traz, e não existe chave capaz de desligar a verificação. A coluna `role` — que existia no schema desde
o início e nenhuma linha de código consultava — passou a decidir o acesso.

| Acesso | Endpoints |
|---|---|
| Público | `GET /`, `GET /health`, `POST /login`, `POST /users` (cadastro) |
| Autenticado (qualquer papel) | todo o `/tasks*`, `GET/PUT /users/<id>`, `GET /users/<id>/tasks`, `GET /categories` |
| `admin` ou `manager` | `POST/PUT/DELETE /categories`, `GET /reports/summary`, `GET /reports/user/<id>` |
| `admin` | `GET /users`, `DELETE /users/<id>` |

```
$ curl -s -w '\nHTTP %{http_code}\n' localhost:5003/reports/summary
{"error":"Autenticação obrigatória"}
HTTP 401

$ curl -s ... localhost:5003/reports/summary -H "Authorization: Bearer $TOKEN_USER"      # role=user
{"error":"Permissão insuficiente"}
HTTP 403

$ curl -s ... localhost:5003/reports/summary -H "Authorization: Bearer $TOKEN_MANAGER"   # role=manager
{"generated_at":"...","overview":{"total_categories":4,"total_tasks":10,"total_users":3},...}
HTTP 200

$ curl -s ... localhost:5003/users -H "Authorization: Bearer $TOKEN_MANAGER"   # rota exclusiva de admin
{"error":"Permissão insuficiente"}
HTTP 403
```

Login devolvendo credencial real — o `token` voltou à resposta, agora assinado e com expiração:

```
$ curl -s -X POST localhost:5003/login -d '{"email":"joao@email.com","password":"1234"}'
{
    "message": "Login realizado com sucesso",
    "token": "eyJzdWIiOjEsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc4NzAwNDA1OH0.tDbSqwh1N0yAwfDZkD3r-2-y7m7_Ce9S10DASj6Myds",
    "user": {"active": true, "created_at": "...", "email": "joao@email.com", "id": 1,
             "name": "João Silva", "role": "admin"}
}
```

Varredura completa, na configuração padrão:

```
  Chamadas anônimas negadas:    22/22   (18 rotas distintas)
  403 por papel insuficiente:    7/7
  Status iguais ao original:    27/27
  Formatos iguais ao original:  27/27
```

O mecanismo é um token assinado com HMAC-SHA256 sobre a `SECRET_KEY` (`middlewares/auth.py`), sem
dependência nova em `requirements.txt`.

## Findings Not Resolved

O único achado deliberadamente não alterado continua sendo o **#25** (senha mínima de 4 caracteres),
pelo motivo já registrado: é política de produto. Resíduos da correção do #3, nenhum deles restaurando
o acesso anônimo:

| Resíduo | Efeito | Recomendação |
|---|---|---|
| Autorização por papel, não por dono do recurso | Um usuário autenticado edita a task de outro | Comparar `g.usuario["sub"]` com `task.user_id` — muda o produto |
| Token sem revogação | Credencial vazada vale até expirar (1h, `TOKEN_TTL_SEGUNDOS`) | Armazenar sessões e conferir na verificação |
| `SECRET_KEY` efêmera quando ausente | Tokens deixam de valer a cada restart em desenvolvimento | Definir `SECRET_KEY` no `.env` |

## Breaking Changes

1. **`password` removido de todas as respostas** (finding #1): `GET /users/<id>`, `POST /users`,
   `PUT /users/<id>` e o objeto `user` do login. As demais chaves permanecem idênticas.
2. **`token` de `POST /login` deixou de ser falso** (finding #3). O valor era `'fake-jwt-token-<id>'`,
   previsível e que nenhuma rota verificava; agora é assinado com HMAC sobre a `SECRET_KEY`, expira e é
   exigido pelas rotas protegidas. A chave `token` permanece no mesmo lugar da resposta.
3. **Formato de erro unificado** para `{"error": "..."}`. Os status codes são idênticos; algumas
   mensagens foram unificadas entre POST e PUT (ex.: "Senha muito curta" e "Senha deve ter no mínimo 4
   caracteres" viraram a mesma mensagem).
4. **Listagens aceitam `limit`/`offset`** com teto de 200 (finding #12). Sem os parâmetros, o
   comportamento é o anterior para os volumes atuais.
5. **Hash de senha migrado para formato com salt** (finding #2). As credenciais existentes continuam
   funcionando: o login detecta o formato MD5 legado e regrava no novo.
6. **18 das 22 rotas passaram a exigir credencial** (finding #3) — todas menos `/`, `/health`,
   `POST /login` e `POST /users`. É a mudança de contrato mais visível desta refatoração, e é
   deliberada: uma API de tarefas com `DELETE /users/<id>` anônimo não é comportamento a preservar.
   Clientes existentes passam a chamar `POST /login` e enviar `Authorization: Bearer <token>`.

```
================================
Total: 25 findings | 24 resolvidos | 1 deliberadamente não alterado | 0 regressões
Rotas protegidas: 18 | chamadas anônimas negadas na configuração padrão: 22/22
================================
```

---

## Histórico de execução

| Execução | Resultado |
|---|---|
| 1ª | Findings #1–#25 tratados, mas o #3 foi fechado com os decorators atrás de `AUTH_ENABLED=false`. O token falso saiu (acerto) e as 22 rotas continuaram anônimas (erro) — o relatório contava o achado como mitigado enquanto `DELETE /users/<id>` respondia 200 a qualquer cliente. |
| 2ª (esta) | A skill foi corrigida antes de rodar de novo (princípio 6 do `SKILL.md`, anti-pattern SEC-10, RF-19 reescrito, prova de mitigação obrigatória na Fase 3.2). O #3 foi refeito com emissão e verificação reais, `role` finalmente consultado, e a evidência acima. |

Correção adicional detectada pela revalidação: `POST /tasks` sem `description` devolvia `null` onde o
original devolvia `""`. Divergência de contrato pequena, não intencional e não relacionada à
autenticação — corrigida em `validators/task_schema.py`, o que levou os formatos de 25/27 para 27/27.
