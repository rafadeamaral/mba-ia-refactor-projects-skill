"""Rotas de relatórios."""
from flask import Blueprint, jsonify

from middlewares.auth import PAPEL_ADMIN, PAPEL_MANAGER, requer_papel


def criar_blueprint(controller) -> Blueprint:
    bp = Blueprint("reports", __name__)

    @bp.route("/reports/summary", methods=["GET"])
    @requer_papel(PAPEL_ADMIN, PAPEL_MANAGER)
    def resumo():
        return jsonify(controller.resumo()), 200

    @bp.route("/reports/user/<int:usuario_id>", methods=["GET"])
    @requer_papel(PAPEL_ADMIN, PAPEL_MANAGER)
    def por_usuario(usuario_id):
        return jsonify(controller.por_usuario(usuario_id)), 200

    return bp
