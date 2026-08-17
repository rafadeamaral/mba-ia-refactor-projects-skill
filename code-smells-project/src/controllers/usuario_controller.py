"""Fluxo de usuários e autenticação."""
import logging

from src.middlewares.exceptions import NotFoundError, UnauthorizedError

log = logging.getLogger(__name__)


class UsuarioController:
    def __init__(self, usuario_model, emissor_token):
        self._usuarios = usuario_model
        # Emissor injetado: trocar o formato da credencial (JWT de biblioteca, sessão em banco)
        # é mudar o argumento do composition root, não este arquivo.
        self._emitir_token = emissor_token

    def listar(self, limite: int, offset: int) -> list[dict]:
        return self._usuarios.listar(limite=limite, offset=offset)

    def buscar_por_id(self, usuario_id: int) -> dict:
        usuario = self._usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, dados: dict) -> int:
        usuario_id = self._usuarios.criar(**dados)
        log.info("usuario_criado usuario_id=%s", usuario_id)
        return usuario_id

    def autenticar(self, email: str, senha: str) -> dict:
        """Autentica e emite a credencial usada pelas rotas protegidas."""
        usuario = self._usuarios.autenticar(email, senha)
        if usuario is None:
            log.info("login_falhou")
            raise UnauthorizedError("Email ou senha inválidos")
        log.info("login_ok usuario_id=%s", usuario["id"])
        return {"usuario": usuario, "token": self._emitir_token(usuario)}
