#!/usr/bin/env python3
"""Sincroniza a skill `refactor-arch` da fonte única para os três projetos.

A skill é mantida em um lugar só — `.claude/skills/refactor-arch/`, na raiz do repositório — e
copiada para dentro de cada projeto. O desafio pede a pasta **dentro dos 3 projetos** (DESAFIO.md,
linhas 208, 224 e 280), então as cópias precisam ser arquivos de verdade: symlink versionado no Git
chega como arquivo de texto contendo o caminho em qualquer clone Windows sem Developer Mode, e a
skill simplesmente não carregaria para quem for avaliar.

Uso:
    python scripts/sync-skill.py            # copia a fonte para os 3 projetos
    python scripts/sync-skill.py --check    # não escreve nada; sai com 1 se houver divergência
"""
from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FONTE = RAIZ / ".claude" / "skills" / "refactor-arch"
PROJETOS = ("code-smells-project", "ecommerce-api-legacy", "task-manager-api")


def destinos() -> list[Path]:
    return [RAIZ / p / ".claude" / "skills" / "refactor-arch" for p in PROJETOS]


def divergentes(destino: Path) -> list[str]:
    """Nomes relativos dos arquivos que diferem da fonte (ou faltam, ou sobram)."""
    if not destino.exists():
        return ["<pasta inexistente>"]

    esperados = {p.relative_to(FONTE).as_posix() for p in FONTE.rglob("*") if p.is_file()}
    presentes = {p.relative_to(destino).as_posix() for p in destino.rglob("*") if p.is_file()}

    diferencas = sorted(esperados ^ presentes)
    diferencas += sorted(
        nome for nome in esperados & presentes
        if not filecmp.cmp(FONTE / nome, destino / nome, shallow=False)
    )
    return diferencas


def main() -> int:
    if not FONTE.is_dir():
        print(f"ERRO: fonte não encontrada em {FONTE}", file=sys.stderr)
        return 2

    checar = "--check" in sys.argv[1:]
    problemas = 0

    for destino in destinos():
        diferencas = divergentes(destino)
        rotulo = destino.relative_to(RAIZ).as_posix()

        if not diferencas:
            print(f"  ok        {rotulo}")
            continue

        if checar:
            problemas += 1
            print(f"  DIVERGE   {rotulo}: {', '.join(diferencas)}")
            continue

        shutil.rmtree(destino, ignore_errors=True)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(FONTE, destino)
        print(f"  atualizado {rotulo} ({len(diferencas)} arquivo(s))")

    if checar and problemas:
        print(f"\n{problemas} projeto(s) fora de sincronia. Rode: python scripts/sync-skill.py")
        return 1

    print("\nSkill sincronizada a partir de .claude/skills/refactor-arch/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
