"""Utilitários de data — substitui `datetime.utcnow()`, deprecado no Python 3.12."""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Instante atual em UTC, sem tzinfo.

    `datetime.utcnow()` está deprecado desde o Python 3.12 e a substituição canônica é
    `datetime.now(timezone.utc)`. O `.replace(tzinfo=None)` é deliberado: as colunas
    `db.DateTime` deste projeto guardam valores *naive*, e comparar um datetime ciente de fuso
    com um naive levanta `TypeError`. Migrar as colunas para `DateTime(timezone=True)` exigiria
    migração de dados — fora do escopo desta refatoração.

    Com esta função, a API deprecada some do código e as comparações continuam válidas, em um
    único lugar que documenta a decisão.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
