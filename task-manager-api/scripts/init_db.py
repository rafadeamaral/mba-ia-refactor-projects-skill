"""Criação do schema — passo explícito, no lugar do db.create_all() no import.

Uso:
    python scripts/init_db.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, init_schema  # noqa: E402
from config.settings import settings  # noqa: E402


def main() -> int:
    aplicacao = create_app()
    init_schema(aplicacao)
    print(f"Schema criado em {settings.SQLALCHEMY_DATABASE_URI}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
