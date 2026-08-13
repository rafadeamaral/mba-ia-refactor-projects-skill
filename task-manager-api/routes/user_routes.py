"""Rotas de usuários e login."""
from flask import Blueprint, jsonify, request

from routes.dto.task_dto import task_para_resposta, task_resumida_para_resposta
from routes.dto.user_dto import usuario_com_contagem, usuario_para_resposta
from validators import user_schema
from validators.common import parse_paginacao


def criar_blueprint(user_controller, task_controller) -> Blueprint:
    bp = Blueprint("users", __name__)

    @bp.route("/users", methods=["GET"])
    def listar():
        limite, offset = parse_paginacao(request.args)
        return jsonify([
            usuario_com_contagem(usuario, total)
            for usuario, total in user_controller.listar(limite, offset)
        ]), 200

    @bp.route("/users/<int:usuario_id>", methods=["GET"])
    def buscar_por_id(usuario_id):
        usuario = user_controller.buscar_por_id(usuario_id)
        tasks = task_controller.listar_por_usuario(usuario_id)
        return jsonify({
            **usuario_para_resposta(usuario),
            "tasks": [task_para_resposta(t) for t in tasks],
        }), 200

    @bp.route("/users", methods=["POST"])
    def criar():
        dados = user_schema.validar_criacao(request.get_json(silent=True))
        usuario = user_controller.criar(dados)
        return jsonify(usuario_para_resposta(usuario)), 201

    @bp.route("/users/<int:usuario_id>", methods=["PUT"])
    def atualizar(usuario_id):
        dados = user_schema.validar_atualizacao(request.get_json(silent=True))
        usuario = user_controller.atualizar(usuario_id, dados)
        return jsonify(usuario_para_resposta(usuario)), 200

    @bp.route("/users/<int:usuario_id>", methods=["DELETE"])
    def deletar(usuario_id):
        user_controller.deletar(usuario_id)
        return jsonify({"message": "Usuário deletado com sucesso"}), 200

    @bp.route("/users/<int:usuario_id>/tasks", methods=["GET"])
    def tasks_do_usuario(usuario_id):
        user_controller.buscar_por_id(usuario_id)  # 404 se não existir
        tasks = task_controller.listar_por_usuario(usuario_id)
        return jsonify([task_resumida_para_resposta(t) for t in tasks]), 200

    @bp.route("/login", methods=["POST"])
    def login():
        credenciais = user_schema.validar_login(request.get_json(silent=True))
        usuario = user_controller.autenticar(credenciais["email"], credenciais["password"])
        # O campo `token` foi removido: a versão anterior devolvia 'fake-jwt-token-<id>', que
        # nenhuma rota verificava. Devolver credencial falsa é pior que não devolver nenhuma.
        return jsonify({
            "message": "Login realizado com sucesso",
            "user": usuario_para_resposta(usuario),
        }), 200

    return bp
