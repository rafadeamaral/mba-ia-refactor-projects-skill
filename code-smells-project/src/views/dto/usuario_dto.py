"""Serialização de usuário — allowlist que mantém a senha fora de qualquer resposta.

A versão anterior devolvia o campo `senha` em `GET /usuarios` e `GET /usuarios/<id>` porque a
montagem do dicionário vivia na camada de dados. Com a allowlist, um campo novo no schema não
vaza por padrão: só aparece na resposta se alguém o adicionar aqui, explicitamente.
"""

CAMPOS_PUBLICOS = ("id", "nome", "email", "tipo", "criado_em")
CAMPOS_LOGIN = ("id", "nome", "email", "tipo")


def usuario_para_resposta(usuario: dict) -> dict:
    return {campo: usuario.get(campo) for campo in CAMPOS_PUBLICOS}


def usuarios_para_resposta(usuarios: list[dict]) -> list[dict]:
    return [usuario_para_resposta(u) for u in usuarios]


def usuario_autenticado_para_resposta(usuario: dict) -> dict:
    return {campo: usuario.get(campo) for campo in CAMPOS_LOGIN}
