"""Fluxo de usuários e autenticação."""
import logging

from sqlalchemy import func

from database import db
from middlewares.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from models.task import Task
from models.user import User

log = logging.getLogger(__name__)


class UserController:
    def listar(self, limite: int, offset: int) -> list[tuple[User, int]]:
        """Usuários com a contagem de tasks em uma única query (antes: len(u.tasks) por usuário)."""
        linhas = db.session.execute(
            db.select(User, func.count(Task.id))
            .outerjoin(Task, Task.user_id == User.id)
            .group_by(User.id)
            .order_by(User.id)
            .limit(limite)
            .offset(offset)
        ).all()
        return [(usuario, total) for usuario, total in linhas]

    def buscar_por_id(self, usuario_id: int) -> User:
        usuario = db.session.get(User, usuario_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, dados: dict) -> User:
        self._garantir_email_livre(dados["email"])

        usuario = User(name=dados["name"], email=dados["email"], role=dados["role"])
        usuario.set_password(dados["password"])

        db.session.add(usuario)
        db.session.commit()
        log.info("usuario_criado usuario_id=%s", usuario.id)
        return usuario

    def atualizar(self, usuario_id: int, dados: dict) -> User:
        usuario = self.buscar_por_id(usuario_id)

        if "email" in dados:
            self._garantir_email_livre(dados["email"], ignorar_id=usuario_id)

        senha = dados.pop("password", None)
        for campo, valor in dados.items():
            setattr(usuario, campo, valor)
        if senha:
            usuario.set_password(senha)

        db.session.commit()
        log.info("usuario_atualizado usuario_id=%s", usuario.id)
        return usuario

    def deletar(self, usuario_id: int) -> None:
        usuario = self.buscar_por_id(usuario_id)
        # As tasks saem por cascade no relacionamento — antes eram apagadas em laço na rota.
        db.session.delete(usuario)
        db.session.commit()
        log.info("usuario_deletado usuario_id=%s", usuario_id)

    def autenticar(self, email: str, senha: str) -> User:
        usuario = db.session.execute(
            db.select(User).filter_by(email=email)).scalar_one_or_none()

        if usuario is None or not usuario.check_password(senha):
            log.info("login_falhou")
            raise UnauthorizedError("Credenciais inválidas")
        if not usuario.active:
            raise ForbiddenError("Usuário inativo")

        log.info("login_ok usuario_id=%s", usuario.id)
        return usuario

    def _garantir_email_livre(self, email: str, ignorar_id: int | None = None) -> None:
        existente = db.session.execute(
            db.select(User).filter_by(email=email)).scalar_one_or_none()
        if existente and existente.id != ignorar_id:
            raise ConflictError("Email já cadastrado")
