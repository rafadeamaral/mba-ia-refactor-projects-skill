"""Validação de usuário e de login."""
from src.middlewares.exceptions import ValidationError
from src.validators.common import exigir_corpo


def validar_criacao(dados) -> dict:
    dados = exigir_corpo(dados)
    nome = dados.get("nome", "")
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not nome or not email or not senha:
        raise ValidationError("Nome, email e senha são obrigatórios")

    return {"nome": nome, "email": email, "senha": senha}


def validar_login(dados) -> dict:
    dados = exigir_corpo(dados)
    email = dados.get("email", "")
    senha = dados.get("senha", "")

    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")

    return {"email": email, "senha": senha}
