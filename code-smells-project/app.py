"""Composition root — monta a aplicação e liga as camadas. Sem SQL, rota ou regra de negócio."""
from flask import Flask
from flask_cors import CORS

from src.config.logging_config import configurar_logging
from src.config.settings import settings
from src.controllers.health_controller import HealthController
from src.controllers.pedido_controller import PedidoController
from src.controllers.produto_controller import ProdutoController
from src.controllers.relatorio_controller import RelatorioController
from src.controllers.usuario_controller import UsuarioController
from src.database.connection import close_connection, get_connection
from src.database.schema import init_schema
from src.middlewares.auth import emitir_token
from src.middlewares.error_handler import registrar_error_handlers
from src.models.pedido_model import PedidoModel
from src.models.produto_model import ProdutoModel
from src.models.usuario_model import UsuarioModel
from src.services.notificacao_service import NotificacaoService
from src.views import (
    pedido_routes,
    produto_routes,
    relatorio_routes,
    sistema_routes,
    usuario_routes,
)


def create_app(connection_provider=get_connection) -> Flask:
    """Cria a aplicação com as dependências ligadas.

    `connection_provider` é injetável para permitir substituir o banco em testes sem tocar
    em nenhum módulo de produção.
    """
    configurar_logging(settings.LOG_LEVEL)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG
    CORS(app, origins=settings.CORS_ORIGINS)
    app.teardown_appcontext(close_connection)

    init_schema(settings.DATABASE_PATH)

    # Camada de dados
    produto_model = ProdutoModel(connection_provider)
    usuario_model = UsuarioModel(connection_provider)
    pedido_model = PedidoModel(connection_provider)

    # Serviços
    notificacao_service = NotificacaoService()

    # Camada de negócio
    produto_controller = ProdutoController(produto_model)
    usuario_controller = UsuarioController(usuario_model, emitir_token)
    pedido_controller = PedidoController(pedido_model, produto_model, notificacao_service)
    relatorio_controller = RelatorioController(pedido_model)
    health_controller = HealthController(produto_model, usuario_model, pedido_model)

    # Camada de roteamento
    app.register_blueprint(produto_routes.criar_blueprint(produto_controller))
    app.register_blueprint(usuario_routes.criar_blueprint(usuario_controller))
    app.register_blueprint(pedido_routes.criar_blueprint(pedido_controller))
    app.register_blueprint(relatorio_routes.criar_blueprint(relatorio_controller))
    app.register_blueprint(sistema_routes.criar_blueprint(health_controller))

    registrar_error_handlers(app)
    return app


if __name__ == "__main__":
    create_app().run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
