"""Relatório de vendas — regra de desconto isolada e testável."""
from src.constants import FAIXAS_DESCONTO


class RelatorioController:
    def __init__(self, pedido_model):
        self._pedidos = pedido_model

    def vendas(self) -> dict:
        dados = self._pedidos.estatisticas()

        total_pedidos = dados["total_pedidos"]
        faturamento = dados["faturamento"] or 0
        desconto = calcular_desconto(faturamento)

        return {
            "total_pedidos": total_pedidos,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": dados["pendentes"],
            "pedidos_aprovados": dados["aprovados"],
            "pedidos_cancelados": dados["cancelados"],
            "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
        }


def calcular_desconto(faturamento: float) -> float:
    """Função pura: as faixas vêm de constantes nomeadas, não de literais no meio do cálculo."""
    for minimo, aliquota in FAIXAS_DESCONTO:
        if faturamento > minimo:
            return faturamento * aliquota
    return 0.0
