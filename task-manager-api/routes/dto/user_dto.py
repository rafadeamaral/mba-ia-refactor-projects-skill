"""Serialização de usuário — allowlist que mantém a senha fora de qualquer resposta.

A versão anterior expunha o hash MD5 em `GET /users/<id>`, `POST /users`, `PUT /users/<id>` e no
payload de login, porque o serializador era o `to_dict()` do próprio model de persistência.
Com allowlist, um campo novo no schema não vaza por padrão.
"""

CAMPOS_PUBLICOS = ("id", "name", "email", "role", "active")


def usuario_para_resposta(usuario) -> dict:
    dados = {campo: getattr(usuario, campo) for campo in CAMPOS_PUBLICOS}
    dados["created_at"] = str(usuario.created_at)
    return dados


def usuario_com_contagem(usuario, total_tasks: int) -> dict:
    return {**usuario_para_resposta(usuario), "task_count": total_tasks}
