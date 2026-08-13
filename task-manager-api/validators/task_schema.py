"""Validação de task — as mesmas regras para criação e atualização.

A versão anterior escrevia essas regras duas vezes (`create_task` e `update_task`), e uma
terceira vez em `utils.helpers.process_task_data`, que era código morto.
"""
from middlewares.exceptions import ValidationError
from utils.helpers import (
    MAX_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_PRIORITY,
    MIN_TITLE_LENGTH,
    VALID_STATUSES,
    parse_date,
    sanitize_string,
)
from validators.common import exigir_corpo


def validar_criacao(dados) -> dict:
    dados = exigir_corpo(dados)
    if "title" not in dados or not dados.get("title"):
        raise ValidationError("Título é obrigatório")
    return _validar(dados, campos=set(dados.keys()) | {"title"})


def validar_atualizacao(dados) -> dict:
    return _validar(exigir_corpo(dados), campos=set(dados.keys()))


def _validar(dados: dict, campos: set) -> dict:
    resultado: dict = {}

    if "title" in campos:
        titulo = sanitize_string(dados.get("title")) or ""
        if len(titulo) < MIN_TITLE_LENGTH:
            raise ValidationError("Título muito curto")
        if len(titulo) > MAX_TITLE_LENGTH:
            raise ValidationError("Título muito longo")
        resultado["title"] = titulo

    if "description" in campos:
        resultado["description"] = dados.get("description")

    if "status" in campos:
        status = dados.get("status")
        if status not in VALID_STATUSES:
            raise ValidationError("Status inválido")
        resultado["status"] = status

    if "priority" in campos:
        prioridade = dados.get("priority")
        if not isinstance(prioridade, int) or isinstance(prioridade, bool):
            raise ValidationError("Prioridade inválida")
        if prioridade < MIN_PRIORITY or prioridade > MAX_PRIORITY:
            raise ValidationError(f"Prioridade deve ser entre {MIN_PRIORITY} e {MAX_PRIORITY}")
        resultado["priority"] = prioridade

    if "user_id" in campos:
        resultado["user_id"] = dados.get("user_id")

    if "category_id" in campos:
        resultado["category_id"] = dados.get("category_id")

    if "due_date" in campos:
        bruto = dados.get("due_date")
        if bruto:
            data = parse_date(bruto)
            if data is None:
                raise ValidationError("Formato de data inválido. Use YYYY-MM-DD")
            resultado["due_date"] = data
        else:
            resultado["due_date"] = None

    if "tags" in campos:
        tags = dados.get("tags")
        resultado["tags"] = ",".join(tags) if isinstance(tags, list) else tags

    return resultado
