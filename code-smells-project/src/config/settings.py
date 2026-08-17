"""Configuração da aplicação — lida do ambiente, sem valores sensíveis no código."""
import logging
import os
import secrets

log = logging.getLogger(__name__)


def _flag(nome: str, padrao: str = "false") -> bool:
    return os.getenv(nome, padrao).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Valores de configuração resolvidos uma única vez, na inicialização."""

    def __init__(self) -> None:
        self.SECRET_KEY = os.getenv("SECRET_KEY") or self._segredo_efemero()
        self.DEBUG = _flag("DEBUG")
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", "loja.db")
        self.HOST = os.getenv("HOST", "127.0.0.1")
        self.PORT = int(os.getenv("PORT", "5000"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        # Validade do token emitido no login, em segundos. Não existe flag para desligar a
        # verificação: guarda que se desliga por configuração não protege nada (SEC-10).
        self.TOKEN_TTL = int(os.getenv("TOKEN_TTL_SEGUNDOS", "3600"))
        self.CORS_ORIGINS = [
            origem.strip()
            for origem in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if origem.strip()
        ]

    @staticmethod
    def _segredo_efemero() -> str:
        """Gera um segredo aleatório quando SECRET_KEY não está no ambiente.

        Mantém a aplicação executável em desenvolvimento sem reintroduzir um segredo
        versionado. Como o valor muda a cada boot, sessões não sobrevivem a um restart —
        o que torna a ausência da variável visível em vez de silenciosa.
        """
        log.warning("SECRET_KEY ausente no ambiente; gerando valor efêmero para esta execução")
        return secrets.token_urlsafe(32)


settings = Settings()
