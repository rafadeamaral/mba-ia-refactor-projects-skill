"""Rotas de usuários e login."""
from flask import Blueprint, jsonify, request

from src.validators import usuario_schema
from src.validators.common import parse_paginacao
from src.views.dto.usuario_dto import (
    usuario_autenticado_para_resposta,
    usuario_para_resposta,
    usuarios_para_resposta,
)


def criar_blueprint(controller) -> Blueprint:
    bp = Blueprint("usuarios", __name__)

    @bp.route("/usuarios", methods=["GET"])
    def listar():
        limite, offset = parse_paginacao(request.args)
        usuarios = controller.listar(limite, offset)
        return jsonify({"dados": usuarios_para_resposta(usuarios), "sucesso": True}), 200

    @bp.route("/usuarios/<int:usuario_id>", methods=["GET"])
    def buscar_por_id(usuario_id):
        usuario = controller.buscar_por_id(usuario_id)
        return jsonify({"dados": usuario_para_resposta(usuario), "sucesso": True}), 200

    @bp.route("/usuarios", methods=["POST"])
    def criar():
        dados = usuario_schema.validar_criacao(request.get_json(silent=True))
        usuario_id = controller.criar(dados)
        return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201

    @bp.route("/login", methods=["POST"])
    def login():
        credenciais = usuario_schema.validar_login(request.get_json(silent=True))
        usuario = controller.autenticar(credenciais["email"], credenciais["senha"])
        return jsonify({
            "dados": usuario_autenticado_para_resposta(usuario),
            "sucesso": True,
            "mensagem": "Login OK",
        }), 200

    return bp
