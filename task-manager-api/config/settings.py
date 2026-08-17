"""Configuração da aplicação — lida do ambiente, sem valores sensíveis no código."""
import logging
import os
import secrets

log = logging.getLogger(__name__)


def _flag(nome: str, padrao: str = "false") -> bool:
    return os.getenv(nome, padrao).strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        self.SECRET_KEY = os.getenv("SECRET_KEY") or self._segredo_efemero()
        self.DEBUG = _flag("DEBUG")
        self.SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///tasks.db")
        self.SQLALCHEMY_TRACK_MODIFICATIONS = False
        self.HOST = os.getenv("HOST", "127.0.0.1")
        self.PORT = int(os.getenv("PORT", "5000"))
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
        self.CORS_ORIGINS = [
            o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ]
        # Validade do token emitido no login, em segundos. Não existe flag para desligar a
        # verificação: guarda desligável por configuração não protege nada (SEC-10).
        self.TOKEN_TTL = int(os.getenv("TOKEN_TTL_SEGUNDOS", "3600"))

    @staticmethod
    def _segredo_efemero() -> str:
        """Gera um segredo aleatório quando SECRET_KEY não está no ambiente.

        Mantém a aplicação executável em desenvolvimento sem reintroduzir um segredo versionado.
        Como muda a cada boot, a ausência da variável fica visível em vez de silenciosa.
        """
        log.warning("SECRET_KEY ausente no ambiente; gerando valor efêmero para esta execução")
        return secrets.token_urlsafe(32)


settings = Settings()
