"""Validação de usuário e login."""
from middlewares.exceptions import ValidationError
from utils.helpers import MIN_PASSWORD_LENGTH, VALID_ROLES, sanitize_string, validate_email
from validators.common import exigir_corpo


def validar_criacao(dados) -> dict:
    dados = exigir_corpo(dados)

    nome = sanitize_string(dados.get("name"))
    email = sanitize_string(dados.get("email"))
    senha = dados.get("password")

    if not nome:
        raise ValidationError("Nome é obrigatório")
    if not email:
        raise ValidationError("Email é obrigatório")
    if not senha:
        raise ValidationError("Senha é obrigatória")

    _validar_email(email)
    _validar_senha(senha)

    papel = dados.get("role", "user")
    _validar_papel(papel)

    return {"name": nome, "email": email, "password": senha, "role": papel}


def validar_atualizacao(dados) -> dict:
    dados = exigir_corpo(dados)
    resultado: dict = {}

    if "name" in dados:
        resultado["name"] = sanitize_string(dados["name"])

    if "email" in dados:
        email = sanitize_string(dados["email"])
        _validar_email(email)
        resultado["email"] = email

    if "password" in dados:
        _validar_senha(dados["password"])
        resultado["password"] = dados["password"]

    if "role" in dados:
        _validar_papel(dados["role"])
        resultado["role"] = dados["role"]

    if "active" in dados:
        resultado["active"] = bool(dados["active"])

    return resultado


def validar_login(dados) -> dict:
    dados = exigir_corpo(dados)
    email = dados.get("email")
    senha = dados.get("password")
    if not email or not senha:
        raise ValidationError("Email e senha são obrigatórios")
    return {"email": email, "password": senha}


def _validar_email(email: str) -> None:
    if not validate_email(email):
        raise ValidationError("Email inválido")


def _validar_senha(senha: str) -> None:
    if not isinstance(senha, str) or len(senha) < MIN_PASSWORD_LENGTH:
        raise ValidationError(f"Senha deve ter no mínimo {MIN_PASSWORD_LENGTH} caracteres")


def _validar_papel(papel: str) -> None:
    if papel not in VALID_ROLES:
        raise ValidationError("Role inválido")
