"""Criação de schema e carga inicial — explícitos, não como efeito colateral de leitura."""
import logging

from werkzeug.security import generate_password_hash

from src.constants import STATUS_PEDIDO_INICIAL
from src.database.connection import abrir_conexao

log = logging.getLogger(__name__)

TABELAS = (
    """
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        descricao TEXT,
        preco REAL,
        estoque INTEGER,
        categoria TEXT,
        ativo INTEGER DEFAULT 1,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT,
        email TEXT,
        senha TEXT,
        tipo TEXT DEFAULT 'cliente',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    f"""
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        status TEXT DEFAULT '{STATUS_PEDIDO_INICIAL}',
        total REAL,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS itens_pedido (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER,
        produto_id INTEGER,
        quantidade INTEGER,
        preco_unitario REAL
    )
    """,
)

PRODUTOS_INICIAIS = (
    ("Notebook Gamer", "Notebook potente para jogos", 5999.99, 10, "informatica"),
    ("Mouse Wireless", "Mouse sem fio ergonômico", 89.90, 50, "informatica"),
    ("Teclado Mecânico", "Teclado mecânico RGB", 299.90, 30, "informatica"),
    ("Monitor 27''", "Monitor 27 polegadas 144hz", 1899.90, 15, "informatica"),
    ("Headset Gamer", "Headset com microfone", 199.90, 25, "informatica"),
    ("Cadeira Gamer", "Cadeira ergonômica", 1299.90, 8, "moveis"),
    ("Webcam HD", "Webcam 1080p", 249.90, 20, "informatica"),
    ("Hub USB", "Hub USB 3.0 7 portas", 79.90, 40, "informatica"),
    ("SSD 1TB", "SSD NVMe 1TB", 449.90, 35, "informatica"),
    ("Camiseta Dev", "Camiseta estampa código", 59.90, 100, "vestuario"),
)

# Credenciais de desenvolvimento: gravadas com hash, nunca em texto plano.
USUARIOS_INICIAIS = (
    ("Admin", "admin@loja.com", "admin123", "admin"),
    ("João Silva", "joao@email.com", "123456", "cliente"),
    ("Maria Santos", "maria@email.com", "senha123", "cliente"),
)


def init_schema(caminho: str | None = None) -> None:
    """Cria as tabelas e popula o banco quando ele está vazio."""
    conexao = abrir_conexao(caminho)
    try:
        for ddl in TABELAS:
            conexao.execute(ddl)
        conexao.commit()

        if conexao.execute("SELECT COUNT(*) FROM produtos").fetchone()[0] == 0:
            _carregar_dados_iniciais(conexao)
            log.info("carga_inicial_concluida produtos=%d usuarios=%d",
                     len(PRODUTOS_INICIAIS), len(USUARIOS_INICIAIS))
    finally:
        conexao.close()


def _carregar_dados_iniciais(conexao) -> None:
    conexao.executemany(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        PRODUTOS_INICIAIS,
    )
    conexao.executemany(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        [(nome, email, generate_password_hash(senha), tipo)
         for nome, email, senha, tipo in USUARIOS_INICIAIS],
    )
    conexao.commit()


def limpar_dados(caminho: str | None = None) -> None:
    """Esvazia todas as tabelas. Chamado por scripts/reset_db.py, nunca por uma rota HTTP."""
    conexao = abrir_conexao(caminho)
    try:
        for tabela in ("itens_pedido", "pedidos", "produtos", "usuarios"):
            conexao.execute(f"DELETE FROM {tabela}")
        conexao.commit()
    finally:
        conexao.close()
