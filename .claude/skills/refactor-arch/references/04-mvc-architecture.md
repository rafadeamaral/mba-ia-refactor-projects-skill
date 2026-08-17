# Referência 4 — Guidelines de Arquitetura MVC (Fase 3)

Regras do padrão alvo. Valem para qualquer linguagem — o que muda é o vocabulário do framework, não a
divisão de responsabilidades.

---

## 1. As camadas e o fluxo

```
   HTTP request
        │
        ▼
┌──────────────────┐   traduz HTTP ↔ chamada de aplicação. Sem regra de negócio, sem SQL.
│  VIEWS / ROUTES  │
└────────┬─────────┘
         │ dados já validados
         ▼
┌──────────────────┐   orquestra o caso de uso. Decide, calcula, compõe. Não conhece SQL.
│   CONTROLLERS    │
└────────┬─────────┘
         │ entidades / parâmetros de domínio
         ▼
┌──────────────────┐   fala com o banco. Não conhece HTTP nem formata resposta.
│      MODELS      │
└────────┬─────────┘
         ▼
     Banco de dados

Transversais: CONFIG · MIDDLEWARES · VALIDATORS · SERVICES · DTOs
```

**Regra de dependência — direção única:** `views → controllers → models`.
Uma camada nunca importa a de cima. Se um model importa um controller, o desenho está errado.

---

## 2. Responsabilidade de cada camada

### Views / Routes

**Faz:** declarar rota (método + path); extrair path/query params e corpo; chamar o validator; chamar
**um** método de controller; traduzir o retorno em status + corpo HTTP.

**Não faz:** SQL ou chamada de ORM; cálculo de domínio; `try/except` por endpoint (isso é do error
handler); montar o DTO de saída campo a campo.

**Tamanho esperado:** 3 a 10 linhas por handler. Um handler que passou de 15 linhas está acumulando
responsabilidade de outra camada.

```python
# ✅ handler fino
@produto_bp.route("/produtos/<int:produto_id>", methods=["GET"])
def buscar_produto(produto_id):
    produto = produto_controller.buscar_por_id(produto_id)   # levanta NotFoundError
    return jsonify({"dados": produto.to_response()}), 200
```

### Controllers

**Faz:** orquestrar o caso de uso; aplicar regras de negócio; coordenar múltiplos models; abrir a
fronteira transacional; disparar efeitos colaterais **através de services injetados**; levantar exceções
de domínio (`NotFoundError`, `ValidationError`, `BusinessRuleError`).

**Não faz:** escrever SQL; tocar em `request`/`response`/`session` do framework; decidir código HTTP;
importar o módulo de rotas.

**Teste de fronteira:** o controller deve ser chamável de um script CLI ou de um worker sem nenhuma
simulação de HTTP. Se não for, ele tem I/O de web dentro.

```python
# ✅ regra de negócio isolada e testável
class PedidoController:
    def __init__(self, pedido_model, produto_model, notificador):
        self._pedidos = pedido_model
        self._produtos = produto_model
        self._notificador = notificador

    def criar(self, usuario_id, itens):
        produtos = self._produtos.buscar_por_ids([i["produto_id"] for i in itens])
        total = self._calcular_total(itens, produtos)          # regra pura
        pedido = self._pedidos.criar(usuario_id, itens, total) # transacional
        self._notificador.pedido_criado(pedido)                # efeito injetado
        return pedido
```

### Models

**Faz:** representar a entidade; encapsular acesso a dados (queries parametrizadas ou ORM); expor
operações de domínio sobre os próprios dados (`is_overdue()`, `tem_estoque(qtd)`); garantir invariantes.

**Não faz:** montar resposta HTTP; formatar para exibição; importar `request`/`jsonify`/`res`; conhecer
o framework web; devolver `{"erro": ...}` como fluxo de controle — levante exceção.

> **Model vs Repository:** em projetos sem ORM, separar `Produto` (entidade) de `ProdutoModel`
> (acesso a dados) é legítimo e recomendado. Com ORM ativo (SQLAlchemy, Sequelize), o model já é a
> entidade — nesse caso concentre as queries complexas em um repositório ou em métodos de classe, nunca
> nas rotas.

### Config

Um único módulo lê o ambiente e expõe valores tipados. **Zero segredo literal no código.** `.env` no
`.gitignore`, `.env.example` versionado com as chaves e valores fictícios. Config é lida uma vez, na
inicialização — não espalhada por `os.getenv` no meio da lógica.

### Middlewares

Preocupações transversais, registradas uma vez no composition root: error handler global (traduz exceção
de domínio → status HTTP), logging de request, CORS restrito, autenticação, rate limiting, handler 404.

### Validators / Schemas

Regras de forma da entrada (obrigatoriedade, tipo, tamanho, formato, faixa, valores permitidos),
**compartilhadas entre criação e atualização**. Regra de forma ≠ regra de negócio: "preço é número
positivo" é validator; "não vender abaixo do custo" é controller.

### Services

Integrações externas e efeitos colaterais (e-mail, SMS, gateway de pagamento, storage), atrás de uma
interface. Sempre **injetados** no controller — nunca instanciados dentro dele. Isso permite substituir
por um dublê em teste e trocar o provedor sem tocar na regra.

### DTOs / Serializers

Definem o que **sai** para o cliente. Existem justamente para que o model possa ter campos que a API
nunca deve expor (hash de senha, flags internas). Serialização de saída não pertence ao model.

---

## 3. Estrutura de diretórios alvo

**Python / Flask:**

```
src/
├── config/settings.py           # env, sem segredo literal
├── models/                      # um arquivo por entidade
│   ├── produto_model.py
│   └── usuario_model.py
├── controllers/                 # um por domínio
│   ├── produto_controller.py
│   └── pedido_controller.py
├── views/                       # blueprints
│   └── produto_routes.py
├── validators/produto_schema.py
├── services/notificacao_service.py
├── middlewares/error_handler.py
├── database/connection.py       # conexão/sessão por requisição
└── app.py                       # composition root
```

**Node / Express:** mesma divisão, com `routes/` no lugar de `views/` e sufixos `.controller.js`,
`.model.js`, `.routes.js` — a convenção da comunidade prevalece sobre a nomenclatura literal do MVC.

### Adaptação ao ponto de partida

| Nível de partida | O que fazer |
|---|---|
| **A — Monolito plano** | Criar toda a árvore; mover código por responsabilidade, não por arquivo |
| **B — Separação nominal** | **Manter a árvore existente** e realocar responsabilidade: extrair controllers das rotas, mover queries para os models, remover camadas mortas |
| **C — MVC parcial** | Adicionar só o que falta (config, middlewares, validators) |
| **D — MVC adequado** | Correções pontuais. Não reestruture o que já está certo |

> Renomear pastas em um projeto nível B/C que já usa `routes/` e `services/` costuma custar mais do que
> entrega. Respeite a convenção vigente do projeto quando ela já for coerente.

---

## 4. Regras que a refatoração precisa satisfazer

1. **Config sem segredo hardcoded** — todo valor sensível vem do ambiente.
2. **Models abstraem os dados** — nenhum SQL fora da camada de models.
3. **Views/Routes só roteiam** — handlers finos, sem regra de negócio.
4. **Controllers concentram o fluxo** — o caso de uso está legível em um só lugar.
5. **Error handling centralizado** — nenhum `try/except` repetitivo por endpoint.
6. **Entry point claro** — o arquivo principal só monta a aplicação.
7. **Dependências injetadas** — nada de `new Database()` dentro de regra de negócio.
8. **Escritas relacionadas são transacionais** — tudo ou nada.
9. **Saída filtrada por DTO** — o cliente recebe apenas o que deve receber.
10. **Contrato preservado** — mesmos endpoints, status e formato de resposta, salvo as duas exceções de
    segurança (parar de vazar dado sensível; fechar rota que estava aberta).
11. **Guardas de acesso na fronteira, ligadas** — autenticação e autorização vivem em `middlewares/` e são
    aplicadas na camada de rotas, junto da declaração do endpoint, para que a política seja legível ao
    lado do path que ela protege. Guarda declarada e não aplicada, ou aplicada e desligada por padrão, é
    ausência de guarda.

## 5. Anti-regras — o que *não* fazer na refatoração

- **Não** criar camadas vazias para cumprir tabela (`services/` que ninguém importa vira ARCH-12).
- **Não** trocar o framework, o banco ou adicionar ORM: refatoração muda estrutura, não tecnologia.
- **Não** implementar funcionalidade nova (JWT completo, cache distribuído) sob o nome de refatoração —
  registre como recomendação fora de escopo.
- **Não** renomear endpoints, campos de payload ou códigos de status.
- **Não** dividir por dividir: um arquivo de 40 linhas com responsabilidade única não precisa virar três.
- **Não** deixar as duas versões do mesmo código convivendo. Migrou, apagou o antigo.
