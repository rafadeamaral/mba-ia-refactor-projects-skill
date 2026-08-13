"""Validações compartilhadas entre recursos."""
from src.constants import PAGINACAO_LIMITE_MAXIMO, PAGINACAO_LIMITE_PADRAO
from src.middlewares.exceptions import ValidationError


def exigir_corpo(dados) -> dict:
    if not dados or not isinstance(dados, dict):
        raise ValidationError("Dados inválidos")
    return dados


def numero_opcional(valor, campo: str) -> float | None:
    """Converte um parâmetro de query em número, traduzindo falha para 400 (era 500)."""
    if valor is None or valor == "":
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        raise ValidationError(f"{campo} deve ser numérico")


def parse_paginacao(args) -> tuple[int, int]:
    limite = numero_opcional(args.get("limit"), "limit")
    offset = numero_opcional(args.get("offset"), "offset")
    limite = PAGINACAO_LIMITE_PADRAO if limite is None else int(limite)
    offset = 0 if offset is None else int(offset)
    return max(1, min(limite, PAGINACAO_LIMITE_MAXIMO)), max(0, offset)
