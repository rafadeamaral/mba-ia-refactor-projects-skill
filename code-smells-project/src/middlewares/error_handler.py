"""Tratamento de erro centralizado — substitui os 16 try/except dos controllers."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from src.middlewares.exceptions import AppError

log = logging.getLogger(__name__)


def registrar_error_handlers(app) -> None:
    @app.errorhandler(AppError)
    def _erro_de_aplicacao(erro: AppError):
        log.info("erro_de_dominio status=%s msg=%s", erro.status, erro.mensagem)
        return jsonify({"erro": erro.mensagem, "sucesso": False}), erro.status

    @app.errorhandler(404)
    def _nao_encontrado(_erro):
        return jsonify({"erro": "Recurso não encontrado", "sucesso": False}), 404

    @app.errorhandler(405)
    def _metodo_nao_permitido(_erro):
        return jsonify({"erro": "Método não permitido", "sucesso": False}), 405

    @app.errorhandler(HTTPException)
    def _erro_http(erro: HTTPException):
        return jsonify({"erro": erro.description, "sucesso": False}), erro.code

    @app.errorhandler(Exception)
    def _erro_inesperado(erro: Exception):
        # A causa técnica vai para o log; o cliente recebe apenas uma mensagem genérica.
        log.exception("erro_nao_tratado: %s", erro)
        return jsonify({"erro": "Erro interno", "sucesso": False}), 500
