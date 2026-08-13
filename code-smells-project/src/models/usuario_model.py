"""Acesso a dados de usuários — senhas sempre com hash, nunca em texto plano."""
from werkzeug.security import check_password_hash, generate_password_hash

from src.constants import PAGINACAO_LIMITE_PADRAO, TIPO_USUARIO_PADRAO

COLUNAS = "id, nome, email, senha, tipo, criado_em"


class UsuarioModel:
    def __init__(self, connection_provider):
        self._conexao = connection_provider

    def listar(self, limite: int = PAGINACAO_LIMITE_PADRAO, offset: int = 0) -> list[dict]:
        linhas = self._conexao().execute(
            f"SELECT {COLUNAS} FROM usuarios ORDER BY id LIMIT ? OFFSET ?", (limite, offset)
        ).fetchall()
        return [dict(linha) for linha in linhas]

    def buscar_por_id(self, usuario_id: int) -> dict | None:
        linha = self._conexao().execute(
            f"SELECT {COLUNAS} FROM usuarios WHERE id = ?", (usuario_id,)
        ).fetchone()
        return dict(linha) if linha else None

    def buscar_por_email(self, email: str) -> dict | None:
        linha = self._conexao().execute(
            f"SELECT {COLUNAS} FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
        return dict(linha) if linha else None

    def criar(self, nome: str, email: str, senha: str, tipo: str = TIPO_USUARIO_PADRAO) -> int:
        conexao = self._conexao()
        cursor = conexao.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, generate_password_hash(senha), tipo),
        )
        conexao.commit()
        return cursor.lastrowid

    def autenticar(self, email: str, senha: str) -> dict | None:
        """Busca por e-mail e compara o hash — a senha nunca entra na query."""
        usuario = self.buscar_por_email(email)
        if usuario is None:
            return None
        if not self._senha_confere(usuario, senha):
            return None
        return usuario

    def _senha_confere(self, usuario: dict, senha: str) -> bool:
        armazenada = usuario["senha"] or ""
        if check_password_hash(armazenada, senha):
            return True
        # Compatibilidade com a base legada, que guardava a senha em texto plano:
        # confere uma única vez e regrava com hash (re-hash on login).
        if armazenada == senha:
            self._regravar_com_hash(usuario["id"], senha)
            return True
        return False

    def _regravar_com_hash(self, usuario_id: int, senha: str) -> None:
        conexao = self._conexao()
        conexao.execute(
            "UPDATE usuarios SET senha = ? WHERE id = ?", (generate_password_hash(senha), usuario_id)
        )
        conexao.commit()

    def contar(self) -> int:
        return self._conexao().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
