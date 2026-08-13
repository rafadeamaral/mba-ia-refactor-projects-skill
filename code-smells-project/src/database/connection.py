"""Conexão com o banco — por requisição, sem estado global mutável."""
import sqlite3

from flask import g

from src.config.settings import settings


def abrir_conexao(caminho: str | None = None) -> sqlite3.Connection:
    """Abre uma conexão nova. Usado fora do ciclo de requisição (scripts, inicialização)."""
    conexao = sqlite3.connect(caminho or settings.DATABASE_PATH)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def get_connection() -> sqlite3.Connection:
    """Conexão ligada ao contexto da requisição atual.

    Substitui o singleton global de módulo: cada requisição tem a sua conexão, fechada
    no teardown, o que elimina a corrida entre threads da versão anterior.
    """
    if "db" not in g:
        g.db = abrir_conexao()
    return g.db


def close_connection(_excecao=None) -> None:
    conexao = g.pop("db", None)
    if conexao is not None:
        conexao.close()
