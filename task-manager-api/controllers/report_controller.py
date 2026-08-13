"""Relatórios de produtividade.

A versão anterior tinha 90 linhas de agregação dentro do handler HTTP, com 12 queries `COUNT`
sequenciais e uma query de tasks por usuário. Aqui a agregação é feita pelo banco.
"""
from datetime import timedelta

from sqlalchemy import case, func

from database import db
from middlewares.exceptions import NotFoundError
from models.category import Category
from models.task import STATUS_TERMINAIS, Task
from models.user import User
from utils.datetime_utils import utc_now
from utils.helpers import calculate_percentage

DIAS_ATIVIDADE_RECENTE = 7

ROTULOS_PRIORIDADE = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "minimal"}


class ReportController:
    def resumo(self) -> dict:
        agora = utc_now()
        corte_recente = agora - timedelta(days=DIAS_ATIVIDADE_RECENTE)

        # Dois GROUP BY no lugar dos doze COUNT sequenciais.
        por_status = dict(db.session.execute(
            db.select(Task.status, func.count()).group_by(Task.status)).all())
        por_prioridade = dict(db.session.execute(
            db.select(Task.priority, func.count()).group_by(Task.priority)).all())

        atrasadas = db.session.execute(
            db.select(Task).filter(
                Task.due_date.is_not(None),
                Task.due_date < agora,
                Task.status.not_in(tuple(STATUS_TERMINAIS)),
            ).order_by(Task.due_date)
        ).scalars().all()

        return {
            "generated_at": str(agora),
            "overview": {
                "total_tasks": sum(por_status.values()),
                "total_users": self._contar(User),
                "total_categories": self._contar(Category),
            },
            "tasks_by_status": {
                "pending": por_status.get("pending", 0),
                "in_progress": por_status.get("in_progress", 0),
                "done": por_status.get("done", 0),
                "cancelled": por_status.get("cancelled", 0),
            },
            "tasks_by_priority": {
                rotulo: por_prioridade.get(nivel, 0)
                for nivel, rotulo in ROTULOS_PRIORIDADE.items()
            },
            "overdue": {
                "count": len(atrasadas),
                "tasks": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "due_date": str(t.due_date),
                        "days_overdue": (agora - t.due_date).days,
                    }
                    for t in atrasadas
                ],
            },
            "recent_activity": {
                "tasks_created_last_7_days": self._contar_tasks(Task.created_at >= corte_recente),
                "tasks_completed_last_7_days": self._contar_tasks(
                    Task.status == "done", Task.updated_at >= corte_recente),
            },
            "user_productivity": self._produtividade_por_usuario(),
        }

    def por_usuario(self, usuario_id: int) -> dict:
        usuario = db.session.get(User, usuario_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")

        agora = utc_now()
        tasks = db.session.execute(
            db.select(Task).filter_by(user_id=usuario_id)).scalars().all()

        contagem = {status: 0 for status in ("done", "pending", "in_progress", "cancelled")}
        atrasadas = alta_prioridade = 0
        for task in tasks:
            if task.status in contagem:
                contagem[task.status] += 1
            if task.priority is not None and task.priority <= 2:
                alta_prioridade += 1
            if task.due_date and task.due_date < agora and task.status not in STATUS_TERMINAIS:
                atrasadas += 1

        return {
            "user": {"id": usuario.id, "name": usuario.name, "email": usuario.email},
            "statistics": {
                "total_tasks": len(tasks),
                **contagem,
                "overdue": atrasadas,
                "high_priority": alta_prioridade,
                "completion_rate": calculate_percentage(contagem["done"], len(tasks)),
            },
        }

    # --- auxiliares ---------------------------------------------------------------------------

    @staticmethod
    def _contar(modelo) -> int:
        return db.session.execute(db.select(func.count()).select_from(modelo)).scalar_one()

    @staticmethod
    def _contar_tasks(*filtros) -> int:
        return db.session.execute(
            db.select(func.count()).select_from(Task).filter(*filtros)).scalar_one()

    @staticmethod
    def _produtividade_por_usuario() -> list[dict]:
        """Uma query agregada — antes era uma query de tasks por usuário, dentro de um laço."""
        linhas = db.session.execute(
            db.select(
                User.id,
                User.name,
                func.count(Task.id),
                func.sum(case((Task.status == "done", 1), else_=0)),
            )
            .outerjoin(Task, Task.user_id == User.id)
            .group_by(User.id)
            .order_by(User.id)
        ).all()

        return [
            {
                "user_id": usuario_id,
                "user_name": nome,
                "total_tasks": total or 0,
                "completed_tasks": concluidas or 0,
                "completion_rate": calculate_percentage(concluidas or 0, total or 0),
            }
            for usuario_id, nome, total, concluidas in linhas
        ]
