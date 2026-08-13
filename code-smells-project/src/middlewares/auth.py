"""Ponto de extensão para autenticação e autorização.

A auditoria registrou (finding #6) que a API não possui autenticação. Emitir e verificar
tokens de verdade é funcionalidade nova, fora do escopo de uma refatoração — o que existe
aqui é o ponto de extensão pronto: os decorators já aplicam a política, bastando implementar
`_resolver_usuario` com o mecanismo escolhido (JWT, sessão, API key).

Enquanto `AUTH_ENABLED` for falso, os decorators são transparentes e o comportamento dos
endpoints permanece idêntico ao original.
"""
import os
from functools import wraps

from flask import g, request

from src.middlewares.exceptions import ForbiddenError, UnauthorizedError

AUTH_ENABLED = os.getenv("AUTH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _resolver_usuario(_authorization: str | None):
    """Ponto de implementação da verificação de credencial. Ver docstring do módulo."""
    raise NotImplementedError(
        "Autenticação não implementada. Defina AUTH_ENABLED=false ou implemente a verificação."
    )


def requer_autenticacao(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if AUTH_ENABLED:
            usuario = _resolver_usuario(request.headers.get("Authorization"))
            if usuario is None:
                raise UnauthorizedError("Autenticação obrigatória")
            g.usuario = usuario
        return fn(*args, **kwargs)

    return wrapper


def requer_papel(*papeis: str):
    def decorator(fn):
        @wraps(fn)
        @requer_autenticacao
        def wrapper(*args, **kwargs):
            if AUTH_ENABLED and getattr(g, "usuario", None) and g.usuario.get("tipo") not in papeis:
                raise ForbiddenError("Permissão insuficiente")
            return fn(*args, **kwargs)

        return wrapper

    return decorator
