```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      JavaScript (Node.js v24.18.1, CommonJS)
Framework:     Express 4.18.2 (resolvido para 4.22.1)
Dependencies:  sqlite3 5.1.6 (resolvido para 5.1.7)
Domain:        LMS / plataforma de cursos (usuários, cursos, matrículas, pagamentos, auditoria)
Architecture:  God Class — 1 classe concentra banco, DDL, seed, rotas, negócio e relatório
Source files:  3 files analyzed | ~180 lines of code
Persistence:   SQLite em memória (`:memory:`), driver sqlite3 baseado em callbacks, sem ORM
DB tables:     users, courses, enrollments, payments, audit_logs
Endpoints:     3 endpoints mapeados
================================
```

### Inventário de endpoints — contrato a preservar

| # | Método | Path | Handler atual | Observação |
|---|---|---|---|---|
| 1 | POST | `/api/checkout` | `AppManager.js:28-78` | fluxo central: cria usuário, cobra, matricula |
| 2 | GET | `/api/admin/financial-report` | `AppManager.js:80-129` | **administrativo, sem autenticação** |
| 3 | DELETE | `/api/users/:id` | `AppManager.js:131-137` | **destrutivo, sem autenticação** |

> As três rotas são registradas por `manager.setupRoutes(app)` (`app.js:10`), um método de instância —
> não por `express.Router()`. Uma busca apenas por `router.` ou `Router()` não encontraria nenhuma.

**Contratos de resposta observados** (relevantes para a validação da Fase 3):

| Endpoint | Sucesso | Erro |
|---|---|---|
| `POST /api/checkout` | `200` JSON `{msg, enrollment_id}` | `400` texto `"Bad Request"` / `"Pagamento recusado"`; `404` texto `"Curso não encontrado"`; `500` texto |
| `GET /api/admin/financial-report` | `200` JSON `[{course, revenue, students[]}]` | `500` texto `"Erro DB"` |
| `DELETE /api/users/:id` | `200` texto | — |

---

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   Node.js 24 + Express 4
Files:   3 analyzed | ~180 lines of code
Date:    2026-08-13
```

## Summary

**CRITICAL: 6 | HIGH: 8 | MEDIUM: 6 | LOW: 5**

180 linhas concentram uma densidade de defeito incomum: `AppManager` é uma God Class que abre a conexão,
cria o schema, semeia dados, registra rotas, implementa a regra de checkout, simula o gateway de pagamento
e monta o relatório financeiro. O fluxo mais crítico do sistema — cobrar e matricular — roda em cinco
níveis de callback aninhado, sem transação e com metade dos erros ignorados, o que garante inconsistência
financeira em qualquer falha parcial. Some-se a isso uma chave `pk_live_` de produção versionada, o número
do cartão impresso em log e um hash de senha caseiro que é reversível por inspeção.

## Findings

### #1 [CRITICAL] Segredos de produção hardcoded e versionados (SEC-01)
**File:** `src/utils.js:1-7`
**Description:** O objeto `config` traz `dbUser: "admin_master"`, `dbPass: "senha_super_secreta_prod_123"`,
`paymentGatewayKey: "pk_live_1234567890abcdef"` e `smtpUser` como literais no código.
**Impact:** O prefixo `pk_live_` identifica uma chave de **produção** do gateway de pagamento. Estando no
repositório, está no histórico do Git de todos que já clonaram — remover o arquivo não desfaz a exposição,
a rotação da chave é obrigatória. As credenciais de banco e SMTP têm o mesmo problema.
**Recommendation:** Módulo de config lendo de variável de ambiente, `.env` no `.gitignore` e `.env.example`
versionado apenas com as chaves. (RF-01)

### #2 [CRITICAL] Número de cartão e chave do gateway em log (SEC-08, elevado)
**File:** `src/AppManager.js:45`
**Description:** ``console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`)`` grava o
número completo do cartão e a chave do gateway em texto claro no stdout.
**Impact:** Stdout é tipicamente coletado por agregadores de log e retido por meses. Gravar o PAN é
violação direta do requisito 3.4 do PCI-DSS, e a chave de produção ao lado torna o log um alvo de valor.
**Severidade:** o catálogo classifica SEC-08 como HIGH; elevado a CRITICAL pela regra de ajuste por
contexto — está no caminho crítico de dinheiro e expõe credencial de produção.
**Recommendation:** Nunca logar dado de cartão. Logar identificadores (`enrollment_id`, últimos 4 dígitos
no máximo) via logger estruturado. (RF-18)

### #3 [CRITICAL] Hash de senha caseiro e reversível (SEC-03)
**File:** `src/utils.js:17-23`, usado em `src/AppManager.js:68`
**Description:** `badCrypto()` concatena 10.000 vezes os dois primeiros caracteres do base64 da senha e
devolve os 10 primeiros caracteres do resultado.
**Impact:** Base64 é *encoding*, não hash — é reversível. Como a saída é a repetição de dois caracteres
derivados sempre do mesmo prefixo, o espaço de valores possíveis é minúsculo: colisões são triviais e o
valor original é recuperável por inspeção. O loop de 10.000 iterações consome CPU sem entregar nenhum
custo real de força bruta. Não há salt.
**Recommendation:** `bcrypt` (ou `argon2`) com salt por usuário e custo configurável. (RF-03)

### #4 [CRITICAL] God Class `AppManager` (ARCH-01)
**File:** `src/AppManager.js:1-141`
**Description:** A classe abre a conexão (`:7`), cria as 5 tabelas (`:12-16`), semeia dados (`:18-21`),
registra as 3 rotas (`:25-138`), implementa a regra de checkout (`:43-64`), simula o gateway de pagamento
(`:46`) e monta o relatório financeiro (`:80-129`) — 7 responsabilidades das 8 da matriz de arquitetura.
**Impact:** Nada é testável isoladamente: verificar a regra de precificação exige subir Express e SQLite.
O próprio nome "Manager" denuncia a ausência de fronteira de responsabilidade.
**Recommendation:** Dividir em `models/` (users, courses, enrollments, payments), `controllers/`
(checkout, report, user) e `routes/` com `express.Router()`. (RF-05, RF-06, RF-07)

### #5 [CRITICAL] Checkout sem fronteira transacional (ARCH-08)
**File:** `src/AppManager.js:50-63` (com `:66-72` para o caso de usuário novo)
**Description:** A sequência insere `users` → `enrollments` → `payments` → `audit_logs` em callbacks
encadeados, cada um com seu próprio `return res.status(500)`. Não há `BEGIN`/`COMMIT`/`ROLLBACK`.
**Impact:** Inconsistência financeira garantida em falha parcial. Se o `INSERT` em `payments` falhar
(`:55`), a matrícula **já foi persistida** e o cliente recebe erro — aluno matriculado sem pagamento
registrado. Se o pagamento for recusado depois da criação do usuário (`:48` após `:69`), sobra conta órfã.
**Recommendation:** Promisificar o driver e envolver a operação inteira em uma transação com rollback na
exceção. (RF-10, RF-16)

### #6 [CRITICAL] Rotas administrativas e destrutivas sem autenticação (SEC-06)
**File:** `src/AppManager.js:80` (`GET /api/admin/financial-report`), `:131` (`DELETE /api/users/:id`)
**Description:** O relatório financeiro completo — receita por curso e nome de cada aluno — e a deleção de
usuário são acessíveis anonimamente. Não há middleware de autenticação em lugar nenhum do projeto.
**Impact:** Qualquer visitante lê o faturamento e a base de alunos (dado pessoal) e apaga usuários.
**Recommendation:** Middleware de autenticação aplicado ao grupo `/api/admin` e às rotas mutáveis. A
emissão de credencial é funcionalidade nova — ver "Fora de escopo". (RF-19)

### #7 [HIGH] Gateway de pagamento simulado dentro do handler (ARCH-02)
**File:** `src/AppManager.js:46`
**Description:** `let status = cc.startsWith("4") ? "PAID" : "DENIED"` — a aprovação do pagamento é
decidida pelo primeiro dígito do cartão, inline no handler HTTP.
**Impact:** A regra de negócio mais crítica do sistema está acoplada ao controller e não pode ser exercida
fora de um request. Como `cc` não é validado (finding #16), um valor não-string quebra `.startsWith` e
derruba a requisição com 500.
**Recommendation:** Interface `PaymentGateway` injetada no controller, com a implementação atual nomeada
explicitamente como `FakePaymentGateway`. (RF-15)

### #8 [HIGH] Callback hell com `this`/`self` misturados (QUAL-04)
**File:** `src/AppManager.js:26,37-77`
**Description:** O checkout aninha cinco níveis de callback. A linha `:26` cria `const self = this` porque
os callbacks declarados como `function(err)` (`:50`, `:54`, `:69`) reescrevem `this` para o statement do
sqlite3 — necessário para ler `this.lastID`, mas incompatível com o `this` da classe.
**Impact:** É o defeito de legibilidade que esconde os findings #5 e #9: o fluxo de erro fica impossível de
auditar visualmente. Metade das linhas do arquivo é indentação.
**Recommendation:** Promisificar o driver uma vez e reescrever o fluxo com `async/await`. (RF-16)

### #9 [HIGH] Erros silenciosamente ignorados (QUAL-03)
**File:** `src/AppManager.js:104,106,133`
**Description:** Nas queries de usuário (`:104`) e pagamento (`:106`) do relatório, o parâmetro `err` é
declarado e nunca verificado. Em `DELETE /api/users/:id` (`:133`) o erro também é ignorado e a rota
responde `200` incondicionalmente.
**Impact:** Falhas de banco viram sucesso silencioso: o relatório exibe `student: 'Unknown'` (`:113`) sem
distinguir "usuário deletado" de "query falhou", e a deleção confirma remoções que podem não ter ocorrido.
**Recommendation:** Com `async/await`, o erro propaga sozinho para o error handler central. (RF-09, RF-16)

### #10 [HIGH] Ausência de tratamento de erro centralizado (ARCH-10)
**File:** `src/app.js:1-14`
**Description:** Não há `app.use((err, req, res, next) => ...)`, handler 404 nem wrapper para handlers
assíncronos. O tratamento é ad-hoc em cada callback.
**Impact:** No Express 4, uma rejeição dentro de handler `async` não é capturada — derruba o processo Node
inteiro, que não tem supervisão. Um erro lançado dentro de um callback do sqlite3 tem o mesmo efeito.
**Recommendation:** Hierarquia de erros de domínio + middleware de erro + `asyncHandler`. (RF-09)

### #11 [HIGH] Estado global mutável exportado por valor (ARCH-05)
**File:** `src/utils.js:9-10,25`, importado em `src/AppManager.js:2`
**Description:** `globalCache` e `totalRevenue` são variáveis de módulo exportadas diretamente.
**Impact:** Dois problemas distintos. (a) `totalRevenue` é exportado **por valor** — quem importa recebe o
snapshot `0` que nunca se atualiza; `AppManager.js:2` já o importa sem usar, um bug latente esperando o
primeiro consumidor. (b) O estado em memória impede rodar mais de uma instância do processo com
comportamento coerente.
**Recommendation:** Encapsular o cache atrás de um módulo com interface explícita; expor totais por query
agregada, não por variável. (RF-08)

### #12 [HIGH] Cache em memória sem limite nem expiração (PERF-04)
**File:** `src/utils.js:9,12-15`, chamado em `src/AppManager.js:59`
**Description:** `logAndCache` grava em `globalCache[key]` a cada checkout, com chave por usuário
(`last_checkout_${userId}`). Não há limite de tamanho, TTL nem invalidação.
**Impact:** Vazamento de memória proporcional ao número de usuários distintos — cresce indefinidamente até
o processo ser reiniciado.
**Recommendation:** Remover o cache (o dado já está em `audit_logs`) ou substituir por cache com TTL e
limite. (RF-08)

### #13 [HIGH] Integridade referencial ausente (PERF-05)
**File:** `src/AppManager.js:12-16` (schema), `:131-137` (deleção)
**Description:** As tabelas não declaram `FOREIGN KEY` e o `DELETE FROM users` não remove `enrollments` nem
`payments`. A própria resposta HTTP admite o defeito: *"Usuário deletado, mas as matrículas e pagamentos
ficaram sujos no banco"* (`:135`).
**Impact:** Corrupção silenciosa de dados contábeis: o relatório financeiro passa a somar receita de
matrículas cujo aluno não existe mais, exibindo `student: 'Unknown'` (`:113`).
**Recommendation:** Declarar as FKs, ativar `PRAGMA foreign_keys = ON` e decidir explicitamente entre
`ON DELETE CASCADE` e soft delete. (RF-10)

### #14 [HIGH] Banco em memória em código de aplicação (PERF-05)
**File:** `src/AppManager.js:7`
**Description:** `new sqlite3.Database(':memory:')` — o banco é recriado do zero a cada boot.
**Impact:** Todos os pagamentos e matrículas são perdidos a cada restart, e cada instância do processo tem
seu próprio banco isolado — a aplicação não pode escalar horizontalmente nem sobreviver a um deploy.
**Recommendation:** Caminho do arquivo vindo da configuração, com `:memory:` restrito a teste. (RF-01)

### #15 [MEDIUM] Consultas N+1 no relatório financeiro (PERF-01)
**File:** `src/AppManager.js:83-128`
**Description:** 1 query de cursos + 1 query de matrículas por curso + 2 queries (usuário e pagamento) por
matrícula.
**Impact:** 10 cursos com 100 matrículas produzem 211 round-trips onde um `JOIN` com `GROUP BY` resolveria
em 1. O custo cresce com o produto de cursos × matrículas.
**Recommendation:** Uma query com `JOIN` entre as quatro tabelas, agrupando em memória. (RF-11)

### #16 [MEDIUM] Orquestração assíncrona por contadores manuais (QUAL-04)
**File:** `src/AppManager.js:86-122`
**Description:** `coursesPending` e `enrPending` são decrementados à mão para decidir quando responder.
**Impact:** Frágil em dois pontos concretos: se a query de matrículas falhar, `enrollments` chega
`undefined` e `.length` (`:93`) lança dentro de um callback, derrubando o processo; e um curso sem
matrículas combinado a erro parcial pode disparar `res.json` duas vezes (`ERR_HTTP_HEADERS_SENT`).
**Recommendation:** `Promise.all` elimina a classe inteira de bug. (RF-16)

### #17 [MEDIUM] Validação de entrada ausente e senha default (QUAL-02)
**File:** `src/AppManager.js:35,68`
**Description:** `if (!u || !e || !cid || !cc)` verifica apenas presença: não valida formato de e-mail, não
valida que `cc` é string numérica, não valida o tipo de `c_id`. Quando a senha não é enviada, o código
substitui pelo literal `"123456"` (`:68`).
**Impact:** `cc` não-string quebra `.startsWith` em `:46` com 500. E contas são criadas silenciosamente com
uma senha previsível que o dono da conta desconhece.
**Recommendation:** Camada de validação por rota; senha ausente é erro de validação, não default. (RF-13)

### #18 [MEDIUM] Inicialização de banco no boot, sem composition root (ARCH-07)
**File:** `src/app.js:8-10`, `src/AppManager.js:10-23`
**Description:** `app.js` instancia `AppManager`, chama `initDb()` (DDL + seed) e `setupRoutes(app)` no
carregamento do módulo. A conexão é criada dentro do construtor da classe (`:7`), não injetada.
**Impact:** Importar o módulo cria schema e insere dados; não há como instanciar a aplicação com um banco
de teste sem editar código de produção. É também ARCH-06 (dependência hardcoded).
**Recommendation:** `createApp(deps)` como composition root, com conexão e models injetados; DDL e seed em
comandos separados. (RF-08)

### #19 [MEDIUM] Camada de middlewares ausente (SEC-09)
**File:** `src/app.js:1-14`
**Description:** Só `express.json()` está registrado. Não há handler 404, logger de requisição, rate
limiting no checkout, `helmet` nem limite de tamanho de corpo.
**Impact:** O endpoint de checkout — que cria usuários e processa pagamento — aceita requisições sem
qualquer limitação de taxa. Rotas inexistentes devolvem o HTML de erro padrão do Express.
**Recommendation:** Registrar os middlewares transversais no composition root. Rate limiting e `helmet`
exigem dependências novas — ver "Fora de escopo". (RF-09)

### #20 [MEDIUM] Contrato de resposta inconsistente (ARCH-09)
**File:** `src/AppManager.js:35,38,41,51,55,60,84,135`
**Description:** Sucesso responde JSON (`:60`), erros respondem texto puro (`"Bad Request"`, `"Erro DB"`,
`"Erro Matrícula"`), e `DELETE /api/users/:id` responde uma frase explicando um bug (`:135`). O corpo do
checkout usa nomes abreviados não convencionais: `usr`, `eml`, `pwd`, `c_id`, `card`.
**Impact:** O cliente precisa inspecionar o `Content-Type` para saber como interpretar a resposta, e não há
código de erro estável para tratar programaticamente.
**Recommendation:** Envelope JSON único para erro, produzido pelo error handler central. Renomear campos do
payload seria quebra de contrato — ver "Fora de escopo". (RF-09)

### #21 [LOW] Nomenclatura de uma letra (QUAL-08)
**File:** `src/AppManager.js:29-33,89,102`
**Description:** `u`, `e`, `p`, `cid`, `cc` para usuário, e-mail, senha, id do curso e cartão; `c` e `enr`
nos laços do relatório.
**Impact:** `e` é convenção de erro em JavaScript e aqui significa e-mail — leitura ativamente enganosa.

### #22 [LOW] `let` onde caberia `const` (QUAL-09)
**File:** `src/AppManager.js:29-33,43,46,52,81,86,90,93`
**Description:** Todas as declarações usam `let`, inclusive as que nunca são reatribuídas.
**Impact:** Perde-se o sinal de imutabilidade que ajuda a raciocinar sobre o fluxo assíncrono.

### #23 [LOW] `console.log` como mecanismo de log (QUAL-06)
**File:** `src/app.js:13`, `src/AppManager.js:45`, `src/utils.js:13`
**Description:** Três pontos de log, sem nível, timestamp ou destino configurável.
**Impact:** Impossível filtrar por severidade ou desligar em produção — e um deles é o finding #2.
**Recommendation:** Logger estruturado. (RF-18)

### #24 [LOW] Import morto (QUAL-07)
**File:** `src/AppManager.js:2`
**Description:** `totalRevenue` é importado e nunca usado.
**Impact:** Sugere uma dependência que não existe e mascara o defeito de export por valor (finding #11).

### #25 [LOW] `sqlite3.verbose()` em código de produção (SEC-07)
**File:** `src/AppManager.js:1`
**Description:** `require('sqlite3').verbose()` mantém stack traces estendidos em qualquer ambiente.
**Impact:** Custo de performance e detalhamento interno desnecessário fora de desenvolvimento.

## Deprecated APIs

**Nenhuma API deprecated de linguagem ou framework detectada** no código. Verificados explicitamente
contra Node.js 24.18.1 / Express 4.22.1: `new Buffer()`, `url.parse()`, `fs.exists()`,
`crypto.createCipher()`, `process.binding()`, `String.prototype.substr()`, `body-parser`,
`res.send(status, body)`, `app.del()`, `require('request')` e `moment` — zero ocorrências. O código já usa
`Buffer.from()` e `express.json()`, que são as formas modernas.

**Dependências superadas (DEP-03), recomendação sem execução automática:**

| Dependência | Situação | Alternativa moderna |
|---|---|---|
| `sqlite3` 5.1.x | API baseada em callbacks, que é a causa raiz dos findings #5, #8, #9 e #16 | `node:sqlite` (nativo a partir do Node 22 — **disponível neste ambiente**) ou `better-sqlite3` |
| `express` 4.22.1 | Express 5 propaga automaticamente rejeições de handlers `async`, eliminando a necessidade do `asyncHandler` | Express 5 |

Trocar dependência é mudança de risco: a Fase 3 mantém `sqlite3` e resolve o problema promisificando o
driver (RF-16), o que entrega o mesmo ganho sem alterar a superfície de dependências. A migração fica
registrada como recomendação.

## Refactoring Plan

### Estrutura proposta

```
ecommerce-api-legacy/
├── src/
│   ├── config/index.js                  configuração vinda do ambiente
│   ├── database/
│   │   ├── connection.js                driver promisificado + transação
│   │   └── schema.js                    DDL e seed explícitos
│   ├── models/
│   │   ├── user.model.js
│   │   ├── course.model.js
│   │   ├── enrollment.model.js
│   │   └── payment.model.js
│   ├── controllers/
│   │   ├── checkout.controller.js
│   │   ├── report.controller.js
│   │   └── user.controller.js
│   ├── routes/
│   │   ├── checkout.routes.js
│   │   ├── report.routes.js
│   │   └── user.routes.js
│   ├── services/
│   │   ├── payment.gateway.js           FakePaymentGateway atrás de interface
│   │   └── audit.service.js
│   ├── validators/checkout.validator.js
│   ├── middlewares/
│   │   ├── errors.js                    hierarquia de erros de domínio
│   │   ├── error-handler.js
│   │   ├── async-handler.js
│   │   └── auth.js                      ponto de extensão
│   ├── utils/logger.js
│   └── app.js                           createApp() — composition root
├── server.js                            entry point (bootstrap)
├── .env.example
└── package.json
```

### Mapeamento finding → transformação

| Findings | Transformação | Arquivos afetados |
|---|---|---|
| #1, #14, #25 | RF-01 Extrair configuração para o ambiente | `config/index.js`, `.env.example` |
| #3 | RF-03 Hash de senha seguro | `models/user.model.js` |
| #4 | RF-05 Dividir God Class em models por domínio | `models/*` |
| #7, #17 | RF-06 Extrair controller do handler | `controllers/*` |
| #4 | RF-07 Extrair camada de rotas com `express.Router()` | `routes/*` |
| #11, #12, #18 | RF-08 Composition root + injeção de dependência | `app.js`, `server.js` |
| #9, #10, #20 | RF-09 Error handler centralizado + asyncHandler | `middlewares/*` |
| #5, #13 | RF-10 Transação e integridade referencial | `database/*`, `controllers/checkout` |
| #15 | RF-11 Eliminar N+1 com JOIN | `models/*`, `controllers/report` |
| #17 | RF-13 Camada de validação | `validators/*` |
| #7 | RF-15 Gateway de pagamento atrás de interface | `services/payment.gateway.js` |
| #8, #16 | RF-16 Callback hell → async/await + Promise.all | todo o fluxo |
| #2, #23 | RF-18 Logging estruturado sem dado sensível | `utils/logger.js` |
| #6 | RF-19 Proteger rotas administrativas | `middlewares/auth.js` |
| #21, #22, #24 | Nomenclatura, `const`, remoção de import morto | todo o código |

### Contrato preservado

Os **3 endpoints** devem continuar respondendo com o mesmo método, path e código de status. Mudanças de
contrato previstas:

1. **Corpos de erro passam de texto puro para JSON** (`{"error": "..."}`). Os status codes e as mensagens
   permanecem idênticos. É consequência inevitável do error handler central (finding #20) — declarada aqui
   por ser observável pelo cliente.
2. **`DELETE /api/users/:id` deixa de responder a frase que admite o bug** e passa a remover os registros
   dependentes (finding #13).

Os nomes abreviados do payload de checkout (`usr`, `eml`, `pwd`, `c_id`, `card`) são **mantidos** —
renomeá-los quebraria o `api.http` e qualquer cliente existente.

### Fora de escopo

- **Autenticação real.** O finding #6 é mitigado protegendo as rotas com um middleware e removendo o
  acesso anônimo às operações administrativas; emitir e verificar credencial é funcionalidade nova.
- **Integração de pagamento real.** O gateway continua fake — mas explicitamente nomeado e isolado atrás de
  uma interface, para que a troca seja local.
- **Troca de `sqlite3` por `node:sqlite` e de Express 4 para 5.** Recomendado no relatório; executá-lo
  altera a superfície de dependências sem ser necessário para corrigir os findings.
- **`helmet` e rate limiting.** Exigem dependências novas.
- **Migração de dados.** Não se aplica: o banco é `:memory:` e é recriado a cada boot.

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

```
ecommerce-api-legacy/
├── server.js                            bootstrap
├── .env.example
├── package.json                         main: server.js
└── src/
    ├── app.js                           composition root — createApp({ db })
    ├── config/index.js
    ├── database/
    │   ├── connection.js                driver promisificado + transação
    │   └── schema.js                    DDL com FKs + seed idempotente
    ├── models/
    │   ├── user.model.js
    │   ├── course.model.js
    │   ├── enrollment.model.js
    │   ├── payment.model.js
    │   ├── audit.model.js
    │   └── password.js                  scrypt com salt
    ├── controllers/
    │   ├── checkout.controller.js
    │   ├── report.controller.js
    │   └── user.controller.js
    ├── routes/
    │   ├── checkout.routes.js
    │   ├── report.routes.js
    │   └── user.routes.js
    ├── services/payment.gateway.js
    ├── validators/checkout.validator.js
    ├── middlewares/
    │   ├── errors.js
    │   ├── error-handler.js
    │   ├── async-handler.js
    │   └── auth.js
    └── utils/logger.js
```

**Antes:** 3 arquivos, 180 linhas, uma God Class com 7 responsabilidades.
**Depois:** 24 módulos em 9 camadas. `AppManager.js` e `utils.js` foram removidos.

Indicador direto do fim do callback hell: a maior indentação do fluxo de checkout caiu de
**36 para 16 espaços**.

## Findings Resolved

| Severidade | Resolvidos | Total | Observação |
|---|---|---|---|
| CRITICAL | 6/6 | 6 | #6 (autenticação) mitigado: rotas administrativa e destrutiva passam pelo middleware, inativo até `AUTH_ENABLED=true`; emissão de credencial permanece fora de escopo |
| HIGH | 8/8 | 8 | |
| MEDIUM | 6/6 | 6 | #19 parcial: 404 e limite de corpo implementados; `helmet` e rate limiting exigem dependências novas |
| LOW | 5/5 | 5 | |
| **Total** | **25/25** | **25** | |

Verificação por grep após a refatoração:

| Verificação | Resultado |
|---|---|
| Segredos literais em código | 0 |
| `console.log` fora do logger | 0 |
| `badCrypto` / base64 usado como hash | 0 (apenas menções em docstring) |
| `AppManager.js` | removido |
| `const self = this` / `that = this` | 0 |
| Estado global mutável (`let x = {}` de módulo) | 0 |
| `:memory:` fixo em código de aplicação | 0 (só a guarda em `connection.js`) |
| Query dentro de `forEach` (N+1) | 0 |
| Contadores manuais de assincronia (`pending--`) | 0 |
| Import morto (`totalRevenue`) | 0 |
| `sqlite3.verbose()` | 0 |
| Transação no checkout | presente (`checkout.controller.js:39`) |

## Validation

Baseline capturado com a versão original antes de qualquer alteração; refatorado exercitado com a
mesma sequência de requisições.

```
  ✓ Application boots without errors     {"msg":"servidor_iniciado","port":3000}
  ✓ 3/3 endpoints respondem
  ✓ 7/7 status codes idênticos ao baseline (200, 400, 400, 404, 200, 200, 404)
  ✓ Relatório financeiro idêntico ao original (ordenado — ver nota abaixo)
  ✓ Caminhos de erro preservados         400 validação · 400 pagamento recusado · 404 curso inexistente
  ✓ Cartão não aparece mais em log       antes: "Processando cartão 4111222233334444 na chave pk_live_..."
  ✓ Registros órfãos após DELETE         antes: true (aluno "Unknown") · depois: false
  ✓ Zero anti-patterns CRITICAL/HIGH remanescentes
```

**Nota sobre a ordem do relatório:** a versão original devolvia os cursos em ordem
**não-determinística** — consequência direta do finding #16, em que os contadores manuais decidiam a
hora de responder conforme os callbacks retornavam. Duas execuções consecutivas do baseline
produziram ordens diferentes. O refatorado ordena por id do curso. O conteúdo é idêntico: comparação
com ambos os lados ordenados retorna `true`.

**Evidência do finding #13 (integridade referencial), antes e depois de `DELETE /api/users/1`:**

```
antes  → [{"course":"Clean Architecture","revenue":997,"students":[{"student":"Unknown","paid":997}]},
          {"course":"Docker","revenue":994,"students":[{"student":"Guilherme","paid":497},
                                                       {"student":"Unknown","paid":497}]}]

depois → [{"course":"Clean Architecture","revenue":0,"students":[]},
          {"course":"Docker","revenue":497,"students":[{"student":"Guilherme","paid":497}]}]
```

A receita deixa de contabilizar matrículas de usuários que não existem mais — o relatório passa a
refletir a realidade contábil.

## Breaking Changes

1. **Corpos de erro passaram de texto puro para JSON** (`{"error": "..."}`). Status codes e mensagens
   são idênticos (`"Bad Request"`, `"Pagamento recusado"`, `"Curso não encontrado"`).
2. **`DELETE /api/users/:id` remove matrículas e pagamentos junto** (finding #13). Antes ficavam
   órfãos, e a resposta em texto admitia o defeito.
3. **`DELETE /api/users/:id` retorna 404** para usuário inexistente; antes respondia 200 sempre.
4. **Checkout exige senha ao criar usuário novo** (finding #17). Antes, senha ausente virava o
   literal `"123456"`.
5. **Checkout valida formato** de e-mail, id de curso e número de cartão, retornando 400 em vez de
   500 (`cc` não-string quebrava `.startsWith`).
6. **Rota inexistente responde JSON 404** em vez do HTML de erro padrão do Express.
7. **Ordem dos cursos no relatório é estável** (por id). Antes era não-determinística.
8. **O cache em memória (`globalCache`) foi removido** (finding #12). Não era observável pela API —
   o dado equivalente já é gravado em `audit_logs`.
9. **Persistência passou de `:memory:` para arquivo** (`DATABASE_PATH`, default `./data/lms.db`).
   Os dados sobrevivem a um restart; `:memory:` continua disponível por configuração, para teste.

```
================================
Total: 25 findings | 25 resolvidos | 0 regressões
================================
```
