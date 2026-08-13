"""Reset do banco — substitui o endpoint POST /admin/reset-db.

Uma operação destrutiva não deve ser exposta como rota HTTP. Aqui ela exige acesso ao servidor
e confirmação explícita.

Uso:
    python scripts/reset_db.py --confirmar
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.settings import settings  # noqa: E402
from src.database.schema import init_schema, limpar_dados  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Apaga todos os dados e recria a carga inicial.")
    parser.add_argument("--confirmar", action="store_true",
                        help="obrigatório: confirma a operação destrutiva")
    args = parser.parse_args()

    if not args.confirmar:
        print("Operação destrutiva. Execute novamente com --confirmar para prosseguir.")
        return 1

    print(f"Resetando banco em {settings.DATABASE_PATH}...")
    limpar_dados(settings.DATABASE_PATH)
    init_schema(settings.DATABASE_PATH)
    print("Banco resetado e recarregado com os dados iniciais.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
