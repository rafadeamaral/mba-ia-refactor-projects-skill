"""Composition root — monta a aplicação e liga as camadas.

A versão anterior configurava a app no nível do módulo e executava `db.create_all()` **no
import**: bastava um `import app` para o arquivo `instance/tasks.db` ser criado. Aqui a criação
do schema é um passo explícito (`scripts/init_db.py` ou `init_schema(app)`), e a aplicação é
construída por uma factory, o que permite instanciá-la com configuração de teste.
"""
from flask import Flask
from flask_cors import CORS

from config.logging_config import configurar_logging
from config.settings import settings
from controllers.category_controller import CategoryController
from controllers.report_controller import ReportController
from controllers.task_controller import TaskController
from controllers.user_controller import UserController
from database import db
from middlewares.error_handler import registrar_error_handlers
from routes import (
    category_routes,
    report_routes,
    system_routes,
    task_routes,
    user_routes,
)
from services.notification_service import NotificationService


def create_app(config=None) -> Flask:
    configurar_logging(settings.LOG_LEVEL)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.SQLALCHEMY_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = settings.SQLALCHEMY_TRACK_MODIFICATIONS
    if config:
        app.config.update(config)

    CORS(app, origins=settings.CORS_ORIGINS)
    db.init_app(app)

    # Serviços
    notificacao_service = NotificationService()

    # Camada de negócio
    task_controller = TaskController(notificacao_service=notificacao_service)
    user_controller = UserController()
    category_controller = CategoryController()
    report_controller = ReportController()

    # Camada de roteamento
    app.register_blueprint(task_routes.criar_blueprint(task_controller))
    app.register_blueprint(user_routes.criar_blueprint(user_controller, task_controller))
    app.register_blueprint(category_routes.criar_blueprint(category_controller))
    app.register_blueprint(report_routes.criar_blueprint(report_controller))
    app.register_blueprint(system_routes.criar_blueprint())

    registrar_error_handlers(app)
    return app


def init_schema(app: Flask) -> None:
    """Cria as tabelas. Passo explícito — nunca efeito colateral de import."""
    # Os models precisam estar importados para que o metadata os conheça.
    from models import category, task, user  # noqa: F401

    with app.app_context():
        db.create_all()


if __name__ == "__main__":
    aplicacao = create_app()
    init_schema(aplicacao)
    aplicacao.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
