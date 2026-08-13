"""Rotas de pedidos."""
from flask import Blueprint, jsonify, request

from src.validators import pedido_schema
from src.validators.common import parse_paginacao


def criar_blueprint(controller) -> Blueprint:
    bp = Blueprint("pedidos", __name__)

    @bp.route("/pedidos", methods=["POST"])
    def criar():
        dados = pedido_schema.validar_criacao(request.get_json(silent=True))
        resultado = controller.criar(dados["usuario_id"], dados["itens"])
        return jsonify({
            "dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"
        }), 201

    @bp.route("/pedidos", methods=["GET"])
    def listar_todos():
        limite, offset = parse_paginacao(request.args)
        return jsonify({"dados": controller.listar(None, limite, offset), "sucesso": True}), 200

    @bp.route("/pedidos/usuario/<int:usuario_id>", methods=["GET"])
    def listar_por_usuario(usuario_id):
        limite, offset = parse_paginacao(request.args)
        pedidos = controller.listar(usuario_id, limite, offset)
        return jsonify({"dados": pedidos, "sucesso": True}), 200

    @bp.route("/pedidos/<int:pedido_id>/status", methods=["PUT"])
    def atualizar_status(pedido_id):
        status = pedido_schema.validar_status(request.get_json(silent=True))
        controller.atualizar_status(pedido_id, status)
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200

    return bp
