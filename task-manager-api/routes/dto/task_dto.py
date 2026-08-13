"""Serialização de task — ponto único de montagem da resposta.

A versão anterior montava o dicionário à mão em três lugares (`task_routes.py:17-28`,
`user_routes.py:162-169`) além do `to_dict()` do model, e as três versões já divergiam entre si.
"""


def _data(valor) -> str | None:
    return str(valor) if valor else None


def task_para_resposta(task, incluir_overdue: bool = False, incluir_relacionados: bool = False):
    dados = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "user_id": task.user_id,
        "category_id": task.category_id,
        "created_at": str(task.created_at),
        "updated_at": str(task.updated_at),
        "due_date": _data(task.due_date),
        "tags": task.tag_list,
    }

    if incluir_overdue:
        dados["overdue"] = task.is_overdue

    if incluir_relacionados:
        dados["user_name"] = task.user.name if task.user else None
        dados["category_name"] = task.category.name if task.category else None

    return dados


def task_resumida_para_resposta(task) -> dict:
    """Formato reduzido usado por `GET /users/<id>/tasks`."""
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status,
        "priority": task.priority,
        "created_at": str(task.created_at),
        "due_date": _data(task.due_date),
        "overdue": task.is_overdue,
    }
