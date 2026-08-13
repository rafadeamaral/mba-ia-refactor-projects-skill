"""Fluxo de produtos — regra de negócio, sem HTTP e sem SQL."""
import logging

from src.middlewares.exceptions import NotFoundError

log = logging.getLogger(__name__)


class ProdutoController:
    def __init__(self, produto_model):
        self._produtos = produto_model

    def listar(self, limite: int, offset: int) -> list[dict]:
        return self._produtos.listar(limite=limite, offset=offset)

    def buscar_por_id(self, produto_id: int) -> dict:
        produto = self._produtos.buscar_por_id(produto_id)
        if produto is None:
            raise NotFoundError("Produto não encontrado")
        return produto

    def buscar(self, termo, categoria, preco_min, preco_max, limite: int, offset: int) -> list[dict]:
        return self._produtos.buscar(
            termo=termo, categoria=categoria, preco_min=preco_min, preco_max=preco_max,
            limite=limite, offset=offset,
        )

    def criar(self, dados: dict) -> int:
        produto_id = self._produtos.criar(**dados)
        log.info("produto_criado produto_id=%s", produto_id)
        return produto_id

    def atualizar(self, produto_id: int, dados: dict) -> None:
        self.buscar_por_id(produto_id)  # 404 se não existir
        self._produtos.atualizar(produto_id, **dados)
        log.info("produto_atualizado produto_id=%s", produto_id)

    def deletar(self, produto_id: int) -> None:
        self.buscar_por_id(produto_id)
        self._produtos.deletar(produto_id)
        log.info("produto_deletado produto_id=%s", produto_id)
