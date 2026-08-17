"""Rotas de relatórios.

Relatório de vendas expõe faturamento consolidado: rota administrativa (finding #6).
"""
from flask import Blueprint, jsonify

from src.constants import TIPO_USUARIO_ADMIN
from src.middlewares.auth import requer_papel


def criar_blueprint(controller) -> Blueprint:
    bp = Blueprint("relatorios", __name__)

    @bp.route("/relatorios/vendas", methods=["GET"])
    @requer_papel(TIPO_USUARIO_ADMIN)
    def vendas():
        return jsonify({"dados": controller.vendas(), "sucesso": True}), 200

    return bp
