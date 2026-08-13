"""Acesso a dados de pedidos — listagem com JOIN e criação transacional."""
from src.constants import (
    PAGINACAO_LIMITE_PADRAO,
    STATUS_PEDIDO_APROVADO,
    STATUS_PEDIDO_CANCELADO,
    STATUS_PEDIDO_INICIAL,
)
from src.middlewares.exceptions import BusinessRuleError

# Uma única query resolve pedidos + itens + nome do produto.
# A versão anterior fazia 1 + N + M queries para o mesmo resultado.
SQL_LISTAGEM = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario,
           pr.nome AS produto_nome
      FROM (SELECT * FROM pedidos {filtro} ORDER BY id LIMIT ? OFFSET ?) p
      LEFT JOIN itens_pedido i ON i.pedido_id = p.id
      LEFT JOIN produtos pr    ON pr.id = i.produto_id
     ORDER BY p.id, i.id
"""

SQL_ESTATISTICAS = f"""
    SELECT COUNT(*)                                                      AS total_pedidos,
           COALESCE(SUM(total), 0)                                       AS faturamento,
           COALESCE(SUM(CASE WHEN status = '{STATUS_PEDIDO_INICIAL}'  THEN 1 ELSE 0 END), 0) AS pendentes,
           COALESCE(SUM(CASE WHEN status = '{STATUS_PEDIDO_APROVADO}' THEN 1 ELSE 0 END), 0) AS aprovados,
           COALESCE(SUM(CASE WHEN status = '{STATUS_PEDIDO_CANCELADO}' THEN 1 ELSE 0 END), 0) AS cancelados
      FROM pedidos
"""


class PedidoModel:
    def __init__(self, connection_provider):
        self._conexao = connection_provider

    def listar(self, usuario_id: int | None = None,
               limite: int = PAGINACAO_LIMITE_PADRAO, offset: int = 0) -> list[dict]:
        filtro = "WHERE usuario_id = ?" if usuario_id is not None else ""
        parametros = ([usuario_id] if usuario_id is not None else []) + [limite, offset]
        linhas = self._conexao().execute(SQL_LISTAGEM.format(filtro=filtro), parametros).fetchall()
        return self._agrupar_por_pedido(linhas)

    @staticmethod
    def _agrupar_por_pedido(linhas) -> list[dict]:
        pedidos: dict[int, dict] = {}
        for linha in linhas:
            pedido = pedidos.setdefault(linha["id"], {
                "id": linha["id"],
                "usuario_id": linha["usuario_id"],
                "status": linha["status"],
                "total": linha["total"],
                "criado_em": linha["criado_em"],
                "itens": [],
            })
            if linha["produto_id"] is not None:
                pedido["itens"].append({
                    "produto_id": linha["produto_id"],
                    "produto_nome": linha["produto_nome"] or "Desconhecido",
                    "quantidade": linha["quantidade"],
                    "preco_unitario": linha["preco_unitario"],
                })
        return list(pedidos.values())

    def buscar_por_id(self, pedido_id: int) -> dict | None:
        linha = self._conexao().execute(
            "SELECT id, usuario_id, status, total, criado_em FROM pedidos WHERE id = ?",
            (pedido_id,),
        ).fetchone()
        return dict(linha) if linha else None

    def criar(self, usuario_id: int, total: float, itens: list[dict]) -> int:
        """Cria pedido, itens e baixa de estoque em uma única transação.

        `itens` já vem validado e precificado pelo controller:
        [{"produto_id": int, "quantidade": int, "preco_unitario": float}, ...]
        """
        conexao = self._conexao()
        try:
            cursor = conexao.execute(
                "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
                (usuario_id, STATUS_PEDIDO_INICIAL, total),
            )
            pedido_id = cursor.lastrowid

            for item in itens:
                conexao.execute(
                    "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario)"
                    " VALUES (?, ?, ?, ?)",
                    (pedido_id, item["produto_id"], item["quantidade"], item["preco_unitario"]),
                )
                # A condição de estoque na própria UPDATE evita a corrida entre requisições
                # concorrentes: se outro pedido consumiu o estoque no meio, rowcount é 0.
                baixa = conexao.execute(
                    "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                    (item["quantidade"], item["produto_id"], item["quantidade"]),
                )
                if baixa.rowcount == 0:
                    raise BusinessRuleError(
                        f"Estoque insuficiente para {item.get('produto_nome', item['produto_id'])}"
                    )

            conexao.commit()
            return pedido_id
        except Exception:
            conexao.rollback()
            raise

    def atualizar_status(self, pedido_id: int, novo_status: str) -> None:
        conexao = self._conexao()
        conexao.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
        conexao.commit()

    def estatisticas(self) -> dict:
        """Uma query agregada no lugar dos cinco COUNT/SUM sequenciais da versão anterior."""
        return dict(self._conexao().execute(SQL_ESTATISTICAS).fetchone())

    def contar(self) -> int:
        return self._conexao().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
