"""Rotas de relatórios."""
from flask import Blueprint, jsonify


def criar_blueprint(controller) -> Blueprint:
    bp = Blueprint("reports", __name__)

    @bp.route("/reports/summary", methods=["GET"])
    def resumo():
        return jsonify(controller.resumo()), 200

    @bp.route("/reports/user/<int:usuario_id>", methods=["GET"])
    def por_usuario(usuario_id):
        return jsonify(controller.por_usuario(usuario_id)), 200

    return bp
