# Refatoração Arquitetural Automatizada — Skill `refactor-arch`

Desafio de criação de Skills: uma skill agnóstica de tecnologia que **analisa**, **audita** e **refatora**
projetos legados para o padrão MVC.

O enunciado original do desafio está preservado em [`DESAFIO.md`](./DESAFIO.md).

| Projeto | Stack | Papel no desafio |
|---|---|---|
| [`code-smells-project/`](./code-smells-project) | Python 3 + Flask 3.1.1 (sqlite3 puro) | E-commerce monolítico, sem camadas reais |
| [`ecommerce-api-legacy/`](./ecommerce-api-legacy) | Node.js + Express 4 (sqlite3) | LMS com checkout, God Class + callback hell |
| [`task-manager-api/`](./task-manager-api) | Python 3 + Flask 3 + SQLAlchemy | Task manager com organização **parcial** de camadas |

---

## Índice

- [A) Análise Manual](#a-análise-manual)
  - [Metodologia e escala de severidade](#metodologia-e-escala-de-severidade)
  - [Projeto 1 — code-smells-project](#projeto-1--code-smells-project-pythonflask)
  - [Projeto 2 — ecommerce-api-legacy](#projeto-2--ecommerce-api-legacy-nodejsexpress)
  - [Projeto 3 — task-manager-api](#projeto-3--task-manager-api-pythonflask--sqlalchemy)
  - [Padrões transversais](#padrões-transversais-insumo-para-o-catálogo-da-skill)
- [B) Construção da Skill](#b-construção-da-skill)
- [C) Resultados](#c-resultados)
- [D) Como Executar](#d-como-executar)

---

## A) Análise Manual

### Metodologia e escala de severidade

Os três projetos foram lidos integralmente (2.118 linhas em 22 arquivos-fonte) antes da construção da
skill. Cada achado foi classificado pela escala do desafio:

| Severidade | Critério |
|---|---|
| **CRITICAL** | Falha grave de arquitetura ou segurança: expõe dados sensíveis, permite execução arbitrária, ou concentra banco + regra de negócio + roteamento no mesmo arquivo (God Class) |
| **HIGH** | Violação forte de MVC/SOLID que inviabiliza teste e manutenção: regra de negócio presa no controller/rota, acoplamento sem injeção de dependência, estado global mutável |
| **MEDIUM** | Padronização, duplicação e performance moderada: N+1, validação ausente, middlewares inadequados |
| **LOW** | Legibilidade, nomenclatura, magic numbers, imports mortos |

**Contagem total da análise manual: 55 achados** — 16 CRITICAL, 14 HIGH, 15 MEDIUM, 10 LOW.

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total |
|---|---:|---:|---:|---:|---:|
| `code-smells-project` | 6 | 4 | 5 | 3 | **18** |
| `ecommerce-api-legacy` | 5 | 6 | 4 | 3 | **18** |
| `task-manager-api` | 5 | 4 | 6 | 4 | **19** |
| **Total** | **16** | **14** | **15** | **10** | **55** |

---

### Projeto 1 — `code-smells-project` (Python/Flask)

**Stack:** Python 3 · Flask 3.1.1 · flask-cors 5.0.1 · SQLite (`sqlite3` puro, sem ORM)
**Domínio:** API de E-commerce — produtos, usuários, pedidos, itens de pedido, relatório de vendas
**Arquitetura atual:** 4 arquivos na raiz (`app.py`, `controllers.py`, `models.py`, `database.py`), 780 linhas.
Existe nomenclatura MVC, mas **não** separação real: `models.py` é uma camada de acesso a dados
procedural que também contém regra de negócio e formatação de resposta.

| # | Severidade | Achado | Local |
|---|---|---|---|
| 1.1 | CRITICAL | SQL Injection sistêmico (concatenação de string) | `models.py` (21 pontos) |
| 1.2 | CRITICAL | Endpoint de execução de SQL arbitrário | `app.py:59-78` |
| 1.3 | CRITICAL | Endpoint destrutivo sem autenticação | `app.py:47-57` |
| 1.4 | CRITICAL | Senhas em texto plano | `models.py:122-131`, `database.py:75-79` |
| 1.5 | CRITICAL | Vazamento de segredos e de senhas nas respostas | `controllers.py:284-289`, `models.py:84,99` |
| 1.6 | CRITICAL | `SECRET_KEY` hardcoded + `DEBUG=True` | `app.py:7-8,88` |
| 1.7 | HIGH | God Module: 4 domínios + regra de negócio + formatação | `models.py:1-314` |
| 1.8 | HIGH | Estado global mutável: conexão singleton thread-unsafe | `database.py:4-10` |
| 1.9 | HIGH | Regra de negócio e efeitos colaterais dentro do controller | `controllers.py:208-210,247-250` |
| 1.10 | HIGH | Ausência total de camada de autenticação/autorização | projeto inteiro |
| 1.11 | MEDIUM | N+1 queries em listagem de pedidos e relatório | `models.py:171-233,235-254` |
| 1.12 | MEDIUM | Duplicação massiva de código | `models.py:171-233`, `controllers.py:28-54` vs `72-90` |
| 1.13 | MEDIUM | Error handling não centralizado, vazando `str(e)` | 15 blocos `try/except` |
| 1.14 | MEDIUM | CORS liberado para qualquer origem | `app.py:9` |
| 1.15 | MEDIUM | Roteamento manual repetitivo, sem Blueprints | `app.py:11-30` |
| 1.16 | LOW | Magic numbers nas faixas de desconto | `models.py:256-262` |
| 1.17 | LOW | `print()` como mecanismo de log (15 ocorrências) | `controllers.py`, `app.py:56,83-86` |
| 1.18 | LOW | Imports mortos e shadowing de builtin (`id`) | `models.py:2`, `database.py:2` |

#### Detalhamento

**[CRITICAL] 1.1 — SQL Injection sistêmico**
`models.py:28,47-50,57-61,68,92,109-111,126-129,140,148-166,174,188,192,220,224,279-281,289-297`
Todas as queries são montadas por concatenação de string. O caso mais grave é
`login_usuario()` (`models.py:109-111`): `"... WHERE email = '" + email + "' AND senha = '" + senha + "'"`.
**Por que é relevante:** um `email` igual a `' OR '1'='1' --` autentica como o primeiro usuário da tabela
(que é o *admin*, semeado em `database.py:76`). Não é apenas leitura indevida — é bypass de autenticação
e, via `buscar_produtos` (`models.py:289-297`), extração de qualquer tabela do banco. O projeto já usa
parâmetros ligados corretamente em `database.py:70-83`, o que prova que a falha é de disciplina, não de
limitação técnica.

**[CRITICAL] 1.2 — Endpoint de execução de SQL arbitrário** — `app.py:59-78`
`POST /admin/query` recebe `{"sql": "..."}` e executa direto no cursor, sem autenticação nem allowlist.
**Por que é relevante:** é um backdoor completo de banco exposto na internet (`host="0.0.0.0"`). Permite
`DROP TABLE`, leitura da tabela `usuarios` inteira com senhas, e escrita de dados. Nenhuma refatoração
arquitetural faz sentido mantendo esta rota — ela deve ser removida.

**[CRITICAL] 1.3 — Endpoint destrutivo sem autenticação** — `app.py:47-57`
`POST /admin/reset-db` apaga as 4 tabelas. Qualquer requisição anônima destrói todos os dados de produção.

**[CRITICAL] 1.4 — Senhas em texto plano** — `models.py:122-131`, `database.py:75-79`
`criar_usuario` grava a senha crua; o seed cadastra `admin123`/`123456`. O login compara string com string.
**Por que é relevante:** um vazamento do arquivo `loja.db` entrega todas as credenciais, e a reutilização
de senhas propaga o incidente para outros serviços dos usuários.

**[CRITICAL] 1.5 — Vazamento de segredos e senhas nas respostas HTTP**
`controllers.py:284-289` — o `/health` devolve `secret_key`, `debug`, `db_path` e `ambiente` no JSON público.
`models.py:84,99` — `get_todos_usuarios()` e `get_usuario_por_id()` incluem o campo `senha`, servido em
`GET /usuarios` e `GET /usuarios/<id>`.
**Por que é relevante:** transforma dois endpoints de leitura em dump de credenciais; a `SECRET_KEY` exposta
permite forjar sessões assinadas pelo Flask.

**[CRITICAL] 1.6 — Configuração hardcoded e debug ligado** — `app.py:7-8,88`
`SECRET_KEY = "minha-chave-super-secreta-123"` e `DEBUG=True` fixos no código, com `app.run(debug=True)`.
**Por que é relevante:** além do segredo versionado no Git, o debugger do Werkzeug expõe um console Python
interativo na página de erro — execução remota de código se o PIN for contornado.

**[HIGH] 1.7 — God Module (`models.py`, 314 linhas)**
Um único arquivo concentra acesso a dados de 4 domínios (produtos, usuários, pedidos, relatórios),
regras de negócio (faixas de desconto em `235-273`, cálculo de total e baixa de estoque em `133-169`) e
formatação de apresentação (montagem manual de dicionários em `12-21`, `31-40`, `304-313`).
**Por que é relevante:** viola SRP em três eixos. É impossível testar a regra de desconto sem um banco
SQLite real, e qualquer mudança de schema quebra a serialização da API. É a raiz da qual derivam 1.11 e 1.12.

**[HIGH] 1.8 — Estado global mutável: conexão singleton** — `database.py:4-10`
`db_connection` é uma global de módulo, criada com `check_same_thread=False` e nunca fechada; `get_db()`
ainda executa DDL e seed como efeito colateral (`database.py:12-84`).
**Por que é relevante:** o servidor Flask atende requisições em múltiplas threads compartilhando **um**
cursor de conexão sem lock — condição de corrida real em escrita concorrente. Impede também trocar o banco
em testes, porque não há injeção de dependência.

**[HIGH] 1.9 — Regra de negócio e efeitos colaterais no controller** — `controllers.py:208-210,247-250`
O controller dispara "e-mail", "SMS" e "push" via `print`, e decide o que notificar conforme o status do
pedido. `models.criar_pedido` (`models.py:133-169`) por sua vez devolve `{"erro": ...}` como fluxo de
controle, obrigando o controller a inspecionar o dicionário (`controllers.py:205`).
**Por que é relevante:** a política de notificação fica inacessível a qualquer outro consumidor (worker, CLI)
e o contrato erro-como-dado impede distinguir falha de negócio de falha técnica.

**[HIGH] 1.10 — Ausência de camada de autenticação/autorização**
`/login` (`controllers.py:167-186`) devolve os dados do usuário sem emitir token nem sessão, e nenhuma rota
verifica identidade — inclusive `PUT/DELETE /produtos/<id>` e as rotas `/admin/*`.
**Por que é relevante:** o campo `tipo` ("admin"/"cliente") existe no schema mas nunca é consultado; a
autorização foi modelada e não implementada.

**[MEDIUM] 1.11 — N+1 queries** — `models.py:171-201`, `203-233`, `235-254`
`get_pedidos_usuario` faz 1 query de pedidos + 1 de itens por pedido + 1 de produto por item. Uma listagem
com 50 pedidos de 3 itens dispara 201 queries onde 1 JOIN bastaria. `relatorio_vendas` usa 5 round-trips
(`COUNT` + `SUM` + 3 `COUNT` filtrados) substituíveis por um único `GROUP BY`.

**[MEDIUM] 1.12 — Duplicação de código**
`get_pedidos_usuario` e `get_todos_pedidos` (`models.py:171-233`) são ~95% idênticas — diferem apenas no
`WHERE`. O bloco de validação de produto é copiado entre `criar_produto` (`controllers.py:28-54`) e
`atualizar_produto` (`controllers.py:72-90`), e já divergiu: só o `criar` valida tamanho do nome e categoria.
**Por que é relevante:** divergência silenciosa é o custo real da duplicação — hoje é possível *atualizar*
um produto para uma categoria inválida que o *criar* recusaria.

**[MEDIUM] 1.13 — Error handling não centralizado**
15 blocos `try/except Exception` repetem `return jsonify({"erro": str(e)}), 500`.
**Por que é relevante:** além do boilerplate, `str(e)` de uma exceção do sqlite3 devolve trechos da query
ao cliente — reconhecimento gratuito da estrutura do banco. O padrão correto é um `@app.errorhandler` único.

**[MEDIUM] 1.14 — CORS irrestrito** — `app.py:9`
`CORS(app)` sem parâmetros libera `Access-Control-Allow-Origin: *` para todos os endpoints, inclusive `/admin/*`.

**[MEDIUM] 1.15 — Roteamento manual repetitivo** — `app.py:11-30`
20 chamadas a `add_url_rule` no entry point, sem Blueprints. Adicionar um domínio exige editar o arquivo
de bootstrap — acoplamento desnecessário entre composition root e roteamento.

**[LOW] 1.16 — Magic numbers** — `models.py:256-262`
Faixas `10000`/`5000`/`1000` e alíquotas `0.1`/`0.05`/`0.02` embutidas no cálculo de desconto; limites `2` e
`200` para tamanho de nome em `controllers.py:47-50`. Regra de negócio sem nome não é auditável nem testável.

**[LOW] 1.17 — `print()` como log** — `controllers.py:8,11,57,61,106,161,179,182,208-210,219,248,250`; `app.py:56,83-86`
Sem níveis, sem timestamp, sem destino configurável; escreve dados de usuário (e-mail no login) em stdout.

**[LOW] 1.18 — Imports mortos, shadowing e concatenação de string**
`import sqlite3` nunca usado (`models.py:2`), `import os` nunca usado (`database.py:2`); o parâmetro `id`
sombreia o builtin em ~8 funções; `cursor2`/`cursor3` (`models.py:187-193`); mensagens montadas com `+`
em vez de f-string em todo o projeto.

---

### Projeto 2 — `ecommerce-api-legacy` (Node.js/Express)

**Stack:** Node.js · Express 4.18.2 · sqlite3 5.1.6
**Domínio:** LMS (plataforma de cursos) — usuários, cursos, matrículas, pagamentos, auditoria; fluxo central de checkout
**Arquitetura atual:** 3 arquivos em `src/` (180 linhas). `app.js` é o entry point, `AppManager.js` é uma
God Class que faz tudo, `utils.js` guarda config e estado global.

| # | Severidade | Achado | Local |
|---|---|---|---|
| 2.1 | CRITICAL | Segredos de produção hardcoded e versionados | `utils.js:1-7` |
| 2.2 | CRITICAL | Número de cartão e chave do gateway em log | `AppManager.js:45` |
| 2.3 | CRITICAL | Hash de senha caseiro (base64 truncado, sem salt) | `utils.js:17-23` |
| 2.4 | CRITICAL | God Class: DB + DDL + seed + rotas + negócio + relatório | `AppManager.js:1-141` |
| 2.5 | CRITICAL | Checkout sem transação — dados órfãos garantidos | `AppManager.js:50-63` |
| 2.6 | HIGH | "Gateway de pagamento" decidido pelo 1º dígito do cartão | `AppManager.js:46` |
| 2.7 | HIGH | Callback hell de 5 níveis com `this`/`self` misturados | `AppManager.js:37-77` |
| 2.8 | HIGH | Delete sem integridade referencial (admitido na resposta) | `AppManager.js:131-137` |
| 2.9 | HIGH | Erros silenciosamente ignorados; sem middleware de erro | `AppManager.js:104-106,131-136` |
| 2.10 | HIGH | Estado global mutável exportado por valor | `utils.js:9-10,25` |
| 2.11 | HIGH | Banco `:memory:` — dados perdidos a cada restart | `AppManager.js:7` |
| 2.12 | MEDIUM | N+1 no relatório financeiro (1 + N + 2M queries) | `AppManager.js:83-128` |
| 2.13 | MEDIUM | Orquestração assíncrona por contadores manuais | `AppManager.js:86-122` |
| 2.14 | MEDIUM | Validação de entrada ausente + senha default `"123456"` | `AppManager.js:35,68` |
| 2.15 | MEDIUM | Sem camada de middlewares (404, logger, rate limit, helmet) | `app.js:1-14` |
| 2.16 | LOW | Variáveis de uma letra e `let` onde cabe `const` | `AppManager.js:29-33` |
| 2.17 | LOW | Contrato de API inconsistente (`res.send` texto vs JSON) | `AppManager.js` |
| 2.18 | LOW | Import morto e `.verbose()` em produção | `AppManager.js:1-2` |

#### Detalhamento

**[CRITICAL] 2.1 — Segredos de produção hardcoded** — `utils.js:1-7`
`dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"`, `smtpUser`.
**Por que é relevante:** o prefixo `pk_live_` indica chave de **produção** do gateway. Está no repositório,
portanto no histórico do Git de todos que clonaram — rotacionar depois não desfaz a exposição. Config deve
vir de variável de ambiente com `.env.example` versionado no lugar dos valores.

**[CRITICAL] 2.2 — PAN do cartão e chave do gateway em log** — `AppManager.js:45`
``console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`)``
**Por que é relevante:** grava o número completo do cartão em texto claro no stdout, que normalmente é
coletado por agregadores de log. É violação direta de PCI-DSS (requisito 3.4) — dado de cartão nunca pode
ser persistido em log.

**[CRITICAL] 2.3 — Criptografia caseira** — `utils.js:17-23`
`badCrypto()` concatena 10.000 vezes os 2 primeiros caracteres do base64 da senha e devolve os 10 primeiros
caracteres do resultado.
**Por que é relevante:** base64 é *encoding*, não hash — é reversível. Como o resultado é sempre a repetição
de 2 caracteres derivados do mesmo prefixo, o espaço de saída é minúsculo: colisões são triviais e o hash
é invertível por inspeção. O loop de 10.000 iterações gasta CPU sem entregar nenhum custo de força bruta
real. Substituir por `bcrypt`/`argon2` com salt.

**[CRITICAL] 2.4 — God Class `AppManager`** — `AppManager.js:1-141`
A classe abre a conexão (`:7`), cria o schema (`:12-16`), semeia dados (`:18-21`), registra rotas (`:25-138`),
implementa a regra de checkout, simula o gateway de pagamento e monta o relatório financeiro.
**Por que é relevante:** é o exemplo canônico de God Class do enunciado — banco + roteamento + negócio no
mesmo arquivo. Nenhuma parte é testável isoladamente e o nome "Manager" já denuncia a ausência de fronteira
de responsabilidade.

**[CRITICAL] 2.5 — Checkout sem transação** — `AppManager.js:50-63`
A sequência cria `user` → `enrollment` → `payment` → `audit_log` em callbacks encadeados, sem
`BEGIN`/`COMMIT`. Cada passo retorna `500` isoladamente em caso de erro.
**Por que é relevante:** se o `INSERT` de `payments` falhar (`:55`), a matrícula **já foi persistida** e o
cliente recebe erro — aluno matriculado sem pagamento registrado. O inverso também ocorre: usuário criado
e depois pagamento recusado (`:48`) deixa conta órfã. Consistência financeira exige transação atômica.

**[HIGH] 2.6 — Pagamento simulado pelo primeiro dígito** — `AppManager.js:46`
`let status = cc.startsWith("4") ? "PAID" : "DENIED"` — qualquer número começando com 4 "paga" o curso.
**Por que é relevante:** a regra de negócio mais crítica do sistema é uma linha de placeholder acoplada ao
controller. A refatoração precisa isolá-la atrás de uma interface `PaymentGateway` injetável.

**[HIGH] 2.7 — Callback hell com `this`/`self` misturados** — `AppManager.js:37-77`
Cinco níveis de aninhamento; a linha `:26` cria `const self = this` porque os callbacks `function(err)`
das linhas `:50` e `:54` reescrevem `this` para o statement do sqlite3 (necessário para ler `this.lastID`).
**Por que é relevante:** é o defeito de legibilidade que esconde os bugs 2.5 e 2.9 — o fluxo de erro fica
impossível de auditar visualmente. Promisificação + `async/await` resolve.

**[HIGH] 2.8 — Delete sem integridade referencial** — `AppManager.js:131-137`
`DELETE FROM users WHERE id = ?` sem remover `enrollments` e `payments`; a resposta HTTP literalmente diz
*"mas as matrículas e pagamentos ficaram sujos no banco"*. O schema (`:12-16`) não declara `FOREIGN KEY`
e o sqlite3 não recebe `PRAGMA foreign_keys = ON`.
**Por que é relevante:** o relatório financeiro (`:104`) passa a exibir `student: 'Unknown'` para registros
órfãos — corrupção silenciosa de dados contábeis.

**[HIGH] 2.9 — Erros ignorados e ausência de middleware de erro**
`AppManager.js:104,106` — os parâmetros `err` das queries de usuário e pagamento nunca são verificados;
`:133` idem, e responde `200` mesmo com falha. Não há `app.use((err, req, res, next) => ...)` em `app.js`.
**Por que é relevante:** uma exceção não capturada dentro de um callback do sqlite3 derruba o processo Node
inteiro (não há supervisão). E falhas parciais retornam sucesso ao cliente.

**[HIGH] 2.10 — Estado global mutável** — `utils.js:9-10,25`
`globalCache` e `totalRevenue` são variáveis de módulo exportadas. `logAndCache` escreve em `globalCache`
sem limite de tamanho nem expiração.
**Por que é relevante:** dois problemas distintos. (a) `totalRevenue` é exportado **por valor** — quem
importa recebe um snapshot `0` que nunca muda; é um bug latente esperando o primeiro uso (`AppManager.js:2`
já importa e não usa). (b) `globalCache` cresce indefinidamente por usuário → vazamento de memória, e
impede escalar horizontalmente porque o estado não é compartilhado entre instâncias.

**[HIGH] 2.11 — Banco em memória** — `AppManager.js:7`
`new sqlite3.Database(':memory:')` — todos os dados (inclusive pagamentos) somem a cada restart, e cada
instância do processo tem seu próprio banco isolado.

**[MEDIUM] 2.12 — N+1 no relatório financeiro** — `AppManager.js:83-128`
1 query de cursos + 1 query de matrículas por curso + 2 queries (usuário e pagamento) por matrícula.
Com 10 cursos e 100 matrículas: 211 round-trips onde 1 `JOIN` com `GROUP BY` resolveria.

**[MEDIUM] 2.13 — Orquestração assíncrona por contadores manuais** — `AppManager.js:86-122`
`coursesPending` e `enrPending` são decrementados à mão para decidir quando responder.
**Por que é relevante:** frágil em dois pontos concretos — se a query de matrículas falhar, `enrollments`
vem `undefined` e `.length` (`:93`) lança exceção dentro de um callback (derruba o processo); e um curso sem
matrículas combinado a erro parcial pode disparar `res.json` duas vezes (`ERR_HTTP_HEADERS_SENT`).
`Promise.all` elimina a classe inteira de bug.

**[MEDIUM] 2.14 — Validação de entrada ausente** — `AppManager.js:35,68`
`if (!u || !e || !cid || !cc)` verifica apenas presença: não valida formato de e-mail, não valida que `cc`
é numérico (um `cc` não-string quebra `.startsWith` em `:46`), não valida tipo de `c_id`. E a senha, quando
ausente, vira o literal `"123456"` (`:68`) — criação silenciosa de conta com credencial previsível.

**[MEDIUM] 2.15 — Ausência de camada de middlewares** — `app.js:1-14`
Só `express.json()`. Sem handler 404, sem logger de request, sem rate limiting no checkout, sem `helmet`,
sem limite de tamanho de body. As rotas são registradas por um método de instância (`setupRoutes(app)`)
em vez de `express.Router()` — não há como montar, versionar ou testar um domínio isoladamente.

**[LOW] 2.16 — Nomenclatura** — `AppManager.js:29-33`
`u`, `e`, `p`, `cid`, `cc` para usuário, e-mail, senha, id do curso e cartão; `c` e `enr` nos loops (`:89,102`).
Todas as declarações usam `let` mesmo sem reatribuição.

**[LOW] 2.17 — Contrato de API inconsistente**
Sucesso responde JSON (`:60`), erro responde texto puro (`:35,38,41`), e uma rota responde texto de piada
(`:135`). O corpo do checkout usa nomes abreviados não convencionais (`usr`, `eml`, `pwd`, `c_id`, `card`).

**[LOW] 2.18 — Import morto e modernização**
`AppManager.js:2` importa `totalRevenue` sem usar; `.verbose()` (`:1`) mantém stack traces custosos em
produção. Modernização recomendada: `sqlite3` (callback-based, sem manutenção ativa) → `better-sqlite3`
ou `node:sqlite`; Express 4 → 5 (que propaga rejeições de handlers `async` automaticamente).

---

### Projeto 3 — `task-manager-api` (Python/Flask + SQLAlchemy)

**Stack:** Python 3 · Flask 3.0.0 · Flask-SQLAlchemy 3.1.1 · flask-cors 4.0.0 · SQLite
**Domínio:** Gerenciador de tarefas — tasks, users, categories, relatórios de produtividade
**Arquitetura atual:** já possui pastas `models/`, `routes/`, `services/`, `utils/` (1.158 linhas). A
separação é **nominal**: as rotas concentram validação, regra de negócio, acesso a dados e serialização;
`services/` e boa parte de `utils/` são código morto.

| # | Severidade | Achado | Local |
|---|---|---|---|
| 3.1 | CRITICAL | Hash de senha com MD5 e sem salt | `models/user.py:29,32` |
| 3.2 | CRITICAL | `to_dict()` expõe o hash da senha na API | `models/user.py:16-25` |
| 3.3 | CRITICAL | Token de autenticação falso; API 100% aberta | `routes/user_routes.py:210` |
| 3.4 | CRITICAL | `SECRET_KEY` hardcoded + `DEBUG=True` | `app.py:13,34` |
| 3.5 | CRITICAL | Credenciais SMTP hardcoded | `services/notification_service.py:7-10` |
| 3.6 | HIGH | Rotas como god-functions: sem camada de controller/service | `routes/*.py` |
| 3.7 | HIGH | Config e `db.create_all()` como efeito colateral de import | `app.py:9-31` |
| 3.8 | HIGH | Regra de negócio duplicada 5× com o model ignorado | 5 arquivos |
| 3.9 | HIGH | `except:` nu engolindo qualquer exceção (9 ocorrências) | `routes/*`, `utils/helpers.py` |
| 3.10 | MEDIUM | N+1 queries em listagem e relatórios | `task_routes.py:41-57`, `report_routes.py:53-68` |
| 3.11 | MEDIUM | **API deprecated:** `Model.query.get()` (SQLAlchemy 2.0) | 14 ocorrências |
| 3.12 | MEDIUM | Ausência de paginação em todas as listagens | `task_routes.py:14,281`, `report_routes.py:30` |
| 3.13 | MEDIUM | Validação inline duplicada; `marshmallow` declarado e não usado | `task_routes.py:96-124` vs `166-198` |
| 3.14 | MEDIUM | Rotas de `categories` dentro do blueprint de relatórios | `report_routes.py:157-223` |
| 3.15 | MEDIUM | 12 queries `COUNT` separadas em um único relatório | `report_routes.py:15-28` |
| 3.16 | LOW | **API deprecated:** `datetime.utcnow()` (Python 3.12+) | 14 ocorrências |
| 3.17 | LOW | Imports mortos em 6 arquivos | `app.py:7`, `task_routes.py:7`, … |
| 3.18 | LOW | Constantes existem em `helpers.py` mas literais são repetidos | `helpers.py:110-116` |
| 3.19 | LOW | `if/else` retornando booleano; `type(x) == list`; `print()` como log | `models/user.py:34-38` etc. |

#### Detalhamento

**[CRITICAL] 3.1 — MD5 sem salt para senhas** — `models/user.py:29,32`
`hashlib.md5(pwd.encode()).hexdigest()`.
**Por que é relevante:** MD5 é criptograficamente quebrado e extremamente rápido — GPUs comuns testam
bilhões de hashes por segundo. Sem salt, um único rainbow table reverte todas as senhas de uma vez. Como o
mínimo exigido é 4 caracteres (`user_routes.py:64`), o espaço de busca é exaurível em segundos. Deve migrar
para `bcrypt`/`argon2` com salt por usuário.

**[CRITICAL] 3.2 — Hash de senha vazado na resposta HTTP** — `models/user.py:16-25`
`to_dict()` inclui `'password': self.password`, e é usado em `GET /users/<id>` (`user_routes.py:33`),
na resposta de `POST /users` (`:85-86`) e no payload de **login** (`:209`).
**Por que é relevante:** combinado com 3.1, qualquer visitante anônimo lista os hashes MD5 de todos os
usuários e os quebra offline. A serialização de saída não pode ser responsabilidade do model de persistência
— é exatamente o tipo de acoplamento que a refatoração para MVC precisa cortar.

**[CRITICAL] 3.3 — Autenticação simulada** — `routes/user_routes.py:210`
`'token': 'fake-jwt-token-' + str(user.id)` — token previsível, não assinado, e **nenhuma** rota verifica
qualquer token.
**Por que é relevante:** `DELETE /users/<id>`, `PUT /tasks/<id>` e `/reports/summary` são acessíveis
anonimamente. Existe controle de papéis modelado (`User.is_admin()`, `models/user.py:34`) que nunca é
invocado — autorização projetada e não implementada.

**[CRITICAL] 3.4 — `SECRET_KEY` hardcoded e debug ligado** — `app.py:13,34`
`'super-secret-key-123'` versionado e `app.run(debug=True, host='0.0.0.0')`. O `python-dotenv` está no
`requirements.txt` (linha 6) e nunca é usado — a infraestrutura de config existe, mas não foi adotada.

**[CRITICAL] 3.5 — Credenciais SMTP hardcoded** — `services/notification_service.py:7-10`
Host, usuário e senha (`'senha123'`) fixos no construtor. O serviço inteiro é código morto (nenhum
`import` em todo o projeto), o que agrava: são credenciais expostas sem sequer entregar funcionalidade.

**[HIGH] 3.6 — Rotas como god-functions: MVC apenas na pasta** — `routes/*.py`
Cada handler acumula quatro responsabilidades. `create_task` (`task_routes.py:85-154`) faz parsing do
request, 8 validações de negócio, duas consultas de integridade referencial, construção da entidade,
persistência com `db.session` e serialização — 70 linhas. `summary_report` (`report_routes.py:12-101`) tem
90 linhas de agregação estatística dentro do handler HTTP.
**Por que é relevante:** é o achado central deste projeto — ter `routes/`, `models/` e `services/` não
significa ter camadas. A regra de negócio está inacessível fora do contexto HTTP: não dá para calcular
estatísticas de produtividade em um job noturno sem simular um request.

**[HIGH] 3.7 — Config e efeito colateral no import** — `app.py:9-31`
Configuração inline no módulo, sem factory (`create_app`), e `db.create_all()` executado **no import**
(`:30-31`).
**Por que é relevante:** importar `app` — o que `seed.py:2` faz — cria o schema como efeito colateral.
Impossível instanciar a app com config de teste (banco em memória) sem tocar o arquivo de produção. É a
ausência do composition root exigido pelo alvo MVC.

**[HIGH] 3.8 — Regra de negócio duplicada 5× enquanto o model é ignorado**
O cálculo de "task atrasada" é reescrito com o mesmo `if` triplo aninhado em:
`task_routes.py:30-39`, `task_routes.py:71-80`, `task_routes.py:283-287`, `user_routes.py:171-180`,
`report_routes.py:33-37` — e existe `Task.is_overdue()` (`models/task.py:50-60`) que **nunca é chamado**.
A serialização de task também é duplicada à mão (`task_routes.py:17-28`) apesar de `to_dict()` existir.
E `process_task_data()` (`utils/helpers.py:57-108`) reimplementa todas as validações de task — também
código morto.
**Por que é relevante:** três implementações concorrentes da mesma regra, duas delas mortas. Mudar a
definição de "atrasada" exige encontrar 5 cópias, e a versão "oficial" (o model) é a única que ninguém usa.

**[HIGH] 3.9 — `except:` nu** — `task_routes.py:62,137,204,236`; `user_routes.py:130,149`; `report_routes.py:186,221`; `utils/helpers.py:46-50`
`except:` sem tipo captura também `KeyboardInterrupt` e `SystemExit`, e descarta a exceção original.
**Por que é relevante:** `get_tasks` (`task_routes.py:62`) converte qualquer erro — inclusive um bug de
programação — em `{'error': 'Erro interno'}` sem log. Um `AttributeError` de refatoração passa despercebido
em produção indefinidamente.

**[MEDIUM] 3.10 — N+1 queries**
`task_routes.py:41-57` — dentro do loop de tasks, um `User.query.get()` e um `Category.query.get()` por task
(101 queries para 50 tasks). `report_routes.py:53-68` — um `Task.query.filter_by(user_id=...)` por usuário.
`report_routes.py:157-165` — um `COUNT` por categoria. Todos resolvíveis com `joinedload` ou `GROUP BY`.

**[MEDIUM] 3.11 — API deprecated: `Model.query.get()`**
`task_routes.py:67,117,122,158,188,195,227`; `user_routes.py:29,95,136,155`; `report_routes.py:105,192,213`.
`Query.get()` é legado no SQLAlchemy 2.0 e emite `LegacyAPIWarning`; o equivalente moderno é
`db.session.get(Model, id)`. O padrão `Model.query` como um todo é legado em favor de
`db.session.execute(db.select(Model))`.
**Por que é relevante:** o projeto já roda SQLAlchemy 2.x (Flask-SQLAlchemy 3.1.1) — está acumulando dívida
que quebra na próxima major.

**[MEDIUM] 3.12 — Ausência de paginação** — `task_routes.py:14,281`; `report_routes.py:30,53`
`Task.query.all()` carrega a tabela inteira em memória para serializar. `/reports/summary` chega a
materializar todas as tasks **e** todos os usuários com suas tasks. Degrada linearmente até o timeout.

**[MEDIUM] 3.13 — Validação inline duplicada** — `task_routes.py:96-124` vs `156-198`; `user_routes.py:54-72` vs `102-125`
As mesmas regras (tamanho do título, status válido, faixa de prioridade, formato de e-mail, role válido)
aparecem duas vezes por recurso, em POST e PUT. `marshmallow` está no `requirements.txt` (linha 4) e não é
importado em lugar nenhum.

**[MEDIUM] 3.14 — Blueprint com responsabilidade misturada** — `report_routes.py:157-223`
O CRUD completo de `/categories` mora dentro do blueprint de relatórios.
**Por que é relevante:** a fronteira de módulo não corresponde ao domínio — sintoma de que os blueprints
foram organizados por conveniência de arquivo, não por recurso.

**[MEDIUM] 3.15 — 12 queries `COUNT` sequenciais** — `report_routes.py:15-28`
Três contagens de totais + quatro por status + cinco por prioridade. Dois `GROUP BY` substituem as doze.

**[LOW] 3.16 — API deprecated: `datetime.utcnow()`**
`models/task.py:15,16,52`; `models/user.py:14`; `task_routes.py:31,72,215,285`; `user_routes.py:172`;
`report_routes.py:35,42,45,71`; `utils/helpers.py:38`; `seed.py:66-74`.
Deprecado no Python 3.12 com remoção prevista. Retorna um `datetime` *naive* (sem tzinfo) rotulado como UTC,
o que produz comparações incorretas ao cruzar com datas cientes de fuso. Equivalente moderno:
`datetime.now(timezone.utc)`.

**[LOW] 3.17 — Imports mortos**
`app.py:7` (`os, sys, json`), `task_routes.py:7` (`json, os, sys, time`), `user_routes.py:6` (`hashlib, json`),
`report_routes.py:8` (`json`) e `:7` (`format_date`, `calculate_percentage` importados e nunca usados),
`utils/helpers.py:1-7` (`os, json, sys, math, hashlib`), `models/task.py:3` (`json`).

**[LOW] 3.18 — Constantes definidas mas não utilizadas** — `utils/helpers.py:110-116`
`VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`,
`DEFAULT_PRIORITY`, `DEFAULT_COLOR` existem — e todas as rotas repetem os literais correspondentes à mão.

**[LOW] 3.19 — Estilo**
`if cond: return True else: return False` em `models/user.py:34-38` e `models/task.py:38-48,50-60`;
`type(tags) == list` em vez de `isinstance` (`task_routes.py:141,210`, `helpers.py:103`); `to_dict()`
montando o dicionário campo a campo (`models/task.py:23-36`); `print()` como log
(`task_routes.py:149,153,219,234`; `user_routes.py:83,89,147`); variáveis de uma letra (`t`, `u`, `c`, `p1`–`p5`).

---

### Padrões transversais (insumo para o catálogo da skill)

A análise dos três projetos mostrou que os mesmos anti-patterns reaparecem com roupagens diferentes por
stack. Essa recorrência é o que torna viável um catálogo agnóstico de tecnologia:

| Anti-pattern | Projeto 1 (Flask puro) | Projeto 2 (Express) | Projeto 3 (Flask+ORM) | Severidade |
|---|---|---|---|---|
| Segredos hardcoded | `app.py:7` | `utils.js:1-7` | `app.py:13`, `notification_service.py:7-10` | CRITICAL |
| Credenciais mal protegidas | texto plano | base64 truncado | MD5 sem salt | CRITICAL |
| Dado sensível vazado na resposta | `/health`, `/usuarios` | cartão em log | `password` no `to_dict()` | CRITICAL |
| God Class / God Module | `models.py` | `AppManager.js` | rotas de 70–90 linhas | CRITICAL/HIGH |
| Autenticação ausente ou falsa | sem token | rotas admin abertas | token falso | CRITICAL/HIGH |
| Estado global mutável | conexão singleton | `globalCache` | `db.create_all()` no import | HIGH |
| Regra de negócio fora da camada correta | notificação no controller | pagamento no handler | "overdue" 5× nas rotas | HIGH |
| Erro engolido / não centralizado | `str(e)` em 15 lugares | `err` ignorado | `except:` nu 9× | HIGH/MEDIUM |
| Consulta N+1 | pedidos e relatório | relatório financeiro | tasks e relatórios | MEDIUM |
| Validação ausente/duplicada | criar vs atualizar | só presença | POST vs PUT | MEDIUM |
| API deprecated | — | `sqlite3` callback, Express 4 | `utcnow()`, `query.get()` | MEDIUM/LOW |
| Magic numbers e código morto | descontos, imports | import morto | constantes e serviços não usados | LOW |

**Conclusões que orientam o desenho da skill:**

1. **Detecção precisa ser por sinal, não por nome de arquivo.** O projeto 3 tem `models/`, `routes/` e
   `services/` e mesmo assim viola MVC — a skill não pode inferir arquitetura pela árvore de diretórios.
2. **A Fase 3 deve se adaptar ao ponto de partida.** Projetos 1 e 2 pedem criação de camadas do zero;
   o projeto 3 pede realocação de responsabilidade dentro de camadas que já existem, além de eliminar
   código morto (services e helpers não usados).
3. **Código morto é sinal de arquitetura mal aplicada**, não só de limpeza: `Task.is_overdue()`,
   `process_task_data()` e `NotificationService` mostram que houve tentativa de separar camadas que o
   fluxo real ignorou.
4. **Segurança e arquitetura se sobrepõem.** Os achados CRITICAL de segurança (senha no `to_dict()`,
   `/admin/query`) só existem porque não há fronteira entre camadas — corrigi-los é consequência natural
   da refatoração, não um passo separado.

---

## B) Construção da Skill

### Estrutura da skill

```
.claude/skills/refactor-arch/
├── SKILL.md                                  # orquestração das 3 fases (~180 linhas)
└── references/
    ├── 01-project-analysis.md                # heurísticas de detecção (Fase 1)
    ├── 02-antipattern-catalog.md             # 38 anti-patterns (Fase 2)
    ├── 03-audit-report-template.md           # formato do relatório (Fase 2)
    ├── 04-mvc-architecture.md                # regras do alvo MVC (Fase 3)
    └── 05-refactoring-playbook.md            # 19 transformações antes/depois (Fase 3)
```

### Decisões de design

**1. `SKILL.md` é prompt, referências são conhecimento.** O `SKILL.md` contém apenas o procedimento —
o que fazer, em que ordem, o que imprimir, quando parar. Todo o conhecimento de domínio (sinais de
detecção, severidades, exemplos de código) vive nos arquivos de referência, carregados **sob demanda por
fase**. A tabela de referências no `SKILL.md` diz explicitamente *quando* ler cada arquivo, para não
carregar o playbook de refatoração durante uma auditoria que talvez nem seja aprovada.

**2. Cinco princípios inegociáveis no topo.** Antes das fases, o `SKILL.md` fixa as regras que valem
para tudo: nada é modificado antes da confirmação, comportamento preservado, evidência obrigatória
(`arquivo:linha`), adaptação ao ponto de partida e precedência de segurança. São as restrições que o
agente mais tende a relaxar sob pressão de "terminar a tarefa".

**3. O inventário de endpoints é o contrato.** A Fase 1 não serve só para imprimir um resumo bonito:
ela produz a lista completa de endpoints que a Fase 3 tem obrigação de preservar e contra a qual será
validada. Sem esse artefato, "a aplicação continua funcionando" vira opinião.

**4. Baseline antes de editar (Fase 3.0).** A skill sobe a aplicação **original** e registra status e
formato de resposta de cada endpoint antes de tocar em qualquer arquivo. É o que transforma a validação
final em comparação objetiva em vez de "parece que subiu".

**5. Severidade com regra de ajuste explícita.** Além da tabela do desafio, o catálogo define quando
subir ou descer um nível (caminho crítico de dinheiro/credenciais, defeito sistêmico vs pontual, código
morto) — evita tanto a inflação de severidade quanto o inverso.

**6. Portão de confirmação como fim de turno.** A Fase 2 termina imprimindo o prompt `[y/n]` e
**encerrando o turno**. Instruir "peça confirmação" sem instruir "pare aqui" costuma resultar em um
agente que pergunta e responde a si mesmo na linha seguinte.

### Anti-patterns do catálogo e por quê

38 anti-patterns em 5 famílias (mínimo exigido: 8). A seleção saiu diretamente da análise manual — cada
entrada foi observada em pelo menos um dos três projetos, com os sinais de detecção derivados do código
real, não de listas genéricas de code smell.

| Família | Qtd. | Por que entrou |
|---|:--:|---|
| **SEC** (01–09) | 9 | Os três projetos concentram seus achados CRITICAL em segurança, e todos derivam da falta de fronteira entre camadas — corrigi-los é consequência da refatoração |
| **ARCH** (01–12) | 12 | Núcleo do desafio: God Class, negócio no controller, dados no controller, apresentação no model, estado global, ausência de DI e de composition root, fronteira transacional, contrato de erro |
| **PERF** (01–05) | 5 | N+1 aparece nos três projetos; integridade referencial e cache sem limite vieram do projeto 2 |
| **QUAL** (01–09) | 9 | Duplicação, exceção engolida, callback hell, magic numbers, `print` como log, código morto, nomenclatura |
| **DEP** (01–03) | 3 | Requisito explícito: APIs deprecated com equivalente moderno — tabelas para stdlib, framework/ORM e dependências superadas |

Distribuição de severidade: **CRITICAL** 8 · **HIGH** 11 · **MEDIUM** 12 · **LOW** 7.

Três entradas merecem destaque porque não aparecem em catálogos convencionais e vieram da análise
manual do projeto 3:

- **ARCH-11 — Camada nominal.** Pasta não é camada. `task-manager-api` tem `models/`, `routes/`,
  `services/` e viola MVC integralmente. Sem esse anti-pattern, uma auditoria automatizada classificaria
  o projeto como "já organizado" e não encontraria nada.
- **ARCH-12 — Abstração morta.** `Task.is_overdue()`, `process_task_data()` e `NotificationService`
  existem e ninguém chama, enquanto as rotas reimplementam a mesma lógica. Código morto aqui não é
  sujeira — é a prova de que a camada certa foi projetada e ignorada.
- **ARCH-08 — Ausência de fronteira transacional.** Classificado como CRITICAL por causa do checkout do
  projeto 2: uma falha no meio da cadeia deixa aluno matriculado sem pagamento registrado.

### Como garanti que a skill é agnóstica de tecnologia

| Estratégia | Implementação |
|---|---|
| **Detecção por manifesto, não por extensão** | Tabela de 10 manifestos (`requirements.txt`, `package.json`, `go.mod`, `pom.xml`, `Gemfile`, `composer.json`, `Cargo.toml`…) → linguagem, com os imports do código como confirmação |
| **Sinais em duas formas** | Cada anti-pattern lista o sinal em pelo menos duas sintaxes (Python e JS/TS) e, quando cabe, o padrão `grep` genérico — ex.: SQL Injection cobre `+`, `%`, `.format()`, f-string e template literal |
| **Vocabulário de camada, não de framework** | As regras falam em "camada de roteamento", "acesso a dados", "efeito colaterais"; a tabela de correspondência traduz para Blueprint/Router/`@Controller`/`urlpatterns` |
| **Playbook bilíngue** | As 19 transformações alternam exemplos Python e JavaScript de propósito — o padrão é o mesmo, muda o vocabulário |
| **Estrutura-alvo adaptativa** | A Fase 3 classifica o ponto de partida em 4 níveis (A monolito plano → D MVC adequado) e prescreve estratégia diferente para cada um, incluindo "não reestruture o que já está certo" |
| **Convenção do projeto prevalece** | Em projeto que já usa `routes/` e `services/`, a skill mantém a nomenclatura em vez de renomear para `views/`/`controllers/` — renomear pasta custa mais do que entrega |

### Desafios encontrados e como resolvi

**Desafio 1 — "Já tem pastas MVC" ≠ "é MVC".** A primeira versão do catálogo detectava arquitetura pela
árvore de diretórios, o que daria zero findings arquiteturais no projeto 3. **Solução:** a Referência 1
mapeia responsabilidades **por arquivo** (8 categorias: roteamento, HTTP I/O, validação, negócio, dados,
apresentação, infra, config) e classifica pelo que o código faz. Um arquivo com 4+ responsabilidades é
God Class, esteja ele em `routes/` ou na raiz. Daí nasceu o ARCH-11.

**Desafio 2 — a mesma transformação não serve para monolito e para projeto semi-organizado.** Aplicar a
árvore-alvo completa em `task-manager-api` significaria renomear `routes/` para `views/` sem ganho real.
**Solução:** os 4 níveis de partida (A–D) com estratégia distinta, e uma seção de **anti-regras** no
guideline de arquitetura: não criar camada vazia, não trocar framework/banco, não implementar
funcionalidade nova sob o nome de refatoração, não dividir arquivo pequeno de responsabilidade única.

**Desafio 3 — provar que "não quebrou" sem suíte de testes.** Nenhum dos três projetos tem testes.
**Solução:** o baseline da Fase 3.0 (golden master informal) — status code e formato de resposta de cada
endpoint capturados antes das alterações, comparados depois, incluindo pelo menos um caminho de erro
(400 e 404).

**Desafio 4 — onde termina refatoração e começa feature.** "Autenticação falsa" é achado CRITICAL, mas
implementar JWT completo é funcionalidade nova, não refatoração. **Solução:** o RF-19 delimita
explicitamente — remover a superfície indefensável, parar de simular autenticação, deixar o ponto de
extensão pronto (decorator/middleware) e registrar a implementação completa na seção "Fora de escopo"
do relatório. O template de relatório tem essa seção obrigatória.

**Desafio 5 — o risco de o agente "pedir confirmação" e continuar.** **Solução:** instrução explícita de
encerrar o turno após o prompt, preferindo `AskUserQuestion`, com a regra reforçada no princípio nº 1 e
repetida na lista de erros comuns do template de relatório.

## C) Resultados

### Resumo dos relatórios de auditoria

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---:|---:|---:|---:|---:|---|
| `code-smells-project` | 7 | 6 | 8 | 5 | **26** | [audit-project-1.md](./reports/audit-project-1.md) |
| `ecommerce-api-legacy` | 6 | 8 | 6 | 5 | **25** | [audit-project-2.md](./reports/audit-project-2.md) |
| `task-manager-api` | 4 | 5 | 9 | 6 | **25** | [audit-project-3.md](./reports/audit-project-3.md) |

### Checklist de Validação

Marcado a partir da execução real da skill em cada projeto. `P1` = `code-smells-project`,
`P2` = `ecommerce-api-legacy`, `P3` = `task-manager-api`.

| Verificação | P1 | P2 | P3 |
|---|:--:|:--:|:--:|
| **Fase 1 — Análise** | | | |
| Linguagem detectada corretamente | ✅ | ✅ | ✅ |
| Framework detectado corretamente | ✅ | ✅ | ✅ |
| Domínio da aplicação descrito corretamente | ✅ | ✅ | ✅ |
| Número de arquivos analisados condiz com a realidade | ✅ | ✅ | ✅ |
| **Fase 2 — Auditoria** | | | |
| Relatório segue o template definido nos arquivos de referência | ✅ | ✅ | ✅ |
| Cada finding tem arquivo e linhas exatos | ✅ | ✅ | ✅ |
| Findings ordenados por severidade (CRITICAL → LOW) | ✅ | ✅ | ✅ |
| Mínimo de 5 findings identificados | ✅ | ✅ | ✅ |
| Detecção de APIs deprecated incluída (se aplicável) | ✅ | ✅ | ✅ |
| Skill pausa e pede confirmação antes da Fase 3 | ✅ | ✅ | ✅ |
| **Fase 3 — Refatoração** | | | |
| Estrutura de diretórios segue padrão MVC | ✅ | ✅ | ✅ |
| Configuração extraída para módulo de config (sem hardcoded) | ✅ | ✅ | ✅ |
| Models criados para abstrair dados | ✅ | ✅ | ✅ |
| Views/Routes separadas para visualização ou roteamento | ✅ | ✅ | ✅ |
| Controllers concentram o fluxo da aplicação | ✅ | ✅ | ✅ |
| Error handling centralizado | ✅ | ✅ | ✅ |
| Entry point claro | ✅ | ✅ | ✅ |
| Aplicação inicia sem erros | ✅ | ✅ | ✅ |
| Endpoints originais respondem corretamente | ✅ * | ✅ | ✅ |

> \* **P1:** 17 dos 19 endpoints originais respondem com status e formato idênticos ao baseline.
> Os outros 2 — `POST /admin/query` (executor de SQL arbitrário) e `POST /admin/reset-db` (reset
> destrutivo, ambos sem autenticação) — foram **removidos deliberadamente**, conforme o finding #2
> do relatório. A remoção é a correção, não uma regressão: mantê-los funcionando significaria deixar
> um backdoor de banco aberto na API.

**Evidência do P1** — cada marca acima corresponde a um resultado verificável:

| Item | Evidência |
|---|---|
| Linguagem / framework | `Python 3.12.0` e `Flask 3.1.1` lidos de `requirements.txt` e confirmados por import |
| Nº de arquivos | `wc -l *.py` → 4 arquivos, 780 linhas |
| Findings com linha exata | 26 findings, todos com `arquivo:linha` verificado por leitura |
| APIs deprecated | seção presente declarando ausência, com as 8 APIs verificadas listadas |
| Pausa antes da Fase 3 | execução interrompida aguardando confirmação; nenhum arquivo modificado até o `y` |
| Config sem hardcoded | grep por segredo literal em `src/` e `app.py` → 0 ocorrências |
| Error handling central | 16 `try/except` removidos; grep por `except` em `src/views/` → 0 |
| Aplicação inicia | log de boot: `carga_inicial_concluida produtos=10 usuarios=3` |
| Endpoints respondem | 24/24 status codes e 10/10 payloads idênticos ao baseline pré-refatoração |

### Critérios de aceite

| Critério | P1 | P2 | P3 |
|---|:--:|:--:|:--:|
| Fase 1 detecta stack corretamente | ✅ | ✅ | ✅ |
| Fase 2 encontra ≥ 5 findings | ✅ (26) | ✅ (25) | ✅ (25) |
| Fase 2 inclui ≥ 1 CRITICAL ou HIGH | ✅ (13) | ✅ (14) | ✅ (9) |
| Fase 3 aplicação funciona após refatoração | ✅ | ✅ | ✅ |

---

### Projeto 1 — `code-smells-project` (Python/Flask)

#### Fase 1 — detecção

```
Language:      Python 3.12.0
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1
Domain:        API de E-commerce (produtos, usuários, pedidos, relatório de vendas)
Architecture:  Monolítica — 4 arquivos na raiz com nomenclatura MVC, sem separação real de camadas
Source files:  4 files analyzed | ~780 lines of code
Persistence:   SQLite (sqlite3 direto, sem ORM)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Endpoints:     19 endpoints mapeados
```

O inventário de endpoints exigiu buscar os dois padrões de registro do Flask: 16 rotas vinham de
`add_url_rule` e apenas 3 de `@app.route`. Uma varredura só por decoradores teria encontrado 3 de 19 —
e a validação da Fase 3 seria contra um contrato incompleto.

#### Fase 2 — auditoria

26 findings, ordenados por severidade, cada um com arquivo e linhas exatos. Os sete CRITICAL:

| # | Finding | Local |
|---|---|---|
| 1 | SQL Injection por concatenação (21 de 27 queries) | `models.py`, 21 pontos |
| 2 | Endpoints administrativos irrestritos (SQL arbitrário + reset destrutivo) | `app.py:47-78` |
| 3 | Dado sensível exposto na resposta (`senha`, `secret_key`) | `controllers.py:284-289`, `models.py:84,99` |
| 4 | Senhas armazenadas em texto plano | `models.py:105-131`, `database.py:75-83` |
| 5 | Segredo hardcoded no código | `app.py:7`, `controllers.py:289` |
| 6 | Autenticação e autorização ausentes | projeto inteiro |
| 7 | God Module — 5 responsabilidades em um arquivo | `models.py:1-314` |

**APIs deprecated:** nenhuma. Verificados explicitamente `datetime.utcnow()`, `imp`, `distutils`,
`@app.before_first_request`, `flask.Markup`, `Model.query.get()` e os adaptadores de data do `sqlite3`
contra Python 3.12.0 / Flask 3.1.1 — o projeto não importa `datetime` e usa `CURRENT_TIMESTAMP` do SQLite.
O relatório declara a ausência em vez de omitir a seção.

A skill pausou após o relatório e aguardou confirmação antes de modificar qualquer arquivo.

#### Fase 3 — antes e depois

| | Antes | Depois |
|---|---|---|
| Arquivos | 4 na raiz | 33 módulos em 8 camadas |
| Linhas | 780 | ~1.100 (com docstrings e validação explícita) |
| Maior arquivo | `models.py` — 314 linhas, 5 responsabilidades | `pedido_model.py` — 115 linhas, 1 responsabilidade |
| SQL | concatenado em 21 pontos, espalhado por 3 arquivos | parametrizado, exclusivamente em `src/models/` e `src/database/` |
| Configuração | `SECRET_KEY` e `DEBUG` no código | `src/config/settings.py` lendo do ambiente + `.env.example` |
| Conexão | global de módulo, `check_same_thread=False` | por requisição, com teardown registrado |
| Erros | 16 `try/except` repetidos vazando `str(e)` | exceções de domínio + um `@app.errorhandler` |
| Senhas | texto plano | `generate_password_hash` + re-hash no login para a base legada |
| Listagem de pedidos | 1 + N + M queries | 1 query com `LEFT JOIN` |
| Relatório de vendas | 5 queries sequenciais | 1 query agregada |
| Notificações | `print()` dentro do controller | `NotificacaoService` injetado |
| Entry point | 88 linhas com rotas, config e SQL | `create_app()` que só monta as camadas |

```
code-smells-project/
├── app.py                     composition root
├── scripts/reset_db.py        substitui POST /admin/reset-db
└── src/
    ├── config/                settings (env) + logging
    ├── database/              conexão por requisição, schema explícito
    ├── models/                produto, usuario, pedido
    ├── controllers/           produto, usuario, pedido, relatorio, health
    ├── views/                 blueprints + dto/
    ├── validators/            common, produto, usuario, pedido
    ├── services/              notificacao_service
    ├── middlewares/           exceptions, error_handler, auth
    └── constants.py
```

#### Validação

Baseline capturado com a **versão original extraída do git**, em banco limpo, antes de qualquer
alteração; o refatorado foi exercitado com a mesma sequência, também em banco limpo.

```
✓ Aplicação inicia sem erros       carga_inicial_concluida produtos=10 usuarios=3
✓ 17/17 endpoints respondem        (19 originais − 2 removidos deliberadamente)
✓ 24/24 status codes idênticos ao baseline
✓ 10/10 payloads de leitura idênticos (timestamps normalizados)
✓ Caminhos de erro preservados     400 validação · 404 inexistente · 401 login
✓ GET /usuarios expõe 'senha':     True → False
✓ GET /health expõe 'secret_key':  True → False
✓ POST /admin/query:               200 → 404 (removido)
✓ Zero anti-patterns CRITICAL/HIGH remanescentes
```

O diff completo entre baseline e resultado tem **uma única linha de divergência** — exatamente o
endpoint que a Fase 3 se propôs a remover:

```diff
- POST /admin/query 200
+ POST /admin/query 404
```

Verificação de anti-patterns residuais por grep: 0 queries concatenadas, 0 rotas administrativas,
0 ocorrências de `senha` em DTO de resposta, 0 segredos literais, 0 SQL fora da camada de dados,
0 `debug=True` hardcoded, 0 `try/except` em rotas, 0 `print()` em código de aplicação.

#### Mudanças de contrato

Oito, todas deliberadas e documentadas no relatório: dois endpoints removidos, dois campos sensíveis
retirados das respostas, normalização de `"sucesso": false` nos erros (a chave `erro` e os status codes
permanecem idênticos), e três correções que tornam a API mais estrita — `PUT /produtos/<id>` passou a
aplicar as validações que só o `POST` fazia, `PUT /pedidos/<id>/status` retorna 404 para pedido
inexistente, e erro de tipo em parâmetro retorna 400 em vez de 500.

---

### Projeto 2 — `ecommerce-api-legacy` (Node.js/Express)

#### Fase 1 — detecção

```
Language:      JavaScript (Node.js v24.18.1, CommonJS)
Framework:     Express 4.18.2 (resolvido para 4.22.1)
Dependencies:  sqlite3 5.1.6
Domain:        LMS / plataforma de cursos (usuários, cursos, matrículas, pagamentos, auditoria)
Architecture:  God Class — 1 classe concentra banco, DDL, seed, rotas, negócio e relatório
Source files:  3 files analyzed | ~180 lines of code
Persistence:   SQLite em memória (:memory:), driver baseado em callbacks, sem ORM
DB tables:     users, courses, enrollments, payments, audit_logs
Endpoints:     3 endpoints mapeados
```

Aqui a heurística de inventário foi testada de outra forma: as três rotas são registradas por
`manager.setupRoutes(app)` — um método de instância. Buscar por `router.` ou `Router()`, o padrão
usual em Express, não encontraria nenhuma.

#### Fase 2 — auditoria

25 findings. Os seis CRITICAL:

| # | Finding | Local |
|---|---|---|
| 1 | Segredos de produção hardcoded (chave `pk_live_`) | `src/utils.js:1-7` |
| 2 | Número de cartão e chave do gateway em log | `src/AppManager.js:45` |
| 3 | Hash de senha caseiro e reversível (`badCrypto`) | `src/utils.js:17-23` |
| 4 | God Class — 7 responsabilidades em 141 linhas | `src/AppManager.js:1-141` |
| 5 | Checkout sem fronteira transacional | `src/AppManager.js:50-63` |
| 6 | Rotas administrativa e destrutiva sem autenticação | `src/AppManager.js:80,131` |

**APIs deprecated:** nenhuma de linguagem ou framework — o código já usa `Buffer.from()` e
`express.json()`, as formas modernas. O que existe é dívida de **dependência** (DEP-03): `sqlite3`
baseado em callbacks (causa raiz dos findings #5, #8, #9 e #16) e Express 4. Ambos ficaram como
recomendação: a Fase 3 resolve o problema promisificando o driver, que entrega o mesmo ganho sem
alterar a superfície de dependências.

#### Fase 3 — antes e depois

| | Antes | Depois |
|---|---|---|
| Arquivos | 3 (`app.js`, `AppManager.js`, `utils.js`) | 24 módulos em 9 camadas |
| Maior arquivo | `AppManager.js` — 141 linhas, 7 responsabilidades | `checkout.controller.js` — 63 linhas, 1 |
| Indentação máx. do checkout | **36 espaços** (5 níveis de callback) | **16 espaços** |
| Transação | nenhuma — 4 escritas encadeadas | `db.transaction()` com rollback |
| Hash de senha | base64 truncado em 10 chars, sem salt | `crypto.scryptSync` com salt e comparação em tempo constante |
| Gateway | `cc.startsWith("4")` inline no handler | `FakePaymentGateway` injetado |
| Relatório financeiro | 1 + N + 2M queries, contadores manuais | 1 query com `JOIN` |
| Integridade | sem FK, registros órfãos ao deletar | FKs com `ON DELETE CASCADE` |
| Persistência | `:memory:` fixo no código | `DATABASE_PATH` configurável |
| Erros | `err` ignorado, sem middleware | erros de domínio + error handler + `asyncHandler` |
| Log | `console.log` com PAN e chave | logger estruturado, só os 4 últimos dígitos |

#### Validação

```
✓ Aplicação inicia sem erros          {"msg":"servidor_iniciado","port":3000}
✓ 3/3 endpoints respondem
✓ 7/7 status codes idênticos ao baseline
✓ Relatório financeiro idêntico ao original (comparação com ambos ordenados)
✓ Cartão em log:                      antes sim → agora não
✓ Registros órfãos após DELETE:       antes true → agora false
✓ Zero anti-patterns CRITICAL/HIGH remanescentes
```

Dois detalhes que só apareceram por comparar execução real, não código:

**A ordem do relatório era não-determinística.** Duas execuções do baseline devolveram os cursos em
ordens diferentes — efeito direto dos contadores manuais (`coursesPending--`) decidindo a hora de
responder conforme os callbacks retornavam. O refatorado ordena por id do curso; comparando ambos
os lados ordenados, o conteúdo é idêntico.

**A corrupção de dados do finding #13 é visível no relatório.** Antes e depois de
`DELETE /api/users/1`:

```
antes  → [{"course":"Clean Architecture","revenue":997,"students":[{"student":"Unknown","paid":997}]}, ...]
depois → [{"course":"Clean Architecture","revenue":0,"students":[]}, ...]
```

A versão original continuava somando receita de matrículas cujo aluno não existia mais.

### Projeto 3 — `task-manager-api` (Python/Flask + SQLAlchemy)

#### Fase 1 — detecção

```
Language:      Python 3.12.0
Framework:     Flask 3.0.0
Dependencies:  flask-sqlalchemy 3.1.1, sqlalchemy 2.0.52, flask-cors 4.0.0,
               marshmallow 3.20.1 (declarada, nunca importada),
               python-dotenv 1.0.0 (declarada, nunca importada)
Domain:        API de Task Manager (tasks, users, categories, relatórios de produtividade)
Architecture:  Separação NOMINAL — existem models/, routes/, services/ e utils/, mas as
               responsabilidades vazam entre elas; services/ e metade de utils/ são código morto
Source files:  15 files analyzed | ~1.158 lines of code
Endpoints:     22 endpoints mapeados
```

Um efeito colateral apareceu já na Fase 1: **importar `app.py` para listar as rotas criou o arquivo
`instance/tasks.db`**. A criação de schema era efeito colateral do import, não de um comando —
virou o finding #7, descoberto por acidente enquanto se fazia o inventário.

#### Fase 2 — auditoria

25 findings. Os quatro CRITICAL:

| # | Finding | Local |
|---|---|---|
| 1 | Hash de senha vazado na resposta da API | `models/user.py:16-25` → 4 endpoints |
| 2 | Senhas com MD5 e sem salt | `models/user.py:29,32` |
| 3 | Autenticação simulada (`fake-jwt-token-<id>`); API 100% aberta | `routes/user_routes.py:210` |
| 4 | Segredos hardcoded (`SECRET_KEY` e credenciais SMTP) | `app.py:13`, `services/notification_service.py:7-10` |

**Este é o projeto que justifica os anti-patterns ARCH-11 e ARCH-12 do catálogo.** Uma auditoria que
inferisse arquitetura pela árvore de diretórios olharia `models/ routes/ services/ utils/` e
concluiria "já está organizado". A varredura por responsabilidade encontrou o oposto:

- **ARCH-11 (camada nominal):** `create_task` tem 70 linhas e faz parsing, 8 validações, 2 consultas
  de integridade, persistência e serialização. `summary_report` tem 90 linhas de agregação dentro do
  handler HTTP.
- **ARCH-12 (abstração morta):** busca por referências em todo o projeto — `Task.is_overdue()`: **0
  chamadas** (a mesma regra reescrita 6× nas rotas); `process_task_data()`: **0**; `NotificationService`:
  **0** (o pacote `services/` não é importado por ninguém); 5 helpers e 7 constantes: **0**.

**APIs deprecated:** aqui, ao contrário dos projetos 1 e 2, **há uso ativo** — `datetime.utcnow()`
(17 ocorrências, deprecado no Python 3.12) e `Model.query.get()` (16 ocorrências, legado no
SQLAlchemy 2.0, que é a versão instalada).

#### Fase 3 — estratégia diferente: nível B

Este foi o único projeto em que a estratégia da Fase 3 mudou. Projetos 1 e 2 eram monolitos planos
(nível A) e receberam a árvore inteira do zero. Aqui já existia uma árvore coerente, então a skill
**manteve `models/`, `routes/`, `services/` e `utils/` com os nomes originais** e apenas adicionou o
que faltava — renomear `routes/` para `views/` custaria mais do que entregaria.

| | Antes | Depois |
|---|---|---|
| Arquivos | 15, com camadas nominais | 30 módulos, uma responsabilidade cada |
| Maior handler | `summary_report` — 90 linhas | 12 linhas |
| `Task.is_overdue()` | existia, 0 chamadas | fonte única, usada pelos 3 DTOs |
| Validação | duplicada POST/PUT + 1 versão morta | `validators/` compartilhado |
| `services/` | 0 imports, com senha SMTP no construtor | adotado, remetente injetado, sem credenciais |
| Senha | MD5 sem salt, exposta na resposta | hash com salt, fora de qualquer DTO |
| `/reports/summary` | 12 `COUNT` + 1 query por usuário | 2 `GROUP BY` + 1 agregação |
| `GET /tasks` | 2 queries extras por task | `joinedload` |
| `datetime.utcnow()` | 17 ocorrências | 0 |
| `Model.query.get()` | 16 ocorrências | 0 |
| Criar schema | efeito colateral do import | `scripts/init_db.py` |

Cada símbolo morto recebeu decisão explícita — **adotar ou remover, nunca manter os dois**.
`is_overdue`, `NotificationService`, `validate_email`, `sanitize_string`, `is_valid_color` e as 7
constantes foram **adotados**; `process_task_data`, `generate_id` e `log_action` foram **removidos**.
A tabela completa está no relatório.

#### Validação

```
✓ Aplicação inicia sem erros
✓ 22/22 endpoints registrados
✓ 35/35 status codes idênticos ao baseline
✓ 18/18 payloads de leitura idênticos (timestamps normalizados)
✓ GET /users/1 expõe 'password':   True → False
✓ POST /login expõe 'token':       True → False
✓ Import puro de app.py cria banco: True → False
✓ Cascade de deleção equivalente:   ambos 10 tasks → 7 após DELETE /users/3
```

A comparação de payload incluiu `/reports/summary` e `/tasks/stats` de propósito: são os dois pontos
onde trocar 12 `COUNT` sequenciais por `GROUP BY` poderia ter mudado um número. Nenhum mudou.

#### Um finding deliberadamente não corrigido

O finding #25 (senha mínima de 4 caracteres) **não foi alterado**. Elevar o mínimo mudaria o resultado
de requisições hoje aceitas — é decisão de política de produto, não refatoração. O risco real que o
finding apontava vinha da combinação com MD5 sem salt, que foi corrigida. A constante agora existe em
um único lugar, com a recomendação registrada; elevá-la virou uma alteração de uma linha.

---

### Logs das aplicações rodando após a refatoração

Saída real das três aplicações, capturada após o commit da refatoração, com banco recém-criado.

#### Projeto 1 — `code-smells-project`

```console
$ SECRET_KEY=exemplo-local PORT=5001 python app.py
2026-08-13 14:59:09 INFO  src.database.schema | carga_inicial_concluida produtos=10 usuarios=3
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5001
2026-08-13 14:59:14 INFO  werkzeug | 127.0.0.1 - - "GET /health HTTP/1.1" 200 -
2026-08-13 14:59:14 INFO  werkzeug | 127.0.0.1 - - "GET /produtos HTTP/1.1" 200 -
```
```console
GET /health              200  {"counts": {"pedidos": 0, "produtos": 10, "usuarios": 3},
                                "database": "connected", "status": "ok", "versao": "1.0.0"}
GET /produtos            200  {"dados": [{"ativo": 1, "categoria": "informatica", ...}], "sucesso": true}
GET /relatorios/vendas   200  {"dados": {"desconto_aplicavel": 0.0, "faturamento_bruto": 0, ...}, "sucesso": true}
```

O `/health` não devolve mais `secret_key`, `db_path`, `debug` nem `ambiente` — antes os quatro
apareciam no JSON público.

#### Projeto 2 — `ecommerce-api-legacy`

```console
$ npm start
{"ts":"2026-08-13T17:59:27.894Z","level":"info","msg":"carga_inicial_concluida","usuarios":1,"cursos":2}
{"ts":"2026-08-13T17:59:27.899Z","level":"info","msg":"servidor_iniciado","port":3000,"env":"development"}
{"ts":"2026-08-13T17:59:30.857Z","level":"info","msg":"pagamento_processado","status":"PAID",
 "amount":497,"cartao_final":"4444","gateway":"fake"}
{"ts":"2026-08-13T17:59:30.902Z","level":"info","msg":"checkout_concluido","enrollment_id":2,"course_id":2}
```
```console
POST /api/checkout                200  {"msg":"Sucesso","enrollment_id":2}
GET  /api/admin/financial-report  200  [{"course":"Clean Architecture","revenue":997,
                                         "students":[{"student":"Leonan","paid":997}]}, ...]
```

Este log é a evidência mais direta da correção do finding #2. A mesma operação, na versão original,
imprimia:

```console
Processando cartão 4111222233334444 na chave pk_live_1234567890abcdef
```

Agora registra `"cartao_final":"4444"` e nenhuma chave de gateway.

#### Projeto 3 — `task-manager-api`

```console
$ python scripts/init_db.py
Schema criado em sqlite:///tasks.db

$ python seed.py
Seed concluído com sucesso!
  3 usuários
  4 categorias
  10 tasks

$ SECRET_KEY=exemplo PORT=5003 python app.py
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5003
2026-08-13 14:59:49 INFO  werkzeug | 127.0.0.1 - - "GET /health HTTP/1.1" 200 -
```
```console
GET /health        200  {"status": "ok", "timestamp": "2026-08-13 17:59:49.822677"}
GET /tasks/stats   200  {"cancelled": 1, "completion_rate": 10.0, "done": 1, "in_progress": 2,
                         "overdue": 2, "pending": 6, "total": 10}
GET /users/1       200  {"active": true, "created_at": "...", "email": "joao@email.com",
                         "id": 1, "name": "João Silva", "role": "admin", "tasks": [...]}
```

Duas coisas visíveis aqui: `GET /users/1` não traz mais o campo `password`, e criar o schema virou um
comando explícito (`scripts/init_db.py`) — antes acontecia sozinho ao importar `app.py`.

---

### Observações sobre o comportamento da skill em stacks diferentes

**O que se manteve idêntico nos três projetos.** A skill foi copiada sem uma única alteração entre os
projetos 1, 2 e 3 — mesmo `SKILL.md`, mesmos 5 arquivos de referência. As três fases, o portão de
confirmação, o formato do relatório e a estrutura da validação funcionaram sem adaptação manual.

**O que a skill teve de adaptar sozinha.**

| Dimensão | Projeto 1 (Flask puro) | Projeto 2 (Express) | Projeto 3 (Flask + ORM) |
|---|---|---|---|
| Nível de partida detectado | A — monolito plano | A — monolito plano | **B — separação nominal** |
| Estratégia da Fase 3 | criar toda a árvore | criar toda a árvore | **manter a árvore, realocar responsabilidade** |
| Achado dominante | SQL Injection sistêmico | callback hell + ausência de transação | camada nominal + abstração morta |
| APIs deprecated | nenhuma | nenhuma (só dependências superadas) | **2 em uso ativo, 33 ocorrências** |
| Nomenclatura alvo | `views/` (criada) | `routes/` (convenção Node) | `routes/` (**preservada do original**) |

**Três aprendizados concretos:**

1. **O inventário de endpoints precisou de heurística diferente em cada projeto.** No projeto 1, 16
   das 19 rotas vinham de `add_url_rule` e só 3 de `@app.route`. No projeto 2, as 3 rotas eram
   registradas por um método de instância (`manager.setupRoutes(app)`), invisível para uma busca por
   `Router()`. Em ambos, procurar apenas o padrão idiomático teria produzido um contrato incompleto —
   e a validação da Fase 3 seria contra o contrato errado.

2. **Detecção por sinal, não por estrutura, foi o que fez o projeto 3 funcionar.** É o único dos três
   em que uma inspeção superficial diria "já está em MVC". Os 25 findings só apareceram porque o
   catálogo mapeia responsabilidade por arquivo em vez de confiar em nome de pasta.

3. **A regra "não implemente funcionalidade nova" foi acionada nos três.** Autenticação real ficou de
   fora nos três projetos, com o ponto de extensão pronto e o gap registrado. No projeto 2, a troca de
   `sqlite3` por `node:sqlite` foi recomendada e não executada. No projeto 3, a política de senha não
   foi endurecida. Em todos os casos a decisão está escrita no relatório, não implícita na omissão.

**O que a comparação com baseline pegou e a leitura de código não pegaria.** No projeto 2, a ordem do
relatório financeiro era não-determinística — duas execuções da mesma versão original devolveram
ordens diferentes, efeito dos contadores manuais de callback. Isso só apareceu porque a validação
executava a aplicação em vez de inspecionar o diff.

## D) Como Executar

### Pré-requisitos

- [Claude Code](https://claude.com/claude-code) instalado e autenticado
- Python 3.10+ (projetos 1 e 3) e Node.js 18+ (projeto 2)

### Invocando a skill

A skill vive em `.claude/skills/refactor-arch/` dentro de cada projeto e é invocada a partir da raiz
do projeto que se quer refatorar:

```bash
cd code-smells-project
claude "/refactor-arch"
```

O fluxo é interativo: a Fase 1 imprime a análise, a Fase 2 imprime o relatório de auditoria e **pausa
pedindo confirmação**, e a Fase 3 só executa após o `y`. O relatório é salvo em `reports/`.

### Rodando o projeto 1 refatorado

```bash
cd code-smells-project
python -m venv .venv && .venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                                 # ajuste SECRET_KEY
python app.py
```

A API sobe em `http://127.0.0.1:5000`. Para resetar o banco (substitui o antigo endpoint destrutivo):

```bash
python scripts/reset_db.py --confirmar
```

### Validando a refatoração

Para reproduzir a validação — comparar o comportamento antes e depois:

```bash
# 1. extrair a versão original do git para um diretório temporário
mkdir /tmp/orig && cd /tmp/orig
for f in app.py controllers.py models.py database.py; do
  git -C /caminho/do/repo show 6d1ce62:code-smells-project/$f > $f
done
python -c "from app import app; app.run(port=5002)" &

# 2. subir o refatorado em outra porta
cd /caminho/do/repo/code-smells-project && PORT=5001 python app.py &

# 3. comparar status codes e payloads dos dois
```

O commit `6d1ce62` é o boilerplate original. A validação executada nesta entrega comparou 24 casos de
requisição (incluindo caminhos de erro) e 10 payloads de leitura.
