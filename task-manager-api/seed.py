"""Script para popular o banco com dados iniciais.

Usa a factory `create_app()` — a versão anterior fazia `from app import app`, e o simples import
já criava o schema como efeito colateral.
"""
from datetime import timedelta

from app import create_app, init_schema
from database import db
from models.category import Category
from models.task import Task
from models.user import User
from utils.datetime_utils import utc_now

USUARIOS = (
    ("João Silva", "joao@email.com", "1234", "admin"),
    ("Maria Santos", "maria@email.com", "abcd", "user"),
    ("Pedro Oliveira", "pedro@email.com", "pass", "manager"),
)

CATEGORIAS = (
    ("Backend", "Tarefas de backend", "#3498db"),
    ("Frontend", "Tarefas de frontend", "#2ecc71"),
    ("DevOps", "Tarefas de infraestrutura", "#e74c3c"),
    ("Bug", "Correção de bugs", "#e67e22"),
)


def _tasks(agora, usuarios, categorias):
    u1, u2, u3 = usuarios
    c1, c2, c3, c4 = categorias
    return (
        {"title": "Implementar autenticação JWT", "description": "Adicionar autenticação real com JWT",
         "status": "pending", "priority": 1, "user_id": u1.id, "category_id": c1.id,
         "due_date": agora - timedelta(days=3)},
        {"title": "Criar tela de login", "description": "Tela de login responsiva",
         "status": "in_progress", "priority": 2, "user_id": u2.id, "category_id": c2.id,
         "due_date": agora + timedelta(days=5)},
        {"title": "Configurar CI/CD", "description": "Pipeline com GitHub Actions",
         "status": "done", "priority": 2, "user_id": u3.id, "category_id": c3.id,
         "tags": "devops,ci,github"},
        {"title": "Corrigir bug no filtro de busca",
         "description": "Filtro não funciona com caracteres especiais",
         "status": "pending", "priority": 1, "user_id": u1.id, "category_id": c4.id,
         "due_date": agora - timedelta(days=1)},
        {"title": "Adicionar paginação na API", "description": "Endpoints retornam todos os registros",
         "status": "pending", "priority": 3, "user_id": u1.id, "category_id": c1.id,
         "due_date": agora + timedelta(days=10)},
        {"title": "Escrever testes unitários", "description": "Cobertura mínima de 80%",
         "status": "pending", "priority": 2, "user_id": u2.id, "category_id": c1.id},
        {"title": "Documentar API com Swagger", "description": "Gerar documentação automática",
         "status": "cancelled", "priority": 4, "user_id": u3.id, "category_id": c1.id},
        {"title": "Refatorar models", "description": "Melhorar organização dos models",
         "status": "in_progress", "priority": 3, "user_id": u2.id, "category_id": c1.id,
         "tags": "refactor,tech-debt"},
        {"title": "Configurar monitoramento", "description": "Prometheus + Grafana",
         "status": "pending", "priority": 4, "user_id": u3.id, "category_id": c3.id,
         "due_date": agora + timedelta(days=20)},
        {"title": "Melhorar validações de input", "description": "Usar marshmallow ou pydantic",
         "status": "pending", "priority": 3, "user_id": u1.id, "category_id": c1.id,
         "tags": "improvement,validation"},
    )


def seed_data(app) -> None:
    with app.app_context():
        Task.query.delete()
        User.query.delete()
        Category.query.delete()
        db.session.commit()

        usuarios = []
        for nome, email, senha, papel in USUARIOS:
            usuario = User(name=nome, email=email, role=papel)
            usuario.set_password(senha)
            db.session.add(usuario)
            usuarios.append(usuario)

        categorias = [Category(name=n, description=d, color=c) for n, d, c in CATEGORIAS]
        db.session.add_all(categorias)
        db.session.commit()

        for dados in _tasks(utc_now(), usuarios, categorias):
            db.session.add(Task(**dados))
        db.session.commit()

        print("Seed concluído com sucesso!")
        print(f"  {User.query.count()} usuários")
        print(f"  {Category.query.count()} categorias")
        print(f"  {Task.query.count()} tasks")


if __name__ == "__main__":
    aplicacao = create_app()
    init_schema(aplicacao)
    seed_data(aplicacao)
