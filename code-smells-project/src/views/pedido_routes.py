"""Rotas de pedidos.

Política de acesso (finding #6): criar pedido e consultar os pedidos de um usuário exigem
credencial; listar a base inteira de pedidos e mover status são operações administrativas.
"""
from flask import Blueprint, jsonify, request

from src.constants import TIPO_USUARIO_ADMIN
from src.middlewares.auth import requer_autenticacao, requer_papel

from src.validators import pedido_schema
from src.validators.common import parse_paginacao


def criar_blueprint(controller) -> Blueprint:
    bp = Blueprint("pedidos", __name__)

    @bp.route("/pedidos", methods=["POST"])
    @requer_autenticacao
    def criar():
        dados = pedido_schema.validar_criacao(request.get_json(silent=True))
        resultado = controller.criar(dados["usuario_id"], dados["itens"])
        return jsonify({
            "dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"
        }), 201

    @bp.route("/pedidos", methods=["GET"])
    @requer_papel(TIPO_USUARIO_ADMIN)
    def listar_todos():
        limite, offset = parse_paginacao(request.args)
        return jsonify({"dados": controller.listar(None, limite, offset), "sucesso": True}), 200

    @bp.route("/pedidos/usuario/<int:usuario_id>", methods=["GET"])
    @requer_autenticacao
    def listar_por_usuario(usuario_id):
        limite, offset = parse_paginacao(request.args)
        pedidos = controller.listar(usuario_id, limite, offset)
        return jsonify({"dados": pedidos, "sucesso": True}), 200

    @bp.route("/pedidos/<int:pedido_id>/status", methods=["PUT"])
    @requer_papel(TIPO_USUARIO_ADMIN)
    def atualizar_status(pedido_id):
        status = pedido_schema.validar_status(request.get_json(silent=True))
        controller.atualizar_status(pedido_id, status)
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200

    return bp
