"""Serialização de categoria."""


def categoria_para_resposta(categoria) -> dict:
    return {
        "id": categoria.id,
        "name": categoria.name,
        "description": categoria.description,
        "color": categoria.color,
        "created_at": str(categoria.created_at),
    }


def categoria_com_contagem(categoria, total_tasks: int) -> dict:
    return {**categoria_para_resposta(categoria), "task_count": total_tasks}
