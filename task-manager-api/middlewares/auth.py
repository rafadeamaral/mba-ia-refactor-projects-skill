"""Autenticação e autorização — emissão e verificação reais, ativas por padrão.

A auditoria registrou (finding #3) que o login devolvia `'fake-jwt-token-<id>'`, que nenhuma rota
verificava credencial e que o campo `role` — com três valores semeados: `admin`, `manager`, `user` —
nunca era consultado por nenhum `if`.

A primeira tentativa de correção removeu o token falso (acerto) e criou estes decorators atrás de
`AUTH_ENABLED`, com default `false` (erro). O efeito prático foi zero: as 22 rotas continuaram
anônimas e o relatório passou a contar o achado como resolvido — o anti-pattern SEC-10 do catálogo.
A flag deixou de existir; não há configuração que devolva as rotas ao estado anônimo.

O token é assinado com HMAC-SHA256 sobre a `SECRET_KEY`, usando apenas biblioteca padrão — nenhuma
dependência nova em `requirements.txt`. Não é JWT: não há cabeçalho `alg` negociável, o que elimina
a classe de ataques de confusão de algoritmo, e o formato é opaco para o cliente.

Fora de escopo, declarado no relatório: revogação/blacklist, refresh token e rotação de chave.
"""
import base64
import hashlib
import hmac
import json
import logging
import time
from functools import wraps

from flask import g, request

from config.settings import settings
from middlewares.exceptions import ForbiddenError, UnauthorizedError

log = logging.getLogger(__name__)

PREFIXO_BEARER = "Bearer "

PAPEL_ADMIN = "admin"
PAPEL_MANAGER = "manager"


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


def _assinar(corpo: str) -> str:
    return _b64(hmac.new(settings.SECRET_KEY.encode(), corpo.encode(), hashlib.sha256).digest())


def emitir_token(usuario) -> str:
    """Emite a credencial devolvida por POST /login."""
    corpo = _b64(json.dumps(
        {"sub": usuario.id, "role": usuario.role, "exp": int(time.time()) + settings.TOKEN_TTL},
        separators=(",", ":"),
    ).encode())
    return f"{corpo}.{_assinar(corpo)}"


def resolver_token(cabecalho: str | None) -> dict | None:
    """Devolve as claims, ou None se ausente, malformado, adulterado ou expirado."""
    if not cabecalho or not cabecalho.startswith(PREFIXO_BEARER):
        return None

    corpo, separador, assinatura = cabecalho[len(PREFIXO_BEARER):].strip().partition(".")
    if not separador or not hmac.compare_digest(assinatura, _assinar(corpo)):
        return None  # compare_digest: comparação em tempo constante

    try:
        claims = json.loads(base64.urlsafe_b64decode(corpo + "=" * (-len(corpo) % 4)))
    except (ValueError, json.JSONDecodeError):
        return None

    return None if claims.get("exp", 0) < time.time() else claims


def requer_autenticacao(fn):
    """Exige credencial válida. Sem ela, 401 — não há caminho que siga adiante."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        claims = resolver_token(request.headers.get("Authorization"))
        if claims is None:
            log.info("acesso_negado rota=%s motivo=credencial_invalida", request.path)
            raise UnauthorizedError("Autenticação obrigatória")
        g.usuario = claims
        return fn(*args, **kwargs)

    return wrapper


def requer_papel(*papeis: str):
    """Exige credencial válida e um dos papéis informados. Caso contrário, 403.

    É aqui que a coluna `role` finalmente passa a ter efeito — ela existia no schema desde o
    início e nenhuma linha de código a consultava.
    """
    def decorator(fn):
        @wraps(fn)
        @requer_autenticacao
        def wrapper(*args, **kwargs):
            if g.usuario.get("role") not in papeis:
                log.info("acesso_negado rota=%s motivo=papel_insuficiente", request.path)
                raise ForbiddenError("Permissão insuficiente")
            return fn(*args, **kwargs)

        return wrapper

    return decorator
