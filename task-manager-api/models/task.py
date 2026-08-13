"""Entidade Task — dados e regras de domínio. Sem serialização de resposta."""
from database import db
from utils.datetime_utils import utc_now

STATUS_TERMINAIS = frozenset({"done", "cancelled"})


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(50), default="pending")
    priority = db.Column(db.Integer, default=3)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    due_date = db.Column(db.DateTime, nullable=True)
    tags = db.Column(db.String(500), nullable=True)

    # cascade: deletar o usuário remove as tasks dele pelo ORM, em vez de um laço na rota.
    user = db.relationship(
        "User", backref=db.backref("tasks", cascade="all, delete-orphan", lazy="select"))
    category = db.relationship("Category", backref="tasks")

    @property
    def is_overdue(self) -> bool:
        """Regra de domínio única.

        A versão anterior tinha este método (como `is_overdue()`) e nunca o chamava: o mesmo
        `if` triplo aninhado estava reescrito em seis pontos das rotas. Agora é esta a
        implementação usada em todos eles.
        """
        return (
            self.due_date is not None
            and self.due_date < utc_now()
            and self.status not in STATUS_TERMINAIS
        )

    @property
    def tag_list(self) -> list[str]:
        return self.tags.split(",") if self.tags else []

    def __repr__(self) -> str:
        return f"<Task {self.id} {self.title!r}>"
