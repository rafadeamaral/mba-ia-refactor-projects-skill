"""Fluxo de tasks — regra de negócio fora do handler HTTP."""
import logging

from sqlalchemy import func
from sqlalchemy.orm import joinedload

from database import db
from middlewares.exceptions import NotFoundError
from models.category import Category
from models.task import STATUS_TERMINAIS, Task
from models.user import User
from utils.datetime_utils import utc_now
from utils.helpers import calculate_percentage

log = logging.getLogger(__name__)


class TaskController:
    def __init__(self, notificacao_service=None):
        self._notificacao = notificacao_service

    # --- leitura ------------------------------------------------------------------------------

    def listar(self, limite: int, offset: int) -> list[Task]:
        """Carrega user e category junto — antes eram duas queries extras por task."""
        return db.session.execute(
            db.select(Task)
            .options(joinedload(Task.user), joinedload(Task.category))
            .order_by(Task.id)
            .limit(limite)
            .offset(offset)
        ).scalars().all()

    def buscar_por_id(self, task_id: int) -> Task:
        task = db.session.get(Task, task_id)
        if task is None:
            raise NotFoundError("Task não encontrada")
        return task

    def buscar(self, termo=None, status=None, prioridade=None, usuario_id=None,
               limite: int = 50, offset: int = 0) -> list[Task]:
        consulta = db.select(Task)

        if termo:
            consulta = consulta.filter(
                db.or_(Task.title.like(f"%{termo}%"), Task.description.like(f"%{termo}%")))
        if status:
            consulta = consulta.filter(Task.status == status)
        if prioridade is not None:
            consulta = consulta.filter(Task.priority == prioridade)
        if usuario_id is not None:
            consulta = consulta.filter(Task.user_id == usuario_id)

        consulta = consulta.order_by(Task.id).limit(limite).offset(offset)
        return db.session.execute(consulta).scalars().all()

    def listar_por_usuario(self, usuario_id: int) -> list[Task]:
        return db.session.execute(
            db.select(Task).filter_by(user_id=usuario_id).order_by(Task.id)
        ).scalars().all()

    def estatisticas(self) -> dict:
        """Contagens agregadas no banco — antes eram 5 queries + um laço sobre todas as tasks."""
        por_status = dict(db.session.execute(
            db.select(Task.status, func.count()).group_by(Task.status)).all())

        total = sum(por_status.values())
        concluidas = por_status.get("done", 0)

        # Contagem no banco em vez de laço sobre todas as tasks em memória.
        atrasadas = db.session.execute(
            db.select(func.count()).select_from(Task).filter(
                Task.due_date.is_not(None),
                Task.due_date < utc_now(),
                Task.status.not_in(tuple(STATUS_TERMINAIS)),
            )
        ).scalar_one()

        return {
            "total": total,
            "pending": por_status.get("pending", 0),
            "in_progress": por_status.get("in_progress", 0),
            "done": concluidas,
            "cancelled": por_status.get("cancelled", 0),
            "overdue": atrasadas,
            "completion_rate": calculate_percentage(concluidas, total),
        }

    # --- escrita ------------------------------------------------------------------------------

    def criar(self, dados: dict) -> Task:
        self._verificar_relacionados(dados)

        task = Task(**dados)
        db.session.add(task)
        db.session.commit()

        log.info("task_criada task_id=%s", task.id)
        if self._notificacao and task.user_id:
            self._notificacao.task_atribuida(task)
        return task

    def atualizar(self, task_id: int, dados: dict) -> Task:
        task = self.buscar_por_id(task_id)
        self._verificar_relacionados(dados)

        usuario_anterior = task.user_id
        for campo, valor in dados.items():
            setattr(task, campo, valor)
        db.session.commit()

        log.info("task_atualizada task_id=%s", task.id)
        if self._notificacao and task.user_id and task.user_id != usuario_anterior:
            self._notificacao.task_atribuida(task)
        return task

    def deletar(self, task_id: int) -> None:
        task = self.buscar_por_id(task_id)
        db.session.delete(task)
        db.session.commit()
        log.info("task_deletada task_id=%s", task_id)

    def _verificar_relacionados(self, dados: dict) -> None:
        """Integridade referencial checada em um só lugar, para criação e atualização."""
        if dados.get("user_id") and db.session.get(User, dados["user_id"]) is None:
            raise NotFoundError("Usuário não encontrado")
        if dados.get("category_id") and db.session.get(Category, dados["category_id"]) is None:
            raise NotFoundError("Categoria não encontrada")
