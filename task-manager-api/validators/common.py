"""Validações compartilhadas."""
from middlewares.exceptions import ValidationError

LIMITE_PADRAO = 50
LIMITE_MAXIMO = 200


def exigir_corpo(dados) -> dict:
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    return dados


def inteiro_opcional(valor, campo: str) -> int | None:
    if valor is None or valor == "":
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        raise ValidationError(f"{campo} deve ser um número inteiro")


def parse_paginacao(args) -> tuple[int, int]:
    limite = inteiro_opcional(args.get("limit"), "limit") or LIMITE_PADRAO
    offset = inteiro_opcional(args.get("offset"), "offset") or 0
    return max(1, min(limite, LIMITE_MAXIMO)), max(0, offset)
