"""Entidade Category."""
from database import db
from utils.datetime_utils import utc_now


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=True)
    color = db.Column(db.String(7), default="#000000")
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self) -> str:
        return f"<Category {self.id} {self.name!r}>"
