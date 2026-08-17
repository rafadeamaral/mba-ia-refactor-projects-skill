"""Autenticação e autorização — emissão e verificação reais, ativas por padrão.

A auditoria registrou (finding #6) que a API não tinha autenticação: qualquer cliente anônimo
criava, alterava e apagava produto, movia status de pedido e lia o relatório de vendas.

A primeira tentativa de correção criou estes mesmos decorators atrás de `AUTH_ENABLED`, com
default `false`. O resultado foi pior que não ter feito nada: o relatório passou a contar o
achado como resolvido enquanto as rotas continuavam anônimas em toda execução real. É o
anti-pattern SEC-10 do catálogo, e a razão de a flag ter deixado de existir — não há como
desligar a verificação por configuração.

O token é assinado com HMAC-SHA256 sobre a `SECRET_KEY`, usando apenas biblioteca padrão. Não é
JWT (não há `alg` negociável, o que elimina a classe de ataques de confusão de algoritmo), mas é
uma credencial de verdade: opaca para o cliente, inforjável sem o segredo e com expiração.

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

from src.config.settings import settings
from src.middlewares.exceptions import ForbiddenError, UnauthorizedError

log = logging.getLogger(__name__)

PREFIXO_BEARER = "Bearer "


def _b64(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


def _assinar(corpo: str) -> str:
    return _b64(hmac.new(settings.SECRET_KEY.encode(), corpo.encode(), hashlib.sha256).digest())


def emitir_token(usuario: dict) -> str:
    """Emite a credencial devolvida pelo login."""
    corpo = _b64(json.dumps(
        {"sub": usuario["id"], "tipo": usuario["tipo"], "exp": int(time.time()) + settings.TOKEN_TTL},
        separators=(",", ":"),
    ).encode())
    return f"{corpo}.{_assinar(corpo)}"


def resolver_token(cabecalho: str | None) -> dict | None:
    """Devolve as claims do token, ou None se ausente, malformado, adulterado ou expirado."""
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
    """Exige credencial válida. Sem ela, 401 — não existe caminho que siga adiante."""
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
    """Exige credencial válida e um dos papéis informados. Caso contrário, 403."""
    def decorator(fn):
        @wraps(fn)
        @requer_autenticacao
        def wrapper(*args, **kwargs):
            if g.usuario.get("tipo") not in papeis:
                log.info("acesso_negado rota=%s motivo=papel_insuficiente", request.path)
                raise ForbiddenError("Permissão insuficiente")
            return fn(*args, **kwargs)

        return wrapper

    return decorator
