"""Rotas de tasks — handlers finos: HTTP entra, controller decide, DTO sai."""
from flask import Blueprint, jsonify, request

from middlewares.auth import requer_autenticacao

from routes.dto.task_dto import task_para_resposta
from validators import task_schema
from validators.common import inteiro_opcional, parse_paginacao


def criar_blueprint(controller) -> Blueprint:
    bp = Blueprint("tasks", __name__)

    @bp.route("/tasks", methods=["GET"])
    @requer_autenticacao
    def listar():
        limite, offset = parse_paginacao(request.args)
        tasks = controller.listar(limite, offset)
        return jsonify([
            task_para_resposta(t, incluir_overdue=True, incluir_relacionados=True) for t in tasks
        ]), 200

    @bp.route("/tasks/search", methods=["GET"])
    @requer_autenticacao
    def buscar():
        limite, offset = parse_paginacao(request.args)
        tasks = controller.buscar(
            termo=request.args.get("q", ""),
            status=request.args.get("status", ""),
            prioridade=inteiro_opcional(request.args.get("priority"), "priority"),
            usuario_id=inteiro_opcional(request.args.get("user_id"), "user_id"),
            limite=limite,
            offset=offset,
        )
        return jsonify([task_para_resposta(t) for t in tasks]), 200

    @bp.route("/tasks/stats", methods=["GET"])
    @requer_autenticacao
    def estatisticas():
        return jsonify(controller.estatisticas()), 200

    @bp.route("/tasks/<int:task_id>", methods=["GET"])
    @requer_autenticacao
    def buscar_por_id(task_id):
        task = controller.buscar_por_id(task_id)
        return jsonify(task_para_resposta(task, incluir_overdue=True)), 200

    @bp.route("/tasks", methods=["POST"])
    @requer_autenticacao
    def criar():
        dados = task_schema.validar_criacao(request.get_json(silent=True))
        task = controller.criar(dados)
        return jsonify(task_para_resposta(task)), 201

    @bp.route("/tasks/<int:task_id>", methods=["PUT"])
    @requer_autenticacao
    def atualizar(task_id):
        dados = task_schema.validar_atualizacao(request.get_json(silent=True))
        task = controller.atualizar(task_id, dados)
        return jsonify(task_para_resposta(task)), 200

    @bp.route("/tasks/<int:task_id>", methods=["DELETE"])
    @requer_autenticacao
    def deletar(task_id):
        controller.deletar(task_id)
        return jsonify({"message": "Task deletada com sucesso"}), 200

    return bp
