"""Health check — apenas conectividade e contagens, sem expor configuração."""


class HealthController:
    def __init__(self, produto_model, usuario_model, pedido_model):
        self._produtos = produto_model
        self._usuarios = usuario_model
        self._pedidos = pedido_model

    def status(self) -> dict:
        return {
            "status": "ok",
            "database": "connected",
            "counts": {
                "produtos": self._produtos.contar(),
                "usuarios": self._usuarios.contar(),
                "pedidos": self._pedidos.contar(),
            },
            "versao": "1.0.0",
        }
