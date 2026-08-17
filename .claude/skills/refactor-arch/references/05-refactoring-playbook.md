# Referência 5 — Playbook de Refatoração (Fase 3)

19 padrões de transformação, cada um com o anti-pattern que resolve e exemplos **antes/depois**. Os
exemplos alternam Python e JavaScript de propósito: o padrão é o mesmo, muda o vocabulário.

| ID | Transformação | Resolve |
|---|---|---|
| [RF-01](#rf-01--extrair-configuração-para-o-ambiente) | Extrair configuração para o ambiente | SEC-01, SEC-07 |
| [RF-02](#rf-02--parametrizar-queries) | Parametrizar queries | SEC-02 |
| [RF-03](#rf-03--hash-de-senha-seguro) | Hash de senha seguro | SEC-03 |
| [RF-04](#rf-04--dto-de-saída) | DTO de saída | SEC-04, ARCH-04 |
| [RF-05](#rf-05--dividir-god-module-em-models-por-domínio) | Dividir God Module em models | ARCH-01 |
| [RF-06](#rf-06--extrair-controller-da-rota) | Extrair controller da rota | ARCH-02, ARCH-03 |
| [RF-07](#rf-07--extrair-camada-de-rotas) | Extrair camada de rotas | ARCH-01, ARCH-11 |
| [RF-08](#rf-08--composition-root-e-injeção-de-dependência) | Composition root e DI | ARCH-05, ARCH-06, ARCH-07 |
| [RF-09](#rf-09--error-handler-centralizado) | Error handler centralizado | ARCH-09, ARCH-10, QUAL-03 |
| [RF-10](#rf-10--fronteira-transacional-e-integridade) | Fronteira transacional e integridade | ARCH-08, PERF-05 |
| [RF-11](#rf-11--eliminar-n1-e-agregação-redundante) | Eliminar N+1 e agregação redundante | PERF-01, PERF-03 |
| [RF-12](#rf-12--paginação) | Paginação | PERF-02 |
| [RF-13](#rf-13--extrair-camada-de-validação) | Extrair camada de validação | QUAL-02, QUAL-01 |
| [RF-14](#rf-14--adotar-ou-remover-código-duplicadomorto) | Adotar ou remover código duplicado/morto | QUAL-01, ARCH-12 |
| [RF-15](#rf-15--extrair-service-para-efeitos-colaterais) | Extrair service para efeitos colaterais | ARCH-02, ARCH-06 |
| [RF-16](#rf-16--callback-hell--asyncawait) | Callback hell → async/await | QUAL-04 |
| [RF-17](#rf-17--constantes-nomeadas-e-enums) | Constantes nomeadas e enums | QUAL-05 |
| [RF-18](#rf-18--logging-estruturado) | Logging estruturado | QUAL-06, SEC-08 |
| [RF-19](#rf-19--remover-superfície-indefensável-e-proteger-rotas) | Remover superfície indefensável | SEC-05, SEC-06 |

---

## RF-01 · Extrair configuração para o ambiente

**Antes**
```python
# app.py
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
CORS(app)
```

**Depois**
```python
# config/settings.py
import os

class Settings:
    SECRET_KEY = os.environ["SECRET_KEY"]                      # falha cedo se ausente
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    DATABASE_PATH = os.getenv("DATABASE_PATH", "loja.db")
    CORS_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "").split(",") if o]
    PORT = int(os.getenv("PORT", "5000"))

settings = Settings()
```
```bash
# .env.example  (versionado — só as chaves)
SECRET_KEY=troque-por-um-valor-aleatorio
DEBUG=false
DATABASE_PATH=loja.db
CORS_ORIGINS=http://localhost:3000
```

**Checklist:** `.env` no `.gitignore`; segredo obrigatório sem default silencioso; nenhum `os.getenv`
espalhado fora do módulo de config; o segredo antigo precisa ser **rotacionado** (continua no histórico
do Git).

---

## RF-02 · Parametrizar queries

**Antes**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```

**Depois**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
```

**Filtros dinâmicos** — o caso que mais tenta a concatenação:

```python
# ✅ cláusulas e parâmetros crescem juntos
def buscar(self, termo=None, categoria=None, preco_max=None):
    sql = "SELECT * FROM produtos WHERE 1=1"
    params = []
    if termo:
        sql += " AND (nome LIKE ? OR descricao LIKE ?)"
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        sql += " AND categoria = ?"
        params.append(categoria)
    if preco_max is not None:
        sql += " AND preco <= ?"
        params.append(preco_max)
    return self._conn.execute(sql, params).fetchall()
```

**Ordenação dinâmica** (identificador não aceita placeholder): valide contra allowlist.
```python
COLUNAS_ORDENAVEIS = {"nome", "preco", "criado_em"}
if ordem not in COLUNAS_ORDENAVEIS:
    raise ValidationError("Coluna de ordenação inválida")
sql += f" ORDER BY {ordem}"
```

---

## RF-03 · Hash de senha seguro

**Antes (JS)**
```js
function badCrypto(pwd) {
    let hash = "";
    for (let i = 0; i < 10000; i++) hash += Buffer.from(pwd).toString('base64').substring(0, 2);
    return hash.substring(0, 10);
}
```

**Depois (JS)**
```js
const bcrypt = require('bcrypt');
const ROUNDS = 12;

const hashPassword  = (plain)         => bcrypt.hash(plain, ROUNDS);
const verifyPassword = (plain, hash)  => bcrypt.compare(plain, hash);
```

**Depois (Python)**
```python
from werkzeug.security import generate_password_hash, check_password_hash

class Usuario:
    def definir_senha(self, senha_pura: str) -> None:
        self.senha_hash = generate_password_hash(senha_pura)   # pbkdf2 com salt

    def verificar_senha(self, senha_pura: str) -> bool:
        return check_password_hash(self.senha_hash, senha_pura)
```

**Migração de base existente:** não é possível reverter MD5/texto plano. Padrão de re-hash no login —
se o valor armazenado estiver no formato antigo e a senha conferir, regrave com o algoritmo novo. Sem
rehash automático, force reset de senha. Documente a escolha no relatório final.

---

## RF-04 · DTO de saída

**Antes**
```python
def to_dict(self):
    return {"id": self.id, "name": self.name, "email": self.email,
            "password": self.password, "role": self.role}     # ⚠ vaza o hash
```

**Depois**
```python
# models/user.py — sem serialização de apresentação
class User(db.Model):
    ...

# views/dto/user_dto.py
PUBLIC_FIELDS = ("id", "name", "email", "role", "active", "created_at")

def user_to_response(user):
    return {f: _serialize(getattr(user, f)) for f in PUBLIC_FIELDS}

def user_with_tasks(user, tasks):
    return {**user_to_response(user), "tasks": [task_to_response(t) for t in tasks]}
```

**Regra:** allowlist, nunca blocklist. Campo novo no model não vaza por padrão — só aparece na resposta
quando alguém o adiciona explicitamente ao DTO.

---

## RF-05 · Dividir God Module em models por domínio

**Antes** — `models.py` com 314 linhas cobrindo produtos, usuários, pedidos e relatórios, com queries
concatenadas e montagem de dicionário de resposta.

**Depois**
```python
# models/produto_model.py
class ProdutoModel:
    def __init__(self, conexao):
        self._conn = conexao                      # injetada (RF-08)

    def listar(self, limite=50, offset=0):
        rows = self._conn.execute(
            "SELECT * FROM produtos ORDER BY id LIMIT ? OFFSET ?", (limite, offset)
        ).fetchall()
        return [Produto.from_row(r) for r in rows]

    def buscar_por_id(self, produto_id):
        row = self._conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
        return Produto.from_row(row) if row else None

    def baixar_estoque(self, produto_id, quantidade):
        self._conn.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
            (quantidade, produto_id, quantidade),
        )
```

**Como dividir:** um arquivo por entidade do domínio; o critério é a **tabela/agregado**, não o tamanho.
Queries que cruzam entidades ficam no model do agregado dono da operação (itens de pedido pertencem a
`PedidoModel`). O que sobra do God Module — regra de negócio → controller; formatação → DTO.

---

## RF-06 · Extrair controller da rota

**Antes**
```python
@task_bp.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data: return jsonify({'error': 'Dados inválidos'}), 400
    if len(data.get('title', '')) < 3: return jsonify({'error': 'Título muito curto'}), 400
    if data.get('status') not in ['pending', 'in_progress', 'done', 'cancelled']:
        return jsonify({'error': 'Status inválido'}), 400
    if data.get('user_id'):
        if not User.query.get(data['user_id']):
            return jsonify({'error': 'Usuário não encontrado'}), 404
    task = Task()
    task.title = data['title']
    # ... mais 40 linhas de atribuição, persistência e serialização
```

**Depois**
```python
# views/task_routes.py — 4 linhas
@task_bp.route("/tasks", methods=["POST"])
def create_task():
    payload = TaskSchema.validate_create(request.get_json())   # RF-13
    task = task_controller.create(payload)                     # levanta exceção de domínio
    return jsonify(task_to_response(task)), 201

# controllers/task_controller.py
class TaskController:
    def __init__(self, task_model, user_model, category_model):
        self._tasks, self._users, self._categories = task_model, user_model, category_model

    def create(self, payload):
        if payload.user_id and not self._users.get(payload.user_id):
            raise NotFoundError("Usuário não encontrado")
        if payload.category_id and not self._categories.get(payload.category_id):
            raise NotFoundError("Categoria não encontrada")
        return self._tasks.create(payload)
```

**Ordem da extração:** (1) mover validação para o schema, (2) mover acesso a dados para o model,
(3) o que sobrar no meio é a regra de negócio — vai para o controller, (4) o handler fica com 3–5 linhas.

---

## RF-07 · Extrair camada de rotas

**Antes**
```python
# app.py — 20 registros manuais no entry point
app.add_url_rule("/produtos", "listar_produtos", controllers.listar_produtos, methods=["GET"])
app.add_url_rule("/produtos/<int:id>", "buscar_produto", controllers.buscar_produto, methods=["GET"])
...
```

**Depois**
```python
# views/produto_routes.py
from flask import Blueprint, jsonify, request

produto_bp = Blueprint("produtos", __name__, url_prefix="/produtos")

def register(controller):
    @produto_bp.route("", methods=["GET"])
    def listar():
        return jsonify({"dados": [produto_to_response(p) for p in controller.listar()]}), 200

    @produto_bp.route("/<int:produto_id>", methods=["GET"])
    def buscar(produto_id):
        return jsonify({"dados": produto_to_response(controller.buscar_por_id(produto_id))}), 200

    return produto_bp
```

**Node/Express**
```js
// routes/checkout.routes.js
const { Router } = require('express');

module.exports = (checkoutController) => {
    const router = Router();
    router.post('/checkout', asyncHandler(async (req, res) => {
        const result = await checkoutController.execute(req.validated);
        res.status(200).json(result);
    }));
    return router;
};
```

**Atenção ao `url_prefix`:** ele muda os paths. Confira o inventário da Fase 1 — `/produtos/busca` com
prefixo `/produtos` vira rota `"/busca"`, e rotas mais específicas devem ser declaradas antes das
paramétricas para não serem capturadas por `<int:id>`.

---

## RF-08 · Composition root e injeção de dependência

**Antes**
```python
# database.py — global mutável + DDL + seed como efeito colateral
db_connection = None

def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("loja.db", check_same_thread=False)
        cursor.execute("CREATE TABLE IF NOT EXISTS produtos (...)")   # DDL escondido
        # ... seed
    return db_connection
```

**Depois**
```python
# database/connection.py — conexão por requisição, sem global mutável
import sqlite3
from flask import g
from config.settings import settings

def get_connection():
    if "db" not in g:
        g.db = sqlite3.connect(settings.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_connection(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()

def init_schema(path):                      # explícito, chamado só na inicialização
    ...
```

```python
# app.py — composition root: só monta
def create_app():
    app = Flask(__name__)
    app.config.from_object(settings)
    CORS(app, origins=settings.CORS_ORIGINS)
    app.teardown_appcontext(close_connection)

    produto_controller = ProdutoController(ProdutoModel(get_connection))
    app.register_blueprint(produto_routes.register(produto_controller))
    register_error_handlers(app)
    return app

if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=settings.PORT, debug=settings.DEBUG)
```

**Ganhos:** sem estado global compartilhado entre threads; schema criado por comando explícito, não por
import; e a app pode ser instanciada com dependências de teste.

---

## RF-09 · Error handler centralizado

**Antes** — 15 blocos idênticos:
```python
try:
    ...
except Exception as e:
    return jsonify({"erro": str(e)}), 500     # vaza interno do banco
```

**Depois**
```python
# middlewares/exceptions.py
class AppError(Exception):
    status = 500
    def __init__(self, message, status=None):
        super().__init__(message)
        self.message, self.status = message, status or self.status

class ValidationError(AppError):   status = 400
class UnauthorizedError(AppError): status = 401
class ForbiddenError(AppError):    status = 403
class NotFoundError(AppError):     status = 404
class ConflictError(AppError):     status = 409
class BusinessRuleError(AppError): status = 422
```
```python
# middlewares/error_handler.py
import logging
log = logging.getLogger(__name__)

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"erro": err.message, "sucesso": False}), err.status

    @app.errorhandler(404)
    def handle_not_found(_):
        return jsonify({"erro": "Recurso não encontrado", "sucesso": False}), 404

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        log.exception("Erro não tratado")                    # detalhe vai para o log
        return jsonify({"erro": "Erro interno", "sucesso": False}), 500   # não para o cliente
```

**Express** (o `asyncHandler` é obrigatório no Express 4, que não propaga rejeição de `async`):
```js
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

app.use((err, req, res, _next) => {
    if (err instanceof AppError) return res.status(err.status).json({ error: err.message });
    logger.error({ err }, 'unhandled error');
    res.status(500).json({ error: 'Erro interno' });
});
```

**Regra:** o cliente recebe mensagem de domínio; a causa técnica vai só para o log. Remova os
`try/except` por endpoint depois de registrar o handler — deixar os dois é pior que nenhum.

---

## RF-10 · Fronteira transacional e integridade

**Antes (JS)** — quatro escritas encadeadas sem transação; falha no meio deixa matrícula sem pagamento.
```js
db.run("INSERT INTO enrollments ...", [userId, cid], function (err) {
    if (err) return res.status(500).send("Erro Matrícula");
    self.db.run("INSERT INTO payments ...", [this.lastID, price, status], function (err) {
        if (err) return res.status(500).send("Erro Pagamento");
        self.db.run("INSERT INTO audit_logs ...", ...);
    });
});
```

**Depois (JS)**
```js
async execute({ userId, courseId, amount }) {
    await this.db.run('BEGIN');
    try {
        const enrollmentId = await this.enrollments.create(userId, courseId);
        await this.payments.create(enrollmentId, amount, 'PAID');
        await this.auditLog.record(`checkout:${courseId}:${userId}`);
        await this.db.run('COMMIT');
        return { enrollmentId };
    } catch (err) {
        await this.db.run('ROLLBACK');
        throw err;                       // o error handler decide o status
    }
}
```

**Depois (Python/SQLAlchemy)**
```python
def criar(self, usuario_id, itens):
    with self._db.session.begin():           # commit no sucesso, rollback na exceção
        pedido = self._pedidos.inserir(usuario_id, total)
        for item in itens:
            self._itens.inserir(pedido.id, item)
            self._produtos.baixar_estoque(item.produto_id, item.quantidade)
    return pedido
```

**Integridade referencial** — declare no schema em vez de emular em laço na aplicação:
```sql
CREATE TABLE enrollments (
    id        INTEGER PRIMARY KEY,
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id)
);
-- SQLite exige ativar por conexão:
PRAGMA foreign_keys = ON;
```
No SQLAlchemy: `db.relationship('Task', cascade='all, delete-orphan')`.

---

## RF-11 · Eliminar N+1 e agregação redundante

**Antes** — 1 + N + 2M queries:
```python
for row in cursor.execute("SELECT * FROM pedidos").fetchall():
    itens = cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in itens:
        prod = cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```

**Depois — SQL direto: um JOIN e agrupamento em memória**
```python
SQL = """
    SELECT p.id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
      FROM pedidos p
      LEFT JOIN itens_pedido i ON i.pedido_id = p.id
      LEFT JOIN produtos pr    ON pr.id = i.produto_id
     WHERE (? IS NULL OR p.usuario_id = ?)
     ORDER BY p.id
"""

def listar(self, usuario_id=None):
    rows = self._conn.execute(SQL, (usuario_id, usuario_id)).fetchall()
    return agrupar_por_pedido(rows)          # 1 query, sempre
```

**Depois — ORM: eager loading**
```python
tasks = db.session.execute(
    db.select(Task).options(joinedload(Task.user), joinedload(Task.category))
).scalars().all()
```

**Agregação redundante** — doze `COUNT` viram um `GROUP BY`:
```python
# antes: um COUNT por status e um por prioridade
por_status = dict(db.session.execute(
    db.select(Task.status, func.count()).group_by(Task.status)
).all())
```

---

## RF-12 · Paginação

**Antes**
```python
tasks = Task.query.all()          # carrega a tabela inteira
```

**Depois**
```python
MAX_LIMIT, DEFAULT_LIMIT = 100, 20

def parse_pagination(args):
    limit = min(int(args.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
    offset = max(int(args.get("offset", 0)), 0)
    return limit, offset

# view
limit, offset = parse_pagination(request.args)
items, total = controller.listar(limit=limit, offset=offset)
return jsonify({"dados": items, "total": total, "limit": limit, "offset": offset}), 200
```

**Compatibilidade:** paginar muda o formato da resposta de listagem — é a única quebra de contrato
tolerada, e precisa aparecer em "Breaking Changes". Se o contrato tiver de ser preservado à risca,
mantenha o envelope atual e aplique só o limite máximo defensivo.

---

## RF-13 · Extrair camada de validação

**Antes** — as mesmas regras em POST e PUT, já divergentes entre si (só o POST valida categoria).

**Depois**
```python
# validators/produto_schema.py
from middlewares.exceptions import ValidationError
from constants import CATEGORIAS_VALIDAS, NOME_MIN, NOME_MAX

def _validar_campos(dados, obrigatorios):
    if not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    for campo in obrigatorios:
        if campo not in dados:
            raise ValidationError(f"{campo} é obrigatório")

    nome = str(dados.get("nome", "")).strip()
    if not NOME_MIN <= len(nome) <= NOME_MAX:
        raise ValidationError(f"Nome deve ter entre {NOME_MIN} e {NOME_MAX} caracteres")
    if float(dados["preco"]) < 0:
        raise ValidationError("Preço não pode ser negativo")
    if int(dados["estoque"]) < 0:
        raise ValidationError("Estoque não pode ser negativo")
    categoria = dados.get("categoria", "geral")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError(f"Categoria inválida. Válidas: {sorted(CATEGORIAS_VALIDAS)}")
    return {"nome": nome, "preco": float(dados["preco"]), "estoque": int(dados["estoque"]),
            "categoria": categoria, "descricao": dados.get("descricao", "")}

validar_criacao    = lambda d: _validar_campos(d, ("nome", "preco", "estoque"))
validar_atualizacao = lambda d: _validar_campos(d, ("nome", "preco", "estoque"))
```

Com `marshmallow`/`pydantic`/`zod` já no projeto, use a biblioteca em vez do validador manual — mas
**só se ela já for dependência**; adicionar biblioteca nova é decisão do usuário.

---

## RF-14 · Adotar ou remover código duplicado/morto

Três variantes da mesma regra (uma nas rotas ×5, uma no model, uma no helper) é pior que uma ruim.
**Escolha a camada correta, adote-a e apague as outras.**

**Antes** — `Task.is_overdue()` existe e nunca é chamado; o `if` triplo é reescrito em 5 lugares:
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            data['overdue'] = True
        else: data['overdue'] = False
    else: data['overdue'] = False
else: data['overdue'] = False
```

**Depois** — a regra vive no model (é uma propriedade da entidade) e todos passam a usá-la:
```python
# models/task.py
TERMINAL_STATUSES = frozenset({"done", "cancelled"})

@property
def is_overdue(self) -> bool:
    return (self.due_date is not None
            and self.due_date < datetime.now(timezone.utc)
            and self.status not in TERMINAL_STATUSES)
```
```python
# views/dto/task_dto.py — único ponto de serialização
def task_to_response(task):
    return {..., "overdue": task.is_overdue}
```

**Duas funções quase iguais** → uma função parametrizada:
```python
# antes: get_pedidos_usuario() e get_todos_pedidos(), 95% idênticas
def listar(self, usuario_id=None):        # depois: uma só, filtro opcional
    ...
```

**Regra de decisão para código morto:** a implementação morta é a correta? Adote e apague as cópias.
Não é? Apague-a. Nunca mantenha as duas.

---

## RF-15 · Extrair service para efeitos colaterais

**Antes**
```python
# controllers.py — dentro do handler HTTP
print("ENVIANDO EMAIL: Pedido " + str(pedido_id) + " criado")
print("ENVIANDO SMS: Seu pedido foi recebido!")
```

**Depois**
```python
# services/notificacao_service.py
class NotificacaoService:
    def __init__(self, email_client, logger):
        self._email, self._log = email_client, logger

    def pedido_criado(self, pedido):
        self._log.info("pedido_criado", extra={"pedido_id": pedido.id})
        self._email.enviar(destino=pedido.usuario_email,
                           assunto=f"Pedido #{pedido.id} recebido",
                           corpo=render_confirmacao(pedido))

# controllers/pedido_controller.py
class PedidoController:
    def __init__(self, pedido_model, notificacao_service):
        self._pedidos, self._notificacao = pedido_model, notificacao_service

    def criar(self, usuario_id, itens):
        pedido = self._pedidos.criar(usuario_id, itens)
        self._notificacao.pedido_criado(pedido)      # dublê em teste, real em produção
        return pedido
```

Vale igualmente para gateway de pagamento: `status = cc.startsWith("4") ? "PAID" : "DENIED"` no handler
vira `PaymentGateway.charge(card, amount)` atrás de uma interface — com a implementação fake explicitamente
nomeada (`FakePaymentGateway`) para que ninguém a confunda com integração real.

---

## RF-16 · Callback hell → async/await

**Antes** — 5 níveis, `this`/`self` misturados, erro tratado em cada nível.
```js
this.db.get("SELECT * FROM courses WHERE id = ?", [cid], (err, course) => {
    if (err || !course) return res.status(404).send("Curso não encontrado");
    this.db.get("SELECT id FROM users WHERE email = ?", [e], (err, user) => {
        this.db.run("INSERT INTO enrollments ...", function (err) {
            self.db.run("INSERT INTO payments ...", function (err) { /* ... */ });
        });
    });
});
```

**Depois** — promisificar o driver uma vez, e o fluxo vira linear:
```js
// database/connection.js
const { promisify } = require('util');

function wrap(db) {
    return {
        get: promisify(db.get.bind(db)),
        all: promisify(db.all.bind(db)),
        run: (sql, params = []) => new Promise((resolve, reject) =>
            db.run(sql, params, function (err) {           // `function` preserva this.lastID
                err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes });
            })),
    };
}
```
```js
// controllers/checkout.controller.js
async execute({ name, email, courseId, card }) {
    const course = await this.courses.findActive(courseId);
    if (!course) throw new NotFoundError('Curso não encontrado');

    const user = await this.users.findByEmail(email) ?? await this.users.create({ name, email });
    const payment = await this.gateway.charge(card, course.price);
    if (payment.status !== 'PAID') throw new BusinessRuleError('Pagamento recusado');

    return this.enrollments.enrollWithPayment(user.id, course, payment);   // transacional (RF-10)
}
```

**Contadores manuais de paralelismo** viram `Promise.all`:
```js
// antes: coursesPending--/enrPending-- decidindo quando responder
const report = await Promise.all(courses.map(async (c) => ({
    course: c.title,
    ...(await this.enrollments.summaryByCourse(c.id)),
})));
```

---

## RF-17 · Constantes nomeadas e enums

**Antes**
```python
if faturamento > 10000:  desconto = faturamento * 0.1
elif faturamento > 5000: desconto = faturamento * 0.05
elif faturamento > 1000: desconto = faturamento * 0.02
```

**Depois**
```python
# constants.py
FAIXAS_DESCONTO = (          # (faturamento mínimo, alíquota) — da maior para a menor
    (10_000, 0.10),
    (5_000,  0.05),
    (1_000,  0.02),
)

# controllers/relatorio_controller.py
def calcular_desconto(faturamento: float) -> float:
    for minimo, aliquota in FAIXAS_DESCONTO:
        if faturamento > minimo:
            return round(faturamento * aliquota, 2)
    return 0.0
```

Para conjuntos de valores válidos, prefira enum a lista de string solta:
```python
class StatusPedido(str, Enum):
    PENDENTE = "pendente"
    APROVADO = "aprovado"
    CANCELADO = "cancelado"

    @classmethod
    def valores(cls): return {s.value for s in cls}
```

Se o projeto já tem constantes declaradas e ignoradas (`VALID_STATUSES`, `MAX_TITLE_LENGTH`), **use as
existentes** em vez de criar um segundo conjunto.

---

## RF-18 · Logging estruturado

**Antes**
```python
print("Login bem-sucedido: " + email)          # PII em stdout, sem nível
print(f"Processando cartão {cc} na chave {key}")   # dado de cartão + segredo
```

**Depois**
```python
# config/logging_config.py
import logging

def configurar_logging(nivel="INFO"):
    logging.basicConfig(
        level=nivel,
        format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )

# uso
log = logging.getLogger(__name__)
log.info("login_ok", extra={"usuario_id": usuario.id})       # id, não e-mail
log.warning("pagamento_recusado", extra={"pedido_id": pedido.id, "bandeira": cartao.bandeira})
```

**Nunca logar:** senha, hash, token, número de cartão, CVV, `SECRET_KEY`, payload completo de request.
Prefira identificadores a dados pessoais. `print` permanece aceitável apenas em scripts de CLI/seed.

---

## RF-19 · Remover superfície indefensável e proteger rotas

**Remover** (não existe versão segura):
```python
# ❌ app.py — executor de SQL arbitrário e reset destrutivo, ambos sem autenticação
@app.route("/admin/query", methods=["POST"])
def executar_query(): cursor.execute(request.get_json()["sql"])

@app.route("/admin/reset-db", methods=["POST"])
def reset_database(): cursor.execute("DELETE FROM pedidos"); ...
```
Um reset de banco legítimo é um **script de manutenção** (`scripts/reset_db.py`), executado por quem tem
acesso ao servidor — não um endpoint HTTP.

**Proteger** o que precisa continuar existindo. A guarda tem de estar **em vigor na configuração padrão**:
uma rota administrativa que continua respondendo 200 anonimamente depois da Fase 3 é um achado aberto,
por mais bem escrito que esteja o decorator que ninguém ligou.

```python
# ❌ o erro clássico: a guarda existe, o achado parece fechado, a rota continua aberta
def requer_autenticacao(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not settings.AUTH_ENABLED:      # default false → decorator transparente
            return fn(*args, **kwargs)
        ...
```

Escolha o mecanismo pelo que o projeto **já tem**, não pelo que seria ideal:

**Caso A — o projeto tem login e identidade de usuário.** Emita no login uma credencial verificável e
exija-a nas rotas protegidas. Um token assinado com HMAC-SHA256 sobre a `SECRET_KEY` resolve com
biblioteca padrão, sem dependência nova e sem tabela nova:

```python
# middlewares/auth.py — emissão e verificação reais, sem dependência externa
import base64, hashlib, hmac, json, time
from functools import wraps

def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()

def emitir_token(usuario_id: int, papel: str, segredo: str, ttl: int = 3600) -> str:
    corpo = _b64(json.dumps({"sub": usuario_id, "papel": papel,
                             "exp": int(time.time()) + ttl}, separators=(",", ":")).encode())
    return f"{corpo}.{_b64(hmac.new(segredo.encode(), corpo.encode(), hashlib.sha256).digest())}"

def resolver_token(cabecalho: str | None, segredo: str) -> dict | None:
    if not cabecalho or not cabecalho.startswith("Bearer "):
        return None
    corpo, _, assinatura = cabecalho[7:].strip().partition(".")
    esperada = _b64(hmac.new(segredo.encode(), corpo.encode(), hashlib.sha256).digest())
    if not assinatura or not hmac.compare_digest(assinatura, esperada):  # tempo constante
        return None
    dados = json.loads(base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4)))
    return None if dados.get("exp", 0) < time.time() else dados

def requer_autenticacao(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        dados = resolver_token(request.headers.get("Authorization"), settings.SECRET_KEY)
        if dados is None:
            raise UnauthorizedError("Autenticação obrigatória")
        g.usuario = dados
        return fn(*args, **kwargs)
    return wrapper

def requer_papel(*papeis):
    def decorator(fn):
        @wraps(fn)
        @requer_autenticacao
        def wrapper(*args, **kwargs):
            if g.usuario.get("papel") not in papeis:
                raise ForbiddenError("Permissão insuficiente")
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

**Caso B — o projeto não tem identidade, só rotas administrativas expostas.** Não invente um sistema de
usuários: exija uma chave administrativa lida do ambiente, comparada em tempo constante. A regra que
importa é o **fail-closed** — chave ausente significa rota inacessível, nunca rota liberada:

```js
// middlewares/auth.js
const crypto = require('node:crypto');

function comparar(a, b) {
    const x = Buffer.from(a), y = Buffer.from(b);
    return x.length === y.length && crypto.timingSafeEqual(x, y);
}

function requerChaveAdministrativa(req, _res, next) {
    // Sem chave configurada a rota fica fechada. O contrário — liberar quando falta
    // configuração — é exatamente o bug que este playbook existe para impedir.
    if (!config.adminApiKey) return next(new UnauthorizedError('Credencial administrativa inválida'));
    const cabecalho = req.headers.authorization || '';
    if (!cabecalho.startsWith('Bearer ') || !comparar(cabecalho.slice(7), config.adminApiKey)) {
        return next(new UnauthorizedError('Credencial administrativa inválida'));
    }
    return next();
}
```

**Quais rotas proteger.** Use a auditoria, não o palpite: toda rota administrativa (`/admin/*`,
relatórios financeiros e gerenciais), toda rota destrutiva (`DELETE`), toda rota mutável (`POST`, `PUT`,
`PATCH`) e toda leitura que exponha dado de terceiros (listagem de usuários, pedidos de outro usuário).
Ficam públicos: health check, índice da API, login, cadastro e o catálogo que já era público por natureza
do produto. Registre a decisão rota a rota no relatório — quem lê precisa poder discordar de um item
específico.

**Consequência esperada no contrato:** rotas que respondiam 200 anonimamente passam a responder 401 sem
credencial. Isso **é** uma breaking change e vai listada como tal. Não é motivo para deixar a rota aberta;
é motivo para documentar como obter a credencial.

**Limite de escopo honesto.** Emitir e verificar credencial com biblioteca padrão está dentro do escopo —
é o que fecha o achado. Ficam fora, e viram recomendação explícita: refresh token, revogação/blacklist,
rotação de chave, MFA, OAuth e políticas de senha do produto. Declare esses resíduos como
"Mitigado parcialmente", nunca como "Resolvido".

**Como provar que fechou** (obrigatório na Fase 3.2):
```bash
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:3000/api/users/1        # 401
curl -s -o /dev/null -w '%{http_code}\n' -X DELETE localhost:3000/api/users/1 \
     -H "Authorization: Bearer $ADMIN_API_KEY"                                        # 200
```
Os dois números precisam aparecer no relatório. Só o segundo prova que não quebrou; só o primeiro prova
que fechou.

---

## Ordem de aplicação e verificação

Aplique na ordem do SKILL.md (config → models → controllers → rotas → validação → middlewares →
correções → composition root). Depois de **cada** bloco, verifique que a aplicação ainda importa e sobe —
descobrir um import quebrado no fim custa muito mais caro do que descobrir no passo seguinte.

**Verificação final por transformação:**

| Verificação | Como conferir |
|---|---|
| Nenhum segredo literal | `grep -rniE "(secret\|password\|key)\s*[:=]\s*['\"]"` no código-fonte |
| Nenhuma query concatenada | busca por `execute(` seguido de `+`, f-string ou template literal |
| Nenhum SQL fora de `models/` | busca por `SELECT\|INSERT\|UPDATE\|DELETE` fora da camada de dados |
| Handlers finos | nenhum handler de rota com mais de ~15 linhas |
| Sem `try/except` repetido | error handler registrado e blocos por endpoint removidos |
| Entry point limpo | `app.py`/`app.js` sem SQL, sem rota inline, sem regra de negócio |
| Contrato preservado | todos os endpoints do inventário respondendo com mesmo status e formato |
