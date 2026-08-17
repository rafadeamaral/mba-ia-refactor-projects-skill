# ecommerce-api-legacy

LMS API (cursos, matrículas, pagamentos) em Node.js/Express. Projeto refatorado para MVC pela skill
`refactor-arch` (relatório da auditoria em [`../reports/audit-project-2.md`](../reports/audit-project-2.md)).

## Como rodar

```bash
npm install
cp .env.example .env      # opcional em desenvolvimento
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é criado em `./data/lms.db` (configurável
por `DATABASE_PATH`) e recebe a carga inicial apenas quando está vazio — a versão anterior usava
`:memory:` fixo no código e perdia todos os pagamentos a cada restart.

Exemplos de requisições estão em `api.http`.

## Estrutura

```
server.js                            bootstrap: abre o banco, inicializa o schema, sobe o servidor
src/
├── app.js                           composition root — createApp({ db })
├── config/                          configuração vinda do ambiente
├── database/
│   ├── connection.js                driver promisificado + helper de transação
│   └── schema.js                    DDL com chaves estrangeiras e seed idempotente
├── models/                          user, course, enrollment, payment, audit, password
├── controllers/                     checkout, report, user
├── routes/                          express.Router() por domínio
├── services/payment.gateway.js      FakePaymentGateway atrás de interface
├── validators/                      validação de entrada
├── middlewares/                     erros de domínio, error handler, asyncHandler, auth
└── utils/logger.js                  logging estruturado
```

O fluxo é `routes → controllers → models`: rotas não contêm SQL nem regra de negócio, controllers não
conhecem HTTP, models não montam resposta.

## Endpoints

| Método | Path | Descrição |
|---|---|---|
| POST | `/api/checkout` | matrícula com pagamento — transacional |
| GET | `/api/admin/financial-report` | receita e alunos por curso |
| DELETE | `/api/users/:id` | remove usuário e seus registros dependentes |

O payload do checkout mantém os nomes originais (`usr`, `eml`, `pwd`, `c_id`, `card`) para não quebrar
clientes existentes.

### Mudanças de comportamento

- **Corpos de erro agora são JSON** (`{"error": "..."}`) em vez de texto puro. Status codes e mensagens
  são idênticos aos anteriores.
- **`DELETE /api/users/:id` remove matrículas e pagamentos junto** (`ON DELETE CASCADE`). Antes eles
  ficavam órfãos no banco e o relatório financeiro passava a somar receita de alunos `Unknown`.
- **`DELETE /api/users/:id` retorna 404** para usuário inexistente; antes respondia 200 sempre.
- **Checkout exige senha ao criar usuário novo.** Antes, senha ausente virava o literal `"123456"`.
- **Checkout valida formato** de e-mail, id de curso e número de cartão, retornando 400.
- **Rota inexistente responde JSON 404** em vez do HTML de erro padrão do Express.

## Pagamento

O gateway continua sendo um stub — a aprovação depende do primeiro dígito do cartão, como antes. A
diferença é que a regra está isolada em `src/services/payment.gateway.js`, nomeada honestamente como
`FakePaymentGateway` e injetada no controller, de modo que a integração real substitui uma classe sem
tocar no fluxo de checkout. O número do cartão **não é mais registrado em log** (apenas os 4 últimos
dígitos).

## Autorização das rotas administrativas

`GET /api/admin/financial-report` e `DELETE /api/users/:id` **exigem credencial**, e não há
configuração que desligue a verificação — a versão anterior desta refatoração deixava o middleware
atrás de `AUTH_ENABLED=false`, o que na prática mantinha as duas rotas anônimas.

Este projeto não tem login nem identidade de usuário exposta por HTTP, então a credencial é uma chave
administrativa lida do ambiente e comparada em tempo constante (`src/middlewares/auth.js`):

```bash
ADMIN_API_KEY=uma-chave-longa-e-aleatoria node server.js

curl localhost:3000/api/admin/financial-report -H "Authorization: Bearer uma-chave-longa-e-aleatoria"
```

Sem `ADMIN_API_KEY` no ambiente, o boot gera uma chave aleatória e a registra no log — as rotas
continuam **fechadas** para quem não a tem. Chave ausente nunca significa rota liberada.

`POST /api/checkout` permanece público: é o fluxo de compra da loja, e autenticar o comprador exigiria
um sistema de contas que o produto não tem. Isso está registrado como gap conhecido no relatório, não
como achado resolvido.
