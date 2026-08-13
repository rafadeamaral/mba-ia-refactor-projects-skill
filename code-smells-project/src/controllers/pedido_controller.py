"""Fluxo de pedidos — validação de estoque, precificação e notificação."""
import logging

from src.constants import STATUS_PEDIDO_APROVADO, STATUS_PEDIDO_CANCELADO
from src.middlewares.exceptions import BusinessRuleError, NotFoundError

log = logging.getLogger(__name__)


class PedidoController:
    def __init__(self, pedido_model, produto_model, notificacao_service):
        self._pedidos = pedido_model
        self._produtos = produto_model
        self._notificacao = notificacao_service

    def listar(self, usuario_id: int | None, limite: int, offset: int) -> list[dict]:
        return self._pedidos.listar(usuario_id=usuario_id, limite=limite, offset=offset)

    def criar(self, usuario_id: int, itens: list[dict]) -> dict:
        itens_precificados, total = self._precificar(itens)
        pedido_id = self._pedidos.criar(usuario_id, total, itens_precificados)
        log.info("pedido_criado pedido_id=%s usuario_id=%s total=%s", pedido_id, usuario_id, total)
        self._notificacao.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def _precificar(self, itens: list[dict]) -> tuple[list[dict], float]:
        """Carrega todos os produtos em uma query e aplica as regras de negócio do pedido."""
        produtos = self._produtos.buscar_por_ids([item["produto_id"] for item in itens])

        precificados, total = [], 0.0
        for item in itens:
            produto = produtos.get(item["produto_id"])
            if produto is None:
                raise BusinessRuleError(f"Produto {item['produto_id']} não encontrado")
            if produto["estoque"] < item["quantidade"]:
                raise BusinessRuleError(f"Estoque insuficiente para {produto['nome']}")

            total += produto["preco"] * item["quantidade"]
            precificados.append({
                "produto_id": produto["id"],
                "produto_nome": produto["nome"],
                "quantidade": item["quantidade"],
                "preco_unitario": produto["preco"],
            })
        return precificados, total

    def atualizar_status(self, pedido_id: int, novo_status: str) -> None:
        if self._pedidos.buscar_por_id(pedido_id) is None:
            raise NotFoundError("Pedido não encontrado")

        self._pedidos.atualizar_status(pedido_id, novo_status)
        log.info("pedido_status_atualizado pedido_id=%s status=%s", pedido_id, novo_status)

        if novo_status in (STATUS_PEDIDO_APROVADO, STATUS_PEDIDO_CANCELADO):
            self._notificacao.status_alterado(pedido_id, novo_status)
