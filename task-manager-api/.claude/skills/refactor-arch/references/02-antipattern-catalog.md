# Referência 2 — Catálogo de Anti-Patterns (Fase 2)

38 anti-patterns organizados em cinco famílias, cada um com **sinais de detecção acionáveis**
(padrões de busca reais, não descrições vagas), severidade e o padrão de correção correspondente no
playbook (`references/05-refactoring-playbook.md`).

## Escala de severidade

| Severidade | Critério |
|---|---|
| **CRITICAL** | Falha grave de arquitetura ou segurança: expõe dado sensível, permite execução arbitrária, corrompe dados, ou concentra banco + negócio + roteamento no mesmo arquivo |
| **HIGH** | Violação forte de MVC/SOLID que inviabiliza teste e manutenção: negócio no controller, acoplamento sem DI, estado global mutável |
| **MEDIUM** | Padronização, duplicação e performance moderada: N+1, validação ausente, middleware inadequado |
| **LOW** | Legibilidade, nomenclatura, magic numbers, código morto |

**Ajuste por contexto** (aplique com parcimônia, e justifique no relatório):

- Sobe um nível quando o anti-pattern está no caminho crítico de dinheiro, credenciais ou dados pessoais.
- Sobe um nível quando é sistêmico (mesmo defeito em todos os arquivos) em vez de pontual.
- Desce um nível quando está em código comprovadamente morto ou em script de desenvolvimento (`seed.py`),
  **exceto** segredos versionados, que permanecem CRITICAL onde estiverem.

## Índice

| Família | IDs | Tema |
|---|---|---|
| [SEC](#família-sec--segurança) | SEC-01…09 | Segurança e exposição de dados |
| [ARCH](#família-arch--arquitetura) | ARCH-01…12 | Separação de responsabilidades, MVC, SOLID |
| [PERF](#família-perf--performance-e-integridade-de-dados) | PERF-01…05 | Performance e integridade de dados |
| [QUAL](#família-qual--qualidade-de-código) | QUAL-01…09 | Qualidade e legibilidade |
| [DEP](#família-dep--apis-deprecated) | DEP-01…03 | APIs deprecated e dependências obsoletas |

---

## Família SEC — Segurança

### SEC-01 · Hardcoded Secrets — **CRITICAL**

Segredos literais no código-fonte versionado.

**Sinais:**
- `grep -rniE "(secret|password|passwd|pwd|token|api[_-]?key|access[_-]?key|private[_-]?key)\s*[:=]\s*['\"][^'\"]{6,}"`
- Prefixos de chave real: `pk_live_`, `sk_live_`, `AKIA`, `ghp_`, `xoxb-`, `-----BEGIN * PRIVATE KEY-----`
- `SECRET_KEY = "..."`, `app.config['SECRET_KEY'] = '...'`, `const config = { dbPass: "..." }`
- Strings de conexão completas: `postgres://user:senha@host/db`

**Falso positivo:** valores em `.env.example`, fixtures de teste e placeholders óbvios (`changeme`,
`xxx`). Valores em arquivos de seed **não** são falso positivo se forem credenciais de usuário reais.

**Impacto:** o segredo permanece no histórico do Git mesmo após remoção; rotação obrigatória.
**Correção:** RF-01.

### SEC-02 · SQL Injection por concatenação — **CRITICAL**

Query montada com dado de entrada via concatenação ou interpolação.

**Sinais:**
- `grep -nE "(execute|query|raw|run|get|all)\s*\(\s*[\"'].*(SELECT|INSERT|UPDATE|DELETE)" ` seguido de `+`, `%`, `.format(`, f-string ou template literal
- Python: `"SELECT ... WHERE id = " + str(id)`, `f"... WHERE nome = '{nome}'"`, `"..." % valor`
- JS/TS: `` `SELECT * FROM t WHERE id = ${id}` ``, `"SELECT..." + req.params.id`
- Construção incremental: `query += " AND campo = '" + valor + "'"`

**Priorize a inspeção** de queries de autenticação (`WHERE email = ... AND senha = ...`): ali a injeção
vira bypass de login, não apenas leitura indevida.

**Não é injeção:** placeholders (`?`, `%s`, `:nome`, `$1`) com os valores passados como parâmetro;
concatenação apenas de identificadores literais internos.
**Correção:** RF-02.

### SEC-03 · Armazenamento inseguro de credenciais — **CRITICAL**

**Sinais:**
- Texto plano: coluna `senha`/`password` recebendo o valor cru; comparação `senha == input`
- Hash rápido/quebrado: `hashlib.md5`, `hashlib.sha1`, `crypto.createHash('md5'|'sha1')`, `SHA1(`
- Hash sem salt: `sha256(pwd)` direto, sem valor aleatório por usuário
- Criptografia caseira: função própria com `base64`, XOR, `substring`, loops de concatenação
- Encoding tratado como hash: `Buffer.from(x).toString('base64')`, `base64.b64encode`

**Sinal de gravidade extra:** senha mínima curta (`len(password) < 4`) multiplica o risco de qualquer hash fraco.
**Correção:** RF-03.

### SEC-04 · Dado sensível exposto na resposta — **CRITICAL**

**Sinais:**
- Serializador incluindo credencial: `'password': self.password`, `"senha": row["senha"]`,
  `SELECT *` de tabela de usuários devolvido direto ao cliente
- Endpoint de diagnóstico vazando config: `/health`, `/status`, `/debug` retornando `secret_key`,
  `db_path`, `env`, versões internas
- `to_dict()` / `toJSON()` / serializer único usado tanto internamente quanto na resposta HTTP
- Stack trace na resposta: `return jsonify({"erro": str(e)})`, `res.send(err.stack)`

**Correção:** RF-04 (DTO de saída) + RF-09 (error handler que não vaza interno).

### SEC-05 · Endpoint de execução arbitrária — **CRITICAL**

**Sinais:**
- Rota que recebe SQL do corpo e executa: `cursor.execute(request.json["sql"])`, `db.run(req.body.query)`
- `eval(`, `exec(`, `new Function(`, `child_process.exec(` com entrada do usuário
- Rota destrutiva sem autenticação: `/admin/reset`, `DELETE FROM` em handler de rota, `drop`, `truncate`

**Ação na Fase 3:** remover o endpoint. Não existe versão "segura" de um executor de SQL exposto.

### SEC-06 · Autenticação ausente ou simulada — **CRITICAL** (HIGH se a API for interna/documentadamente pública)

**Sinais:**
- Token previsível ou não assinado: `'token': 'fake-jwt-token-' + str(user.id)`, `token = user.id`
- Login que responde sucesso sem emitir credencial de sessão
- Nenhum decorator/middleware de auth em rotas mutáveis: procure por `@login_required`,
  `@jwt_required`, `passport`, `verifyToken`, `authMiddleware` — **a ausência é o sinal**
- Papel modelado e nunca consultado: existe `is_admin()`/campo `role`/`tipo`, mas nenhum `if` o usa
- Rotas `/admin/*` sem verificação

**Correção:** RF-19 (guardas de rota) — e, no mínimo, registrar o gap explicitamente no relatório.

### SEC-07 · Debug ligado / erro verboso em produção — **HIGH**

**Sinais:**
- `DEBUG = True`, `app.run(debug=True)`, `app.config["DEBUG"] = True`
- `NODE_ENV` ausente ou forçado para `development`; `sqlite3.verbose()`
- `printStackTrace`, `traceback.format_exc()` devolvido ao cliente

**Impacto:** o debugger do Werkzeug expõe console interativo na página de erro; stack traces revelam
estrutura interna e caminhos de arquivo.

### SEC-08 · Dado sensível em log — **HIGH**

**Sinais:**
- `print`/`console.log`/`logger` interpolando `card`, `cartao`, `cvv`, `password`, `token`, `secret`,
  `email` do usuário, CPF/SSN
- Log de payload inteiro: `console.log(req.body)`, `print(dados)`

**Nota:** número de cartão em log é violação de PCI-DSS mesmo em ambiente de desenvolvimento.

### SEC-09 · CORS permissivo / middlewares de segurança ausentes — **MEDIUM**

**Sinais:**
- `CORS(app)` sem `origins`, `cors()` sem opções, `Access-Control-Allow-Origin: *`
- Ausência de `helmet`, rate limiting, limite de tamanho de body
- `host="0.0.0.0"` combinado com debug ligado

---

## Família ARCH — Arquitetura

### ARCH-01 · God Class / God Module — **CRITICAL**

Um arquivo ou classe concentrando 4+ responsabilidades da tabela de mapeamento (Referência 1, §6).

**Sinais:**
- Arquivo-fonte > 250 linhas contendo simultaneamente SQL/ORM, regra de negócio e montagem de resposta
- Classe com nome genérico: `*Manager`, `*Helper`, `*Util`, `*Handler`, `App`, `Main`, `Core`
- Um arquivo servindo 3+ domínios distintos (produtos + usuários + pedidos)
- No mesmo arquivo: criação de conexão, DDL (`CREATE TABLE`), seed e registro de rotas

**Correção:** RF-05 (dividir por domínio) + RF-06 + RF-07.

### ARCH-02 · Regra de negócio no controller/rota — **HIGH**

**Sinais:**
- Handler de rota com > 30 linhas ou > 3 níveis de indentação
- Cálculo de domínio dentro do handler: totais, descontos, faixas, decisão de status
- Efeito colateral disparado do handler: envio de e-mail/SMS/push, chamada a gateway de pagamento
- Regra de negócio "simulada" inline: `status = cc.startsWith("4") ? "PAID" : "DENIED"`

**Teste mental:** para executar esta regra em um job noturno, seria preciso simular um HTTP request?
Se sim, a regra está no lugar errado.
**Correção:** RF-06, RF-15.

### ARCH-03 · Acesso a dados no controller/rota — **HIGH**

**Sinais:**
- `cursor.execute`, `db.query`, `db.session`, `Model.query`, `SELECT`/`INSERT` dentro de um handler
- Import de driver de banco (`sqlite3`, `pg`) em arquivo de rota
- Handler que abre/fecha conexão

### ARCH-04 · Apresentação dentro do model — **HIGH**

**Sinais:**
- Camada de dados montando o dicionário de resposta campo a campo
- Formatação de exibição no model: `str(date)`, máscara de moeda, tradução de rótulos
- Model devolvendo `{"erro": "..."}` em vez de entidade ou exceção

**Correção:** RF-04.

### ARCH-05 · Estado global mutável — **HIGH**

**Sinais:**
- Variável de módulo reatribuída: `global db_connection`, `let globalCache = {}`, `let total = 0`
- Conexão singleton compartilhada entre requisições, especialmente com `check_same_thread=False`
- Cache em memória sem limite nem expiração (também é PERF-04)
- Export de valor primitivo mutável (JS): `module.exports = { totalRevenue }` — quem importa recebe um
  snapshot congelado; bug latente

**Correção:** RF-08.

### ARCH-06 · Dependência hardcoded (sem injeção) — **HIGH**

**Sinais:**
- Classe instanciando suas próprias dependências no construtor: `this.db = new sqlite3.Database(...)`
- Import direto de conexão concreta dentro da regra de negócio
- Cliente de serviço externo (SMTP, gateway) construído dentro do consumidor
- **Consequência observável:** impossível testar sem banco/rede reais

**Correção:** RF-08, RF-15.

### ARCH-07 · Ausência de composition root / efeito colateral no import — **HIGH**

**Sinais:**
- `db.create_all()`, `initDb()`, `CREATE TABLE`, seed executados em nível de módulo (fora de função)
- Configuração inline no entry point, sem factory (`create_app`) nem `main()`
- Função de acesso a dados que também cria schema (`get_db()` que roda DDL)
- Importar o módulo da app produz efeito no banco

**Correção:** RF-08.

### ARCH-08 · Ausência de fronteira transacional — **CRITICAL**

**Sinais:**
- Sequência de 2+ escritas relacionadas sem `BEGIN`/`COMMIT`/`rollback`
- Callbacks aninhados de escrita, cada um com seu próprio retorno de erro
- Baixa de estoque, criação de pedido e registro de pagamento em statements independentes
- `commit()` por operação dentro de um loop

**Impacto:** falha no meio do fluxo deixa dado órfão e inconsistência financeira.
**Correção:** RF-10.

### ARCH-09 · Erro como valor de retorno / contrato inconsistente — **MEDIUM**

**Sinais:**
- Função de domínio devolvendo `{"erro": "..."}` ou `None` para sinalizar falha de negócio
- Chamador inspecionando a chave `erro` do resultado para decidir status HTTP
- Respostas ora `res.send("texto")`, ora `res.json({...})` no mesmo serviço
- Envelope de resposta variando entre endpoints (`{"dados": ...}` vs lista pura)

**Correção:** RF-09 (exceções de domínio + envelope único).

### ARCH-10 · Tratamento de erro não centralizado — **MEDIUM**

**Sinais:**
- `try/except` (ou `try/catch`) repetido em todo handler com o mesmo corpo
- Ausência de `@app.errorhandler`, `app.use((err, req, res, next) => ...)`, `@ExceptionHandler`
- Ausência de handler 404/500 global
- Express: handlers `async` sem wrapper — rejeição não capturada derruba o processo

**Correção:** RF-09.

### ARCH-11 · Camada nominal (pasta sem camada) — **HIGH**

O anti-pattern mais fácil de passar despercebido em projetos "organizados".

**Sinais:**
- Existe `routes/`, mas os arquivos de rota contêm validação + negócio + query + serialização
- Existe `services/`, mas nenhum arquivo o importa
- Existe `models/`, mas as queries são escritas nas rotas
- Blueprint/Router agrupando recursos sem relação (CRUD de `categories` dentro de `report_routes`)

**Como confirmar:** para cada pasta de camada, verifique quem a importa e o que os arquivos realmente
fazem. Camada que ninguém consome não é camada.
**Correção:** RF-06, RF-07, RF-14.

### ARCH-12 · Abstração morta / código não utilizado — **MEDIUM**

**Sinais:**
- Método de model nunca chamado enquanto a lógica equivalente é reescrita nas rotas
  (`Task.is_overdue()` existe; as rotas reimplementam o `if`)
- Serviço completo sem nenhum import (`NotificationService`)
- Helper de validação nunca invocado enquanto as rotas validam à mão
- Constantes declaradas e literais repetidos no lugar delas
- Dependência no manifesto e nunca importada (`marshmallow`, `python-dotenv`)

**Por que não é só limpeza:** revela que a camada correta foi projetada e ignorada pelo fluxo real.
**Correção:** RF-14 — adotar a implementação existente ou removê-la, nunca manter as duas.

---

## Família PERF — Performance e integridade de dados

### PERF-01 · Query N+1 — **MEDIUM**

**Sinais:**
- Query dentro de laço: `for ... in ...:` contendo `execute`/`query`/`.get(`/`filter_by`
- Cursores auxiliares numerados (`cursor2`, `cursor3`) — indício quase certo de N+1 aninhado
- ORM sem eager loading: `Model.query.all()` seguido de acesso a relacionamento no laço
- Callbacks de query aninhados por item de uma lista

**Como quantificar no relatório:** "N registros → 2N+1 queries; um JOIN resolve em 1".
**Correção:** RF-11.

### PERF-02 · Resultado sem paginação — **MEDIUM**

**Sinais:**
- `SELECT *` sem `LIMIT`; `Model.query.all()`, `find({})`, `findAll()` em rota de listagem
- Rota de listagem sem parâmetros `page`/`limit`/`offset`/`cursor`
- Relatório que materializa a tabela inteira em memória para agregar

**Correção:** RF-12.

### PERF-03 · Agregação redundante — **MEDIUM**

**Sinais:**
- Vários `COUNT`/`SUM` sequenciais que diferem apenas no `WHERE`
- Contagem feita em Python/JS sobre `all()` quando o banco faria com `GROUP BY`
- Somatório acumulado em laço sobre todos os registros

**Correção:** RF-11.

### PERF-04 · Cache/coleção em memória sem limite — **HIGH**

**Sinais:**
- Dicionário/objeto de módulo que só cresce: `globalCache[key] = value`, `self.notifications.append(...)`
- Nenhuma política de expiração, tamanho máximo ou invalidação
- Estado em memória compartilhado que impede rodar múltiplas instâncias

### PERF-05 · Integridade referencial ausente — **HIGH**

**Sinais:**
- `DELETE` de entidade-pai sem tratar filhos e sem `ON DELETE CASCADE`
- Schema sem `FOREIGN KEY`; SQLite sem `PRAGMA foreign_keys = ON`
- Deleção de filhos em laço na camada de aplicação em vez de cascade/transação
- Relacionamento de ORM sem `cascade`
- Banco `:memory:` em código de produção (dados perdidos a cada restart)

**Correção:** RF-10.

---

## Família QUAL — Qualidade de código

### QUAL-01 · Lógica duplicada — **MEDIUM**

**Sinais:**
- Duas funções com > 80% de corpo idêntico, diferindo só no filtro
- A mesma regra reescrita em 3+ lugares (cálculo de "atrasado", montagem do mesmo DTO)
- Bloco de validação copiado entre criação e atualização — **e já divergido**

**Registre a divergência quando existir**: é a prova concreta do custo da duplicação.
**Correção:** RF-13, RF-14.

### QUAL-02 · Validação ausente, fraca ou duplicada — **MEDIUM**

**Sinais:**
- Handler usando `request.get_json()` / `req.body` sem checar `None`/`undefined`
- Validação só de presença, sem formato/tipo/faixa
- Conversão de tipo sem proteção: `int(x)`, `float(x)`, `parseInt` sem tratamento
- Recurso referenciado sem checar existência antes de atualizar
- Default perigoso para campo ausente: senha padrão, papel de admin
- Regras repetidas entre POST e PUT em vez de um schema compartilhado

**Correção:** RF-13.

### QUAL-03 · Exceção engolida — **MEDIUM** (HIGH se sistêmico)

**Sinais:**
- Python: `except:` nu, `except Exception: pass`, `except: return None`
- JS: `catch (e) {}`, callback que ignora o parâmetro `err`
- Erro capturado e descartado sem log
- Resposta de sucesso mesmo com erro detectado

**Nota Python:** `except:` nu captura `KeyboardInterrupt` e `SystemExit`.
**Correção:** RF-09.

### QUAL-04 · Aninhamento profundo / callback hell — **MEDIUM**

**Sinais:**
- 4+ níveis de callback ou indentação em uma função
- `const self = this` / `var that = this` para contornar rebind de `this`
- Contadores manuais para orquestrar assincronia (`pending--; if (pending === 0) res.json(...)`)
- Condicionais aninhados triplos que retornam booleano

**Risco concreto:** contador manual permite duplo envio de resposta (`ERR_HTTP_HEADERS_SENT`).
**Correção:** RF-16.

### QUAL-05 · Magic numbers e strings — **LOW**

**Sinais:**
- Literais numéricos em regra de negócio: faixas, alíquotas, limites de tamanho
- Listas de valores válidos inline: `if status not in ['pending', 'done', ...]`
- Strings de status/papel repetidas em vários arquivos sem enum/constante

**Correção:** RF-17.

### QUAL-06 · `print`/`console.log` como logging — **LOW**

**Sinais:**
- `print(`, `console.log(` fora de scripts de CLI e seed
- Ausência de `logging`/`winston`/`pino` no projeto
- Sem níveis, timestamp ou destino configurável

**Correção:** RF-18.

### QUAL-07 · Código morto e imports não utilizados — **LOW**

**Sinais:**
- Imports nunca referenciados (`import os, sys, json` em arquivo que não os usa)
- Funções/variáveis exportadas e nunca importadas
- Bloco comentado de código antigo
- Dependência declarada no manifesto e nunca importada

### QUAL-08 · Nomenclatura ruim — **LOW**

**Sinais:**
- Variáveis de uma letra fora de laço curto: `u`, `e`, `p`, `cc`, `cid`
- Sombreamento de builtin: `id`, `list`, `dict`, `type`, `input`
- Sufixos numéricos: `cursor2`, `cursor3`, `data1`
- Nomes genéricos de classe/arquivo: `Manager`, `Helper`, `utils.js` como depósito
- Idioma misturado no mesmo escopo (nomes em inglês, mensagens em português, sem padrão)

### QUAL-09 · Construções não idiomáticas — **LOW**

**Sinais:**
- `if cond: return True else: return False` em vez de `return cond`
- `type(x) == list` em vez de `isinstance(x, list)` / `Array.isArray(x)`
- Concatenação com `+` em vez de f-string/template literal
- `let` sem reatribuição onde caberia `const`
- Dicionário montado campo a campo em vez de literal

---

## Família DEP — APIs deprecated

**Regra obrigatória:** confirme a versão da linguagem/framework no manifesto antes de classificar, e
**sempre** indique o equivalente moderno. Reportar "está deprecated" sem a substituição não é acionável.

### DEP-01 · API deprecated da linguagem/stdlib — **LOW** (MEDIUM se já emite warning na versão em uso)

| Deprecated | Desde | Equivalente moderno |
|---|---|---|
| `datetime.utcnow()`, `datetime.utcfromtimestamp()` | Python 3.12 | `datetime.now(timezone.utc)` |
| `imp` | Python 3.4 (removido em 3.12) | `importlib` |
| `distutils` | Python 3.10 (removido em 3.12) | `setuptools` / `packaging` |
| `asyncio.get_event_loop()` fora de loop | Python 3.10 | `asyncio.run()` / `get_running_loop()` |
| `locale.getdefaultlocale()` | Python 3.11 | `locale.getlocale()` |
| `new Buffer(x)` | Node 6 | `Buffer.from(x)` / `Buffer.alloc(n)` |
| `url.parse()` | Node 11 | `new URL()` |
| `fs.exists()` | Node 1 | `fs.existsSync()` / `fs.promises.access()` |
| `crypto.createCipher()` | Node 10 | `crypto.createCipheriv()` |
| `process.binding()` | Node 10 | módulos públicos equivalentes |
| `substr()` | anexo B do ECMAScript | `slice()` / `substring()` |
| `var` em código novo | ES6 | `const` / `let` |

**Sinal adicional:** `datetime.utcnow()` retorna datetime *naive* rotulado como UTC — a comparação com
datetime ciente de fuso quebra. É correção de correção, não só de estilo.

### DEP-02 · API deprecated de framework/ORM — **MEDIUM**

| Deprecated | Contexto | Equivalente moderno |
|---|---|---|
| `Model.query.get(id)` | SQLAlchemy 2.0 (`LegacyAPIWarning`) | `db.session.get(Model, id)` |
| `Model.query` (estilo geral) | SQLAlchemy 2.0 | `db.session.execute(db.select(Model))` |
| `@app.before_first_request` | removido no Flask 2.3+ | inicialização na factory `create_app()` |
| `flask.Markup`, `flask.escape` | Flask 2.3 | `markupsafe.Markup`, `markupsafe.escape` |
| `body-parser` | Express 4.16+ | `express.json()` / `express.urlencoded()` |
| `res.send(status, body)` | Express 4 | `res.status(code).send(body)` |
| `app.del()` | Express 3 | `app.delete()` |
| `request` (biblioteca HTTP) | descontinuada em 2020 | `fetch` nativo / `axios` / `undici` |
| `moment` | modo de manutenção | `date-fns`, `dayjs`, `Temporal` |
| `sequelize.import()` | Sequelize 5 | `require` direto do model |
| Django `url()` | Django 4.0 | `re_path()` / `path()` |

### DEP-03 · Dependência obsoleta ou superada — **LOW**

**Sinais:**
- Pacote sem manutenção ativa ou sucedido por alternativa oficial:
  `sqlite3` (callback) → `better-sqlite3` ou `node:sqlite`; `request` → `undici`
- Major do framework em fim de vida (Express 4 → 5, que propaga rejeição de handler `async`)
- Versão fixada muito atrás da estável, com CVE conhecido
- Dependência declarada e nunca usada (cruze com QUAL-07)

**Cuidado:** troca de dependência é mudança de risco. Proponha no relatório; execute na Fase 3 apenas se
for necessária para corrigir um achado CRITICAL/HIGH ou se o usuário aprovar explicitamente.

---

## Checklist de varredura da Fase 2

- [ ] Todo arquivo-fonte lido integralmente (não apenas grep)
- [ ] Cada finding com `arquivo:linha` verificado
- [ ] Ocorrências do mesmo anti-pattern agrupadas em um finding
- [ ] Severidades atribuídas pela tabela, com ajuste de contexto justificado
- [ ] Família `DEP-*` verificada explicitamente contra a versão real da stack
- [ ] `ARCH-11` e `ARCH-12` verificados em projetos que já possuem pastas de camada
- [ ] Findings ordenados CRITICAL → HIGH → MEDIUM → LOW
- [ ] Mínimo de 5 findings e pelo menos 1 CRITICAL/HIGH
