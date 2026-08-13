"""Tratamento de erro centralizado — substitui os 12 blocos try/except das rotas."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from database import db
from middlewares.exceptions import AppError

log = logging.getLogger(__name__)


def registrar_error_handlers(app) -> None:
    @app.errorhandler(AppError)
    def _erro_de_dominio(erro: AppError):
        log.info("erro_de_dominio status=%s msg=%s", erro.status, erro.mensagem)
        return jsonify({"error": erro.mensagem}), erro.status

    @app.errorhandler(404)
    def _nao_encontrado(_erro):
        return jsonify({"error": "Recurso não encontrado"}), 404

    @app.errorhandler(405)
    def _metodo_nao_permitido(_erro):
        return jsonify({"error": "Método não permitido"}), 405

    @app.errorhandler(HTTPException)
    def _erro_http(erro: HTTPException):
        return jsonify({"error": erro.description}), erro.code

    @app.errorhandler(Exception)
    def _erro_inesperado(erro: Exception):
        # A sessão pode ter ficado suja: desfaz antes de responder.
        db.session.rollback()
        log.exception("erro_nao_tratado: %s", erro)
        return jsonify({"error": "Erro interno"}), 500
