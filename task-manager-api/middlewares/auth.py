"""Ponto de extensão para autenticação e autorização.

A auditoria registrou (finding #3) que o login devolvia `'fake-jwt-token-<id>'` e que nenhuma
rota verificava credencial alguma. A refatoração removeu o token falso — devolver credencial
simulada é pior que não devolver nenhuma, porque induz o cliente a acreditar que há sessão.

Implementar emissão e verificação de token é funcionalidade nova, fora do escopo de uma
refatoração. O que existe aqui é o ponto de extensão: implemente `_resolver_usuario` e ligue
`AUTH_ENABLED=true`. Enquanto isso, os decorators são transparentes.
"""
from functools import wraps

from flask import g, request

from config.settings import settings
from middlewares.exceptions import ForbiddenError, UnauthorizedError


def _resolver_usuario(_authorization: str | None):
    raise NotImplementedError(
        "Autenticação não implementada — ver middlewares/auth.py"
    )


def requer_autenticacao(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not settings.AUTH_ENABLED:
            return fn(*args, **kwargs)

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
            if settings.AUTH_ENABLED and getattr(g, "usuario", None) is not None:
                if g.usuario.role not in papeis:
                    raise ForbiddenError("Permissão insuficiente")
            return fn(*args, **kwargs)

        return wrapper

    return decorator
