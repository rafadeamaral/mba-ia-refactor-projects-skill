"""Rotas de relatórios."""
from flask import Blueprint, jsonify


def criar_blueprint(controller) -> Blueprint:
    bp = Blueprint("relatorios", __name__)

    @bp.route("/relatorios/vendas", methods=["GET"])
    def vendas():
        return jsonify({"dados": controller.vendas(), "sucesso": True}), 200

    return bp
