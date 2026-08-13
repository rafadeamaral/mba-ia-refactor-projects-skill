"""Rotas de sistema: índice da API e health check."""
from flask import Blueprint, jsonify

INDICE = {
    "mensagem": "Bem-vindo à API da Loja",
    "versao": "1.0.0",
    "endpoints": {
        "produtos": "/produtos",
        "usuarios": "/usuarios",
        "pedidos": "/pedidos",
        "login": "/login",
        "relatorios": "/relatorios/vendas",
        "health": "/health",
    },
}


def criar_blueprint(health_controller) -> Blueprint:
    bp = Blueprint("sistema", __name__)

    @bp.route("/", methods=["GET"])
    def index():
        return jsonify(INDICE)

    @bp.route("/health", methods=["GET"])
    def health():
        return jsonify(health_controller.status()), 200

    return bp
