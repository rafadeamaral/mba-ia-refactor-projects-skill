"""Fluxo de categorias."""
import logging

from sqlalchemy import func

from database import db
from middlewares.exceptions import NotFoundError
from models.category import Category
from models.task import Task

log = logging.getLogger(__name__)


class CategoryController:
    def listar(self) -> list[tuple[Category, int]]:
        """Categorias com contagem de tasks em uma query — antes era um COUNT por categoria."""
        linhas = db.session.execute(
            db.select(Category, func.count(Task.id))
            .outerjoin(Task, Task.category_id == Category.id)
            .group_by(Category.id)
            .order_by(Category.id)
        ).all()
        return [(categoria, total) for categoria, total in linhas]

    def buscar_por_id(self, categoria_id: int) -> Category:
        categoria = db.session.get(Category, categoria_id)
        if categoria is None:
            raise NotFoundError("Categoria não encontrada")
        return categoria

    def criar(self, dados: dict) -> Category:
        categoria = Category(**dados)
        db.session.add(categoria)
        db.session.commit()
        log.info("categoria_criada categoria_id=%s", categoria.id)
        return categoria

    def atualizar(self, categoria_id: int, dados: dict) -> Category:
        categoria = self.buscar_por_id(categoria_id)
        for campo, valor in dados.items():
            setattr(categoria, campo, valor)
        db.session.commit()
        return categoria

    def deletar(self, categoria_id: int) -> None:
        categoria = self.buscar_por_id(categoria_id)
        db.session.delete(categoria)
        db.session.commit()
        log.info("categoria_deletada categoria_id=%s", categoria_id)
