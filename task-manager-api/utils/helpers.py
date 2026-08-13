"""Helpers de uso geral.

Este arquivo era o principal sintoma do anti-pattern "abstração morta": das 9 funções e 7
constantes que definia, **nenhuma** era chamada pelas rotas, que reimplementavam tudo à mão.
A refatoração aplicou a regra "adotar ou remover" a cada símbolo — o que sobrou aqui é o que
passou a ser efetivamente usado.

Removidos: `process_task_data` (substituído por `validators/task_schema.py`), `generate_id` e
`log_action` (sem uso e sem substituto necessário — logging agora é via `logging`).
"""
import re
from datetime import datetime

# --- Constantes de domínio -------------------------------------------------------------------
# Existiam e eram ignoradas: as rotas repetiam os literais. Agora são a fonte única.
VALID_STATUSES = ("pending", "in_progress", "done", "cancelled")
VALID_ROLES = ("user", "admin", "manager")
MAX_TITLE_LENGTH = 200
MIN_TITLE_LENGTH = 3
# Mantido em 4, como no original. Elevar o mínimo é decisão de política de produto, não
# refatoração: mudaria o resultado de requisições que hoje são aceitas. O risco real do finding
# #25 vem do MD5 sem salt, que a refatoração corrige — a recomendação de elevar fica registrada.
MIN_PASSWORD_LENGTH = 4
DEFAULT_PRIORITY = 3
MIN_PRIORITY = 1
MAX_PRIORITY = 5
DEFAULT_COLOR = "#000000"

FORMATOS_DATA = ("%Y-%m-%d", "%d/%m/%Y")
REGEX_EMAIL = re.compile(r"^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$")


def format_date(valor) -> str | None:
    return str(valor) if valor else None


def calculate_percentage(parte: int, total: int) -> float:
    if total == 0:
        return 0
    return round((parte / total) * 100, 2)


def validate_email(email: str) -> bool:
    return bool(email and REGEX_EMAIL.match(email))


def sanitize_string(valor):
    return valor.strip() if isinstance(valor, str) else valor


def is_valid_color(cor: str) -> bool:
    return bool(cor) and len(cor) == 7 and cor[0] == "#"


def parse_date(texto: str) -> datetime | None:
    for formato in FORMATOS_DATA:
        try:
            return datetime.strptime(texto, formato)
        except (TypeError, ValueError):
            continue
    return None
