"""Validação de categoria."""
from middlewares.exceptions import ValidationError
from utils.helpers import DEFAULT_COLOR, is_valid_color, sanitize_string
from validators.common import exigir_corpo


def validar_criacao(dados) -> dict:
    dados = exigir_corpo(dados)

    nome = sanitize_string(dados.get("name"))
    if not nome:
        raise ValidationError("Nome é obrigatório")

    cor = dados.get("color", DEFAULT_COLOR)
    _validar_cor(cor)

    return {"name": nome, "description": dados.get("description", ""), "color": cor}


def validar_atualizacao(dados) -> dict:
    dados = exigir_corpo(dados)
    resultado: dict = {}

    if "name" in dados:
        nome = sanitize_string(dados["name"])
        if not nome:
            raise ValidationError("Nome é obrigatório")
        resultado["name"] = nome

    if "description" in dados:
        resultado["description"] = dados["description"]

    if "color" in dados:
        _validar_cor(dados["color"])
        resultado["color"] = dados["color"]

    return resultado


def _validar_cor(cor: str) -> None:
    if not is_valid_color(cor):
        raise ValidationError("Cor inválida. Use o formato #RRGGBB")
