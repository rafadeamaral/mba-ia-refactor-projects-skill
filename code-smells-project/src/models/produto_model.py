"""Acesso a dados de produtos — queries parametrizadas, sem lógica de apresentação."""
from src.constants import PAGINACAO_LIMITE_PADRAO

COLUNAS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


class ProdutoModel:
    def __init__(self, connection_provider):
        # A conexão é injetada (callable), não importada de uma global de módulo.
        self._conexao = connection_provider

    def listar(self, limite: int = PAGINACAO_LIMITE_PADRAO, offset: int = 0) -> list[dict]:
        linhas = self._conexao().execute(
            f"SELECT {COLUNAS} FROM produtos ORDER BY id LIMIT ? OFFSET ?",
            (limite, offset),
        ).fetchall()
        return [dict(linha) for linha in linhas]

    def buscar_por_id(self, produto_id: int) -> dict | None:
        linha = self._conexao().execute(
            f"SELECT {COLUNAS} FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()
        return dict(linha) if linha else None

    def buscar_por_ids(self, produto_ids: list[int]) -> dict[int, dict]:
        """Carrega vários produtos em uma única query — evita o N+1 na criação de pedido."""
        if not produto_ids:
            return {}
        marcadores = ",".join("?" * len(produto_ids))
        linhas = self._conexao().execute(
            f"SELECT {COLUNAS} FROM produtos WHERE id IN ({marcadores})", tuple(produto_ids)
        ).fetchall()
        return {linha["id"]: dict(linha) for linha in linhas}

    def buscar(self, termo=None, categoria=None, preco_min=None, preco_max=None,
               limite: int = PAGINACAO_LIMITE_PADRAO, offset: int = 0) -> list[dict]:
        """Filtro dinâmico: as cláusulas e os parâmetros crescem juntos, sem concatenar valores."""
        sql = f"SELECT {COLUNAS} FROM produtos WHERE 1=1"
        parametros: list = []

        if termo:
            sql += " AND (nome LIKE ? OR descricao LIKE ?)"
            parametros += [f"%{termo}%", f"%{termo}%"]
        if categoria:
            sql += " AND categoria = ?"
            parametros.append(categoria)
        if preco_min is not None:
            sql += " AND preco >= ?"
            parametros.append(preco_min)
        if preco_max is not None:
            sql += " AND preco <= ?"
            parametros.append(preco_max)

        sql += " ORDER BY id LIMIT ? OFFSET ?"
        parametros += [limite, offset]

        linhas = self._conexao().execute(sql, parametros).fetchall()
        return [dict(linha) for linha in linhas]

    def criar(self, nome: str, descricao: str, preco: float, estoque: int, categoria: str) -> int:
        conexao = self._conexao()
        cursor = conexao.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
        conexao.commit()
        return cursor.lastrowid

    def atualizar(self, produto_id: int, nome: str, descricao: str, preco: float,
                  estoque: int, categoria: str) -> None:
        conexao = self._conexao()
        conexao.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ?"
            " WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )
        conexao.commit()

    def deletar(self, produto_id: int) -> None:
        conexao = self._conexao()
        conexao.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        conexao.commit()

    def contar(self) -> int:
        return self._conexao().execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
