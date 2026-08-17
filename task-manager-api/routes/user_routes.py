"""Rotas de usuários e login.

Política de acesso, decidida a partir da auditoria (finding #3):
`POST /users` é o cadastro e continua público; `POST /login` é a porta de entrada da credencial;
ler ou alterar um usuário exige credencial; listar a base inteira e deletar usuário são operações
administrativas.
"""
from flask import Blueprint, jsonify, request

from middlewares.auth import PAPEL_ADMIN, requer_autenticacao, requer_papel

from routes.dto.task_dto import task_para_resposta, task_resumida_para_resposta
from routes.dto.user_dto import usuario_com_contagem, usuario_para_resposta
from validators import user_schema
from validators.common import parse_paginacao


def criar_blueprint(user_controller, task_controller) -> Blueprint:
    bp = Blueprint("users", __name__)

    @bp.route("/users", methods=["GET"])
    @requer_papel(PAPEL_ADMIN)
    def listar():
        limite, offset = parse_paginacao(request.args)
        return jsonify([
            usuario_com_contagem(usuario, total)
            for usuario, total in user_controller.listar(limite, offset)
        ]), 200

    @bp.route("/users/<int:usuario_id>", methods=["GET"])
    @requer_autenticacao
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
    @requer_autenticacao
    def atualizar(usuario_id):
        dados = user_schema.validar_atualizacao(request.get_json(silent=True))
        usuario = user_controller.atualizar(usuario_id, dados)
        return jsonify(usuario_para_resposta(usuario)), 200

    @bp.route("/users/<int:usuario_id>", methods=["DELETE"])
    @requer_papel(PAPEL_ADMIN)
    def deletar(usuario_id):
        user_controller.deletar(usuario_id)
        return jsonify({"message": "Usuário deletado com sucesso"}), 200

    @bp.route("/users/<int:usuario_id>/tasks", methods=["GET"])
    @requer_autenticacao
    def tasks_do_usuario(usuario_id):
        user_controller.buscar_por_id(usuario_id)  # 404 se não existir
        tasks = task_controller.listar_por_usuario(usuario_id)
        return jsonify([task_resumida_para_resposta(t) for t in tasks]), 200

    @bp.route("/login", methods=["POST"])
    def login():
        credenciais = user_schema.validar_login(request.get_json(silent=True))
        sessao = user_controller.autenticar(credenciais["email"], credenciais["password"])
        # O `token` da versão original era 'fake-jwt-token-<id>' e nenhuma rota o verificava.
        # Este é assinado com HMAC sobre a SECRET_KEY, expira, e é exigido pelas rotas protegidas.
        return jsonify({
            "message": "Login realizado com sucesso",
            "token": sessao["token"],
            "user": usuario_para_resposta(sessao["usuario"]),
        }), 200

    return bp
