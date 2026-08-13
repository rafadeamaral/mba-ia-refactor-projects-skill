"""Rotas de categorias.

Extraídas de `report_routes.py`, onde o CRUD de categoria convivia com os relatórios sem
qualquer relação de domínio. Os paths não mudaram.
"""
from flask import Blueprint, jsonify, request

from routes.dto.category_dto import categoria_com_contagem, categoria_para_resposta
from validators import category_schema


def criar_blueprint(controller) -> Blueprint:
    bp = Blueprint("categories", __name__)

    @bp.route("/categories", methods=["GET"])
    def listar():
        return jsonify([
            categoria_com_contagem(categoria, total) for categoria, total in controller.listar()
        ]), 200

    @bp.route("/categories", methods=["POST"])
    def criar():
        dados = category_schema.validar_criacao(request.get_json(silent=True))
        categoria = controller.criar(dados)
        return jsonify(categoria_para_resposta(categoria)), 201

    @bp.route("/categories/<int:categoria_id>", methods=["PUT"])
    def atualizar(categoria_id):
        dados = category_schema.validar_atualizacao(request.get_json(silent=True))
        categoria = controller.atualizar(categoria_id, dados)
        return jsonify(categoria_para_resposta(categoria)), 200

    @bp.route("/categories/<int:categoria_id>", methods=["DELETE"])
    def deletar(categoria_id):
        controller.deletar(categoria_id)
        return jsonify({"message": "Categoria deletada"}), 200

    return bp
