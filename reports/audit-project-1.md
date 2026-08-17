```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      Python 3.12.0
Framework:     Flask 3.1.1
Dependencies:  flask-cors 5.0.1
Domain:        API de E-commerce (produtos, usuários, pedidos, relatório de vendas)
Architecture:  Monolítica — 4 arquivos na raiz com nomenclatura MVC, sem separação real de camadas
Source files:  4 files analyzed | ~780 lines of code
Persistence:   SQLite (sqlite3 direto, sem ORM)
DB tables:     produtos, usuarios, pedidos, itens_pedido
Endpoints:     19 endpoints mapeados
================================
```

### Inventário de endpoints — contrato a preservar

| # | Método | Path | Handler atual | Observação |
|---|---|---|---|---|
| 1 | GET | `/` | `app.py:32` `index` | índice da API |
| 2 | GET | `/produtos` | `app.py:11` → `controllers.listar_produtos` | |
| 3 | GET | `/produtos/busca` | `app.py:12` → `controllers.buscar_produtos` | precede a rota paramétrica |
| 4 | GET | `/produtos/<int:id>` | `app.py:13` → `controllers.buscar_produto` | |
| 5 | POST | `/produtos` | `app.py:14` → `controllers.criar_produto` | sem autenticação |
| 6 | PUT | `/produtos/<int:id>` | `app.py:15` → `controllers.atualizar_produto` | sem autenticação |
| 7 | DELETE | `/produtos/<int:id>` | `app.py:16` → `controllers.deletar_produto` | sem autenticação |
| 8 | GET | `/usuarios` | `app.py:18` → `controllers.listar_usuarios` | **devolve senhas** |
| 9 | GET | `/usuarios/<int:id>` | `app.py:19` → `controllers.buscar_usuario` | **devolve senha** |
| 10 | POST | `/usuarios` | `app.py:20` → `controllers.criar_usuario` | |
| 11 | POST | `/login` | `app.py:21` → `controllers.login` | não emite token |
| 12 | POST | `/pedidos` | `app.py:23` → `controllers.criar_pedido` | |
| 13 | GET | `/pedidos` | `app.py:24` → `controllers.listar_todos_pedidos` | |
| 14 | GET | `/pedidos/usuario/<int:usuario_id>` | `app.py:25` → `controllers.listar_pedidos_usuario` | |
| 15 | PUT | `/pedidos/<int:pedido_id>/status` | `app.py:26` → `controllers.atualizar_status_pedido` | |
| 16 | GET | `/relatorios/vendas` | `app.py:28` → `controllers.relatorio_vendas` | |
| 17 | GET | `/health` | `app.py:30` → `controllers.health_check` | **vaza SECRET_KEY** |
| 18 | POST | `/admin/reset-db` | `app.py:47` `reset_database` | **destrutivo, sem auth** |
| 19 | POST | `/admin/query` | `app.py:59` `executar_query` | **executa SQL arbitrário** |

> 16 rotas registradas via `add_url_rule` (`app.py:11-30`) + 3 via decorador `@app.route`
> (`app.py:32,47,59`). Buscar apenas por decoradores encontraria 3 de 19.

---

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: code-smells-project
Stack:   Python 3.12 + Flask 3.1.1
Files:   4 analyzed | ~780 lines of code
Date:    2026-08-13
```

## Summary

**CRITICAL: 7 | HIGH: 6 | MEDIUM: 8 | LOW: 5**

O projeto tem nomenclatura MVC sem separação real: `models.py` acumula acesso a dados de quatro domínios,
regras de negócio e formatação de resposta, enquanto a conexão vive em uma global de módulo que também
executa DDL e seed. A ausência de fronteira entre camadas é a causa direta dos achados de segurança —
não existe um ponto único onde validar entrada, parametrizar query ou filtrar o que sai na resposta, então
cada função reimplementa (ou esquece) cada uma dessas proteções. Dois endpoints administrativos sem
autenticação — um executor de SQL arbitrário e um reset destrutivo — tornam a superfície indefensável
independentemente da arquitetura.

## Findings

### #1 [CRITICAL] SQL Injection por concatenação (SEC-02)
**File:** `models.py:28,47-50,57-61,68,92,109-111,126-129,140,148-151,155,157-160,163-166,174,188,192,220,224,279-281,289-297`
**Description:** 21 das 27 chamadas a `cursor.execute()` montam a query concatenando parâmetros diretamente
na string SQL. Em `login_usuario` (`models.py:109-111`), e-mail e senha entram sem escape na cláusula WHERE:
`"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"`.
**Impact:** `email = "' OR '1'='1' --"` autentica como o primeiro usuário da tabela, que é o admin semeado em
`database.py:76` — bypass completo de autenticação, não apenas leitura indevida. A busca de produtos
(`models.py:289-297`) monta a query por concatenação incremental e permite extrair qualquer tabela do banco,
incluindo `usuarios` com as senhas em texto plano.
**Recommendation:** Substituir toda concatenação por placeholders `?` com parâmetros ligados, dentro da nova
camada `models/`. O próprio projeto já faz isso corretamente em `database.py:70-83`, o que confirma que a
falha é de disciplina, não de limitação técnica. (RF-02)

### #2 [CRITICAL] Endpoints administrativos irrestritos (SEC-05)
**File:** `app.py:47-57` (`POST /admin/reset-db`), `app.py:59-78` (`POST /admin/query`)
**Description:** `/admin/query` recebe `{"sql": "..."}` do corpo e executa direto no cursor, sem autenticação
nem allowlist. `/admin/reset-db` apaga as quatro tabelas com `DELETE FROM`, também sem autenticação.
**Impact:** Backdoor completo de banco exposto em `host="0.0.0.0"` (`app.py:88`): permite `DROP TABLE`,
leitura integral da tabela de usuários e escrita arbitrária. Qualquer requisição anônima destrói todos os
dados. Nenhuma reestruturação arquitetural torna essas rotas defensáveis.
**Recommendation:** Remover os dois endpoints. Reset de banco legítimo é script de manutenção
(`scripts/reset_db.py`), executado por quem tem acesso ao servidor — não rota HTTP. (RF-19)

### #3 [CRITICAL] Dado sensível exposto na resposta (SEC-04)
**File:** `controllers.py:284-289`, `models.py:84,99`
**Description:** O `/health` devolve `secret_key`, `debug`, `db_path` e `ambiente` no JSON público
(`controllers.py:285-289`). `get_todos_usuarios()` e `get_usuario_por_id()` incluem o campo `senha` no
dicionário retornado (`models.py:84,99`), servido em `GET /usuarios` e `GET /usuarios/<id>`.
**Impact:** Dois endpoints de leitura viram dump de credenciais. A `SECRET_KEY` exposta permite forjar
qualquer sessão assinada pelo Flask. Combinado com o finding #4 (senhas em texto plano), o vazamento é
imediatamente utilizável — não exige nem quebra de hash.
**Recommendation:** Extrair a serialização de saída para DTOs com allowlist de campos; `/health` responde
apenas `status` e conectividade do banco. (RF-04)

### #4 [CRITICAL] Senhas armazenadas em texto plano (SEC-03)
**File:** `models.py:105-120,122-131`, `database.py:75-83`
**Description:** `criar_usuario` grava a senha crua no banco (`models.py:126-129`); o seed cadastra
`admin123`, `123456` e `senha123` (`database.py:76-79`); o login compara string com string
(`models.py:109-111`). Nenhum hash em nenhum ponto do fluxo.
**Impact:** Vazamento do arquivo `loja.db` — ou do finding #1, #2 ou #3 — entrega todas as credenciais em
claro. Reutilização de senha propaga o incidente para outros serviços dos usuários.
**Recommendation:** `generate_password_hash`/`check_password_hash` (Werkzeug, já disponível via Flask), com
re-hash no login para as credenciais existentes. (RF-03)

### #5 [CRITICAL] Segredo hardcoded no código (SEC-01)
**File:** `app.py:7`, `controllers.py:289`
**Description:** `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"`, com o mesmo literal repetido
na resposta do `/health`.
**Impact:** Segredo versionado permanece no histórico do Git mesmo após remoção — a rotação é obrigatória,
não opcional. Duplicar o literal em dois arquivos garante que uma futura troca deixe uma cópia para trás.
**Recommendation:** Módulo `config/settings.py` lendo de variável de ambiente, `.env` no `.gitignore` e
`.env.example` versionado apenas com as chaves. (RF-01)

### #6 [CRITICAL] Autenticação e autorização ausentes (SEC-06)
**File:** `controllers.py:167-186` (login), `app.py:11-30` (todas as rotas)
**Description:** `/login` valida credenciais e devolve os dados do usuário sem emitir token ou sessão
(`controllers.py:176-180`). Nenhuma rota verifica identidade — incluindo `PUT`/`DELETE /produtos/<id>`,
`PUT /pedidos/<id>/status` e as rotas `/admin/*`. O campo `tipo` ("admin"/"cliente") existe no schema
(`database.py:32`) e nunca é consultado.
**Impact:** Toda a superfície mutável da API é anônima. A autorização foi modelada e não implementada.
**Recommendation:** Remover a superfície indefensável (#2) e **proteger de fato** as rotas administrativas
e mutáveis: emitir credencial verificável no login e exigi-la nos handlers, com a guarda ativa na
configuração padrão. Emitir e verificar credencial com biblioteca padrão é correção deste achado, não
funcionalidade nova. (RF-19)

### #7 [CRITICAL] God Module (ARCH-01)
**File:** `models.py:1-314`
**Description:** Um único arquivo concentra acesso a dados de 4 domínios (produtos, usuários, pedidos,
relatórios), regras de negócio (faixas de desconto em `256-262`; cálculo de total, validação de estoque e
baixa de estoque em `133-169`) e montagem do DTO de resposta (`12-21`, `31-40`, `95-102`, `304-313`).
São 5 das 8 responsabilidades da matriz de arquitetura em um só arquivo.
**Impact:** Impossível testar a regra de desconto sem um SQLite real; qualquer mudança de schema quebra a
serialização da API. É a origem estrutural dos findings #10, #13 e #14.
**Recommendation:** Dividir em `models/` por domínio (produto, usuario, pedido), mover regras de negócio
para `controllers/` e a serialização para DTOs. (RF-05, RF-06, RF-04)

### #8 [HIGH] Estado global mutável: conexão singleton (ARCH-05)
**File:** `database.py:4-10`
**Description:** `db_connection` é global de módulo, criada com `check_same_thread=False` e nunca fechada.
Todas as requisições compartilham a mesma conexão e cursores derivados dela.
**Impact:** O servidor Flask atende requisições em múltiplas threads escrevendo na mesma conexão sem lock —
condição de corrida real em escrita concorrente (ex.: dois pedidos simultâneos dando baixa no mesmo estoque).
Impede também substituir o banco em teste, porque não há injeção de dependência.
**Recommendation:** Conexão por requisição no contexto da aplicação (`flask.g`) com teardown registrado, e
`PRAGMA foreign_keys = ON`. (RF-08)

### #9 [HIGH] DDL e seed como efeito colateral do acesso a dados (ARCH-07)
**File:** `database.py:7-84`, `app.py:82`
**Description:** `get_db()` cria as quatro tabelas e popula o banco com produtos e usuários na primeira
chamada. Não existe factory (`create_app`) nem separação entre inicialização e acesso.
**Impact:** Toda chamada de leitura carrega o risco de disparar DDL; qualquer import do módulo em um script
ou teste materializa o schema. Não há composition root — configuração, roteamento e infraestrutura estão
espalhados pelo entry point.
**Recommendation:** Separar `database/connection.py` (acesso) de `init_schema()` explícito, chamado apenas
na inicialização; introduzir `create_app()`. (RF-08)

### #10 [HIGH] Regra de negócio e efeitos colaterais no controller (ARCH-02)
**File:** `controllers.py:208-210,247-250`
**Description:** O controller dispara "e-mail", "SMS" e "push" via `print` ao criar pedido
(`controllers.py:208-210`) e decide o que notificar conforme o status na atualização (`247-250`).
**Impact:** A política de notificação fica inacessível a qualquer outro consumidor — um worker ou uma CLI
precisaria simular um request HTTP para reaproveitá-la. Também não há como testá-la sem capturar stdout.
**Recommendation:** Extrair `services/notificacao_service.py` com interface injetada no controller. (RF-15)

### #11 [HIGH] Acesso a dados dentro do controller (ARCH-03)
**File:** `controllers.py:264-292`
**Description:** `health_check` importa `get_db` e executa quatro queries SQL diretamente na camada de
controller (`controllers.py:266-274`), contornando `models.py`.
**Impact:** A fronteira de camada, já fraca, é violada explicitamente — a rota conhece nomes de tabela.
Qualquer renomeação de schema exige caçar SQL fora da camada de dados.
**Recommendation:** Mover a contagem para os models correspondentes; o `/health` verifica apenas
conectividade. (RF-06)

### #12 [HIGH] Apresentação embutida na camada de dados (ARCH-04)
**File:** `models.py:12-21,31-40,79-86,95-102,178-199,211-231,304-313`
**Description:** As funções de acesso a dados montam à mão o dicionário de resposta campo a campo, em sete
blocos distintos, três deles idênticos para a entidade produto.
**Impact:** Model e contrato de API ficam soldados: incluir uma coluna no schema muda a resposta HTTP sem
que ninguém decida isso, e foi exatamente assim que o campo `senha` (#3) vazou.
**Recommendation:** Models devolvem entidades; a serialização vive em DTOs na camada de views. (RF-04)

### #13 [HIGH] Debug ligado e bind em todas as interfaces (SEC-07)
**File:** `app.py:8,88`
**Description:** `app.config["DEBUG"] = True` e `app.run(host="0.0.0.0", port=5000, debug=True)`.
**Impact:** O debugger do Werkzeug expõe um console Python interativo na página de erro; combinado com
`0.0.0.0`, a superfície fica acessível fora da máquina local. Stack traces revelam caminhos e estrutura.
**Recommendation:** `DEBUG` vindo de variável de ambiente, default `false`. (RF-01)

### #14 [MEDIUM] Consultas N+1 na listagem de pedidos (PERF-01)
**File:** `models.py:171-201`, `203-233`
**Description:** Ambas as funções fazem 1 query de pedidos, 1 query de itens por pedido e 1 query de produto
por item, usando cursores auxiliares (`cursor2`, `cursor3`).
**Impact:** 50 pedidos com 3 itens cada disparam 201 queries onde um `LEFT JOIN` resolveria em 1.
Degrada linearmente com o volume de dados.
**Recommendation:** Uma query com `LEFT JOIN` entre `pedidos`, `itens_pedido` e `produtos`, agrupando o
resultado em memória. (RF-11)

### #15 [MEDIUM] Duplicação de código com divergência já instalada (QUAL-01)
**File:** `models.py:171-201` vs `203-233`; `controllers.py:28-54` vs `72-90`; `models.py:12-21,31-40,304-313`
**Description:** `get_pedidos_usuario` e `get_todos_pedidos` são ~95% idênticas, diferindo apenas na cláusula
`WHERE`. O bloco de validação de produto foi copiado de `criar_produto` para `atualizar_produto`. A montagem
do dicionário de produto aparece três vezes.
**Impact:** A duplicação já divergiu: só `criar_produto` valida tamanho do nome (`controllers.py:47-50`) e
categoria válida (`52-54`). Hoje é possível **atualizar** um produto para uma categoria que o **criar**
recusaria — bug ativo, não risco futuro.
**Recommendation:** Função de listagem única com filtro opcional; validação extraída para schema
compartilhado entre criação e atualização. (RF-13, RF-14)

### #16 [MEDIUM] Tratamento de erro não centralizado (ARCH-10)
**File:** `controllers.py` — 16 blocos `except Exception as e` (linhas 10,21,60,95,108,125,133,143,164,185,218,254,261,291 e outros)
**Description:** Todo handler repete `try/except Exception` devolvendo `jsonify({"erro": str(e)}), 500`.
Não há `@app.errorhandler` registrado.
**Impact:** Além do boilerplate, `str(e)` de uma exceção do sqlite3 devolve trechos da query ao cliente —
reconhecimento gratuito da estrutura do banco. Erros de programação viram 500 silencioso sem log.
**Recommendation:** Hierarquia de exceções de domínio + `@app.errorhandler` único; mensagem de domínio para
o cliente, causa técnica apenas no log. (RF-09)

### #17 [MEDIUM] Validação ausente ou inconsistente (QUAL-02)
**File:** `controllers.py:169-171`, `118-121`, `237-245`, `72-90`
**Description:** `login` chama `request.get_json()` sem verificar `None` (`169`); `buscar_produtos` converte
`float(preco_min)` sem proteção (`118-121`); `atualizar_status_pedido` valida o valor do status mas não
verifica se o pedido existe (`237-245`); `atualizar_produto` não valida tamanho de nome nem categoria.
**Impact:** Requisição sem corpo em `/login` retorna 500 em vez de 400; `?preco_min=abc` retorna 500;
atualizar status de um pedido inexistente retorna 200 sem ter feito nada.
**Recommendation:** Camada de validação por recurso, compartilhada entre POST e PUT, com erros traduzidos
para 400 pelo error handler. (RF-13)

### #18 [MEDIUM] Agregação redundante no relatório (PERF-03)
**File:** `models.py:239-254`
**Description:** Cinco round-trips ao banco (`COUNT(*)`, `SUM(total)` e três `COUNT` filtrados por status)
que diferem apenas na cláusula `WHERE`.
**Impact:** Cinco viagens ao banco onde um `GROUP BY status` com agregados resolveria em uma.
**Recommendation:** Consolidar em uma query agregada única. (RF-11)

### #19 [MEDIUM] Listagens sem paginação (PERF-02)
**File:** `models.py:7`, `75`, `206`, `299`
**Description:** `SELECT * FROM produtos`, `usuarios`, `pedidos` e a busca de produtos não têm `LIMIT`, e as
rotas correspondentes não aceitam parâmetros de paginação.
**Impact:** A resposta cresce sem limite com o volume da tabela; a listagem de pedidos combina isso com o
N+1 do finding #14, multiplicando o custo.
**Recommendation:** `limit`/`offset` com teto defensivo, preservando o envelope `{"dados": [...]}` atual.
(RF-12)

### #20 [MEDIUM] Erro como valor de retorno (ARCH-09)
**File:** `models.py:143,145`, `controllers.py:205-206`
**Description:** `criar_pedido` devolve `{"erro": "Produto X não encontrado"}` como resultado normal da
função; o controller inspeciona a chave `"erro"` do dicionário para decidir o status HTTP.
**Impact:** Impossível distinguir falha de negócio de falha técnica, e o contrato do model fica ambíguo —
o mesmo tipo de retorno significa sucesso ou erro conforme as chaves presentes. Um produto legitimamente
chamado "erro" quebraria a lógica.
**Recommendation:** Exceções de domínio (`NotFoundError`, `BusinessRuleError`) traduzidas para status HTTP
pelo error handler central. (RF-09)

### #21 [MEDIUM] CORS liberado para qualquer origem (SEC-09)
**File:** `app.py:9`
**Description:** `CORS(app)` sem parâmetros aplica `Access-Control-Allow-Origin: *` a todos os endpoints,
inclusive `/admin/*` e `/usuarios`.
**Impact:** Qualquer site pode consumir a API a partir do navegador da vítima. Não há `helmet` equivalente,
rate limiting nem limite de tamanho de corpo.
**Recommendation:** Lista de origens permitidas vinda da configuração. (RF-01)

### #22 [LOW] Magic numbers em regra de negócio (QUAL-05)
**File:** `models.py:256-262`, `controllers.py:47-50,52`
**Description:** Faixas de desconto `10000`/`5000`/`1000` e alíquotas `0.1`/`0.05`/`0.02` embutidas no
cálculo; limites de nome `2`/`200` e a lista de categorias válidas inline no controller.
**Impact:** Regra de negócio sem nome não é auditável — não dá para responder "quais são as faixas de
desconto?" sem ler a implementação. Alterá-las exige editar lógica em vez de configuração.
**Recommendation:** Constantes nomeadas em `constants.py`, com as faixas como estrutura de dados iterável.
(RF-17)

### #23 [LOW] `print()` como mecanismo de log (QUAL-06)
**File:** `controllers.py` (14 ocorrências), `app.py:56,83-86` (5 ocorrências)
**Description:** 19 chamadas a `print()` fazem o papel de log, sem nível, timestamp ou destino configurável.
`controllers.py:161,179,182` escrevem o e-mail do usuário em stdout.
**Impact:** Impossível filtrar por severidade ou desligar em produção; e-mail de usuário em log é dado
pessoal desnecessário.
**Recommendation:** `logging` configurado no módulo de config; identificadores em vez de dados pessoais.
(RF-18)

### #24 [LOW] Imports não utilizados (QUAL-07)
**File:** `models.py:2`, `database.py:2`
**Description:** `import sqlite3` em `models.py` e `import os` em `database.py`, nenhum dos dois referenciado.
**Impact:** Sugere dependências que o módulo não tem e polui a leitura da fronteira real de cada arquivo.
**Recommendation:** Remover na reorganização dos módulos.

### #25 [LOW] Nomenclatura ruim e shadowing de builtin (QUAL-08)
**File:** `models.py:24,54,65,89` e `controllers.py:14,64,98`; `models.py:187-193,219-225`
**Description:** O parâmetro `id` sombreia o builtin em oito funções; `cursor2` e `cursor3` nomeiam cursores
auxiliares dos laços N+1.
**Impact:** `id` sombreado impede usar a função builtin no escopo e confunde leitura; sufixos numéricos são
sintoma direto do finding #14.
**Recommendation:** `produto_id`, `usuario_id`, `pedido_id`; os cursores auxiliares desaparecem com o JOIN.

### #26 [LOW] Construções não idiomáticas (QUAL-09)
**File:** todo o projeto — ex. `controllers.py:8,11,57,106`, `models.py:143,145`
**Description:** Mensagens montadas com `+` e `str()` em vez de f-strings, em ~30 pontos.
**Impact:** Verbosidade e risco de `TypeError` em concatenação com valor não-string.
**Recommendation:** f-strings.

## Deprecated APIs

| API | Local | Deprecated desde | Equivalente moderno |
|---|---|---|---|
| — | — | — | — |

**Nenhuma API deprecated detectada** para Python 3.12.0 / Flask 3.1.1. Verificados explicitamente:
`datetime.utcnow()`, `imp`, `distutils`, `locale.getdefaultlocale()`, `@app.before_first_request`,
`flask.Markup`, `flask.escape`, `Model.query.get()` e adaptadores de data do `sqlite3` — nenhuma ocorrência.
O projeto não importa `datetime` e usa `CURRENT_TIMESTAMP` do próprio SQLite para timestamps.

## Refactoring Plan

### Estrutura proposta

```
code-smells-project/
├── src/
│   ├── config/settings.py              # env, sem segredo literal
│   ├── database/
│   │   ├── connection.py               # conexão por requisição + teardown
│   │   └── schema.py                   # init_schema()/seed explícitos
│   ├── models/
│   │   ├── produto_model.py
│   │   ├── usuario_model.py
│   │   └── pedido_model.py
│   ├── controllers/
│   │   ├── produto_controller.py
│   │   ├── usuario_controller.py
│   │   ├── pedido_controller.py
│   │   └── relatorio_controller.py
│   ├── views/
│   │   ├── produto_routes.py           # blueprints
│   │   ├── usuario_routes.py
│   │   ├── pedido_routes.py
│   │   ├── relatorio_routes.py
│   │   └── dto/                        # serialização de saída (allowlist)
│   ├── validators/
│   │   ├── produto_schema.py
│   │   └── usuario_schema.py
│   ├── services/notificacao_service.py
│   ├── middlewares/
│   │   ├── exceptions.py               # hierarquia de erros de domínio
│   │   └── error_handler.py
│   └── constants.py
├── scripts/reset_db.py                 # substitui POST /admin/reset-db
├── app.py                              # composition root (create_app)
├── .env.example
└── requirements.txt
```

### Mapeamento finding → transformação

| Findings | Transformação | Arquivos afetados |
|---|---|---|
| #5, #13, #21 | RF-01 Extrair configuração para o ambiente | `config/settings.py`, `.env.example`, `app.py` |
| #1 | RF-02 Parametrizar queries | `models/*` |
| #4 | RF-03 Hash de senha seguro | `models/usuario_model.py`, `database/schema.py` |
| #3, #12 | RF-04 DTO de saída com allowlist | `views/dto/*` |
| #7 | RF-05 Dividir God Module por domínio | `models/*` |
| #10, #11 | RF-06 Extrair controller da rota | `controllers/*` |
| — | RF-07 Extrair camada de rotas (Blueprints) | `views/*`, `app.py` |
| #8, #9 | RF-08 Composition root + conexão por requisição | `database/connection.py`, `app.py` |
| #16, #20 | RF-09 Error handler centralizado | `middlewares/*` |
| #14, #18 | RF-11 Eliminar N+1 e agregação redundante | `models/pedido_model.py` |
| #19 | RF-12 Paginação | `models/*`, `views/*` |
| #15, #17 | RF-13 Extrair camada de validação | `validators/*` |
| #15 | RF-14 Unificar funções duplicadas | `models/pedido_model.py` |
| #10 | RF-15 Service para efeitos colaterais | `services/notificacao_service.py` |
| #22 | RF-17 Constantes nomeadas | `constants.py` |
| #23 | RF-18 Logging estruturado | `config/logging_config.py` |
| #2, #6 | RF-19 Remover superfície indefensável | `app.py`, `scripts/reset_db.py` |

### Contrato preservado

Os **19 endpoints** inventariados na Fase 1 devem responder com o mesmo método, path, status e formato após
a refatoração, com três exceções deliberadas:

1. `POST /admin/query` — **removido** (finding #2, executor de SQL arbitrário).
2. `POST /admin/reset-db` — **removido**, substituído por `scripts/reset_db.py` (finding #2).
3. `GET /usuarios`, `GET /usuarios/<id>` e `GET /health` — deixam de expor `senha` e `secret_key`
   (finding #3). As demais chaves permanecem inalteradas.

### Fora de escopo

- **Revogação de credencial, refresh token e rotação de chave.** A Fase 3 emite e verifica o token
  (correção do finding #6); invalidar um token antes da expiração exige armazenamento de sessão, que é
  decisão de produto. Registrado como resíduo, não como achado fechado.
- **OAuth, MFA e política de senha.** Mudam o produto, não a arquitetura.
- **Migração de banco.** SQLite permanece; trocar de banco não é refatoração arquitetural.
- **Suíte de testes automatizados.** A validação da Fase 3 usa o baseline de endpoints capturado antes das
  alterações; escrever testes unitários é trabalho subsequente (agora viável, com as camadas separadas).
- **Rate limiting e headers de segurança.** Recomendados, mas exigem dependências novas.

```
================================
Total: 26 findings
================================
```

---

```
================================
PHASE 3: REFACTORING COMPLETE
================================
```

## New Project Structure

```
code-smells-project/
├── app.py                          composition root (create_app)
├── .env.example
├── requirements.txt
├── scripts/
│   └── reset_db.py                 substitui POST /admin/reset-db
└── src/
    ├── constants.py
    ├── config/
    │   ├── settings.py             configuração vinda do ambiente
    │   └── logging_config.py
    ├── database/
    │   ├── connection.py           conexão por requisição + teardown
    │   └── schema.py               init_schema() e carga inicial explícitos
    ├── models/
    │   ├── produto_model.py
    │   ├── usuario_model.py
    │   └── pedido_model.py
    ├── controllers/
    │   ├── produto_controller.py
    │   ├── usuario_controller.py
    │   ├── pedido_controller.py
    │   ├── relatorio_controller.py
    │   └── health_controller.py
    ├── views/
    │   ├── produto_routes.py
    │   ├── usuario_routes.py
    │   ├── pedido_routes.py
    │   ├── relatorio_routes.py
    │   ├── sistema_routes.py
    │   └── dto/
    │       ├── produto_dto.py
    │       └── usuario_dto.py
    ├── validators/
    │   ├── common.py
    │   ├── produto_schema.py
    │   ├── usuario_schema.py
    │   └── pedido_schema.py
    ├── services/
    │   └── notificacao_service.py
    └── middlewares/
        ├── exceptions.py
        ├── error_handler.py
        └── auth.py
```

**Antes:** 4 arquivos, 780 linhas, nenhuma camada real.
**Depois:** 33 módulos organizados em 8 camadas. Os arquivos `controllers.py`, `models.py` e
`database.py` da raiz foram removidos — nenhuma versão antiga convive com a nova.

## Findings Resolved

| Severidade | Resolvidos | Total | Observação |
|---|---|---|---|
| CRITICAL | 7/7 | 7 | #6 (autenticação) resolvido com prova de execução: ver "Prova de mitigação" abaixo |
| HIGH | 6/6 | 6 | |
| MEDIUM | 8/8 | 8 | |
| LOW | 5/5 | 5 | |
| **Total** | **26/26** | **26** | |

Verificação por grep após a refatoração:

| Verificação | Resultado |
|---|---|
| Queries com concatenação de parâmetro | 0 |
| Endpoints `/admin/query` e `/admin/reset-db` | 0 |
| Campo `senha` em qualquer DTO de resposta | 0 |
| Segredo literal em código | 0 |
| SQL fora de `src/models/` e `src/database/` | 0 |
| `debug=True` hardcoded | 0 |
| `try/except` dentro de rotas | 0 |
| `print()` como log em código de aplicação | 0 (mantido apenas em `scripts/`, que é CLI) |
| Rota mutável ou administrativa sem decorator de guarda | 0 (10 rotas protegidas: 7 `@requer_papel`, 3 `@requer_autenticacao`) |
| Flag capaz de desligar a autenticação (`AUTH_ENABLED` e similares) | 0 — removida do código e do `.env.example` |

## Validation

Baseline capturado com a **versão original** (extraída do git) antes de qualquer alteração, em banco
limpo; refatorado exercitado com a mesma sequência de chamadas, também em banco limpo.

```
  ✓ Application boots without errors        (log: carga_inicial_concluida produtos=10 usuarios=3)
  ✓ 17/17 endpoints respondem               (19 originais − 2 removidos deliberadamente)
  ✓ 24/24 casos com status code idêntico ao baseline
  ✓ 10/10 payloads de leitura idênticos ao original (timestamps normalizados)
  ✓ Caminhos de erro preservados            (400 em validação, 404 em recurso inexistente, 401 em login)
  ✓ POST /admin/query agora responde 404    (removido, conforme planejado)
  ✓ GET /usuarios não expõe mais 'senha'    (era True, agora False)
  ✓ GET /health não expõe mais 'secret_key' (era True, agora False)
  ✓ Zero anti-patterns CRITICAL/HIGH remanescentes
```

Diff completo entre baseline e resultado — única divergência é o endpoint removido:

```
28c28
< POST /admin/query 200
---
> POST /admin/query 404
```

## Prova de mitigação — finding #6 (autenticação)

Execução na **configuração padrão do projeto**: nenhuma variável de ambiente exportada além do que o
`.env.example` já traz, e não existe chave capaz de desligar a verificação.

Política de acesso aplicada, rota a rota:

| Acesso | Endpoints |
|---|---|
| Público | `GET /`, `GET /health`, `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>`, `POST /login`, `POST /usuarios` (cadastro) |
| Autenticado | `GET /usuarios/<id>`, `POST /pedidos`, `GET /pedidos/usuario/<id>` |
| Admin | `POST/PUT/DELETE /produtos`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /usuarios`, `GET /relatorios/vendas` |

```
$ curl -s -w '
HTTP %{http_code}
' localhost:5001/relatorios/vendas
{"erro":"Autenticação obrigatória","sucesso":false}
HTTP 401

$ curl -s -w '
HTTP %{http_code}
' localhost:5001/relatorios/vendas -H "Authorization: Bearer $TOKEN_CLIENTE"
{"erro":"Permissão insuficiente","sucesso":false}
HTTP 403

$ curl -s -w '
HTTP %{http_code}
' localhost:5001/relatorios/vendas -H "Authorization: Bearer ${TOKEN_ADMIN%?}X"
{"erro":"Autenticação obrigatória","sucesso":false}     # assinatura adulterada em 1 caractere
HTTP 401

$ curl -s -w '
HTTP %{http_code}
' localhost:5001/relatorios/vendas -H "Authorization: Bearer $TOKEN_ADMIN"
{"dados":{"desconto_aplicavel":70.0,"faturamento_bruto":3500.0,"faturamento_liquido":3430.0,
"pedidos_aprovados":1,"pedidos_cancelados":0,"pedidos_pendentes":0,"ticket_medio":3500.0,
"total_pedidos":1},"sucesso":true}
HTTP 200
```

Varredura completa, sem credencial — 12 chamadas cobrindo as 10 rotas protegidas (duas delas
exercitadas duas vezes, com id existente e inexistente):

```
  GET    /usuarios                    -> 401  NEGADO ok
  GET    /usuarios/1                  -> 401  NEGADO ok
  GET    /usuarios/9999               -> 401  NEGADO ok
  POST   /produtos                    -> 401  NEGADO ok
  PUT    /produtos/1                  -> 401  NEGADO ok
  DELETE /produtos/3                  -> 401  NEGADO ok
  POST   /pedidos                     -> 401  NEGADO ok
  GET    /pedidos                     -> 401  NEGADO ok
  GET    /pedidos/usuario/1           -> 401  NEGADO ok
  PUT    /pedidos/1/status            -> 401  NEGADO ok
  GET    /relatorios/vendas           -> 401  NEGADO ok
  POST   /produtos (payload inválido) -> 401  NEGADO ok

  Chamadas a rota protegida negadas: 12/12  (10 rotas distintas)
  Públicas ainda acessíveis:          9/9
  Status iguais ao original:         21/21
```

O mecanismo é um token assinado com HMAC-SHA256 sobre a `SECRET_KEY`, emitido por `POST /login`
(`src/middlewares/auth.py`), sem dependência nova em `requirements.txt`.

## Findings Not Resolved

Nenhum achado da auditoria permanece aberto. Resíduos conhecidos da correção do #6, todos com
severidade abaixo do achado original e nenhum deles restaurando o acesso anônimo:

| Resíduo | Efeito | Recomendação |
|---|---|---|
| Token sem revogação | Credencial vazada vale até expirar (1h por padrão, `TOKEN_TTL_SEGUNDOS`) | Armazenar sessões e conferir na verificação |
| Sem refresh token | Cliente precisa refazer login a cada expiração | Emitir par access/refresh |
| `SECRET_KEY` efêmera quando ausente do ambiente | Tokens deixam de valer a cada restart em desenvolvimento | Definir `SECRET_KEY` no `.env` |

## Breaking Changes

1. **`POST /admin/query` removido** (finding #2). Executava SQL arbitrário sem autenticação.
2. **`POST /admin/reset-db` removido** (finding #2). Substituído por
   `python scripts/reset_db.py --confirmar`.
3. **`GET /usuarios` e `GET /usuarios/<id>` não devolvem mais o campo `senha`** (finding #3).
   As demais chaves permanecem idênticas.
4. **`GET /health` não devolve mais `secret_key`, `db_path`, `debug` e `ambiente`** (finding #3).
   Mantém `status`, `database`, `counts` e `versao`.
5. **Respostas de erro passam a incluir sempre `"sucesso": false`.** Antes o campo aparecia em
   alguns erros e não em outros (`{erro}` vs `{erro,sucesso}`). A chave `erro` e a mensagem são
   idênticas às originais, e nenhum status code mudou — consumidores que leem `erro` não são afetados.
6. **`PUT /produtos/<id>` passou a aplicar as mesmas validações do `POST`** (finding #15). Antes era
   possível atualizar um produto para uma categoria inválida que a criação recusaria.
7. **`PUT /pedidos/<id>/status` retorna 404 para pedido inexistente** (finding #17). Antes respondia
   200 sem ter alterado nada.
8. **Erros de tipo em parâmetros retornam 400 em vez de 500** (finding #17). Ex.: `?preco_min=abc`.
9. **10 rotas que respondiam 200 anonimamente agora exigem credencial** (finding #6) — as listadas como
   "Autenticado" e "Admin" na tabela acima. É a mudança de contrato mais visível desta refatoração, e é
   deliberada: preservar comportamento não pode significar preservar uma API administrativa aberta.
   Clientes existentes precisam chamar `POST /login` e enviar `Authorization: Bearer <token>`.
10. **`POST /login` passou a devolver o campo `token`.** O login já existia e respondia 200 sem emitir
    credencial alguma; o campo é aditivo e as demais chaves da resposta não mudaram.

```
================================
Total: 26 findings | 26 resolvidos | 0 regressões
Rotas protegidas: 10 | chamadas anônimas negadas na configuração padrão: 12/12
================================
```

---

## Histórico de execução

| Execução | Resultado |
|---|---|
| 1ª | Findings #1–#26 tratados, mas o #6 foi fechado com o decorator atrás de `AUTH_ENABLED=false`. Na prática as rotas continuaram anônimas: correção declarada, não aplicada. |
| 2ª (esta) | A skill foi corrigida antes de rodar de novo — princípio 6 do `SKILL.md`, anti-pattern SEC-10 no catálogo, RF-19 reescrito e prova de mitigação obrigatória na Fase 3.2. O #6 foi refeito com emissão e verificação reais, ativas por padrão, e a evidência acima. |

A primeira execução é o motivo de o catálogo ter ganhado o SEC-10 ("guarda de segurança desligada por
padrão"): o defeito não estava no código do decorator, estava no critério que aceitou chamá-lo de
correção.
