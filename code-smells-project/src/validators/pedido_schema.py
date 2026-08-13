"""Validação de pedido e de mudança de status."""
from src.constants import STATUS_PEDIDO_VALIDOS
from src.middlewares.exceptions import ValidationError
from src.validators.common import exigir_corpo


def validar_criacao(dados) -> dict:
    dados = exigir_corpo(dados)

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens or len(itens) == 0:
        raise ValidationError("Pedido deve ter pelo menos 1 item")

    itens_normalizados = []
    for item in itens:
        if not isinstance(item, dict) or "produto_id" not in item or "quantidade" not in item:
            raise ValidationError("Item inválido: informe produto_id e quantidade")
        quantidade = item["quantidade"]
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ValidationError("Quantidade deve ser um inteiro positivo")
        itens_normalizados.append({"produto_id": item["produto_id"], "quantidade": quantidade})

    return {"usuario_id": usuario_id, "itens": itens_normalizados}


def validar_status(dados) -> str:
    dados = exigir_corpo(dados)
    status = dados.get("status", "")
    if status not in STATUS_PEDIDO_VALIDOS:
        raise ValidationError("Status inválido")
    return status
