"""Rotas de produtos — handlers finos: HTTP entra, controller decide, DTO sai.

Política de acesso (finding #6): o catálogo é leitura pública por natureza do produto; a
escrita — criar, atualizar e deletar produto — passou a exigir credencial de admin.
"""
from flask import Blueprint, jsonify, request

from src.constants import TIPO_USUARIO_ADMIN
from src.middlewares.auth import requer_papel

from src.validators import produto_schema
from src.validators.common import numero_opcional, parse_paginacao
from src.views.dto.produto_dto import produto_para_resposta, produtos_para_resposta


def criar_blueprint(controller) -> Blueprint:
    bp = Blueprint("produtos", __name__)

    @bp.route("/produtos", methods=["GET"])
    def listar():
        limite, offset = parse_paginacao(request.args)
        produtos = controller.listar(limite, offset)
        return jsonify({"dados": produtos_para_resposta(produtos), "sucesso": True}), 200

    @bp.route("/produtos/busca", methods=["GET"])
    def buscar():
        limite, offset = parse_paginacao(request.args)
        resultados = controller.buscar(
            termo=request.args.get("q", ""),
            categoria=request.args.get("categoria"),
            preco_min=numero_opcional(request.args.get("preco_min"), "preco_min"),
            preco_max=numero_opcional(request.args.get("preco_max"), "preco_max"),
            limite=limite,
            offset=offset,
        )
        return jsonify({
            "dados": produtos_para_resposta(resultados),
            "total": len(resultados),
            "sucesso": True,
        }), 200

    @bp.route("/produtos/<int:produto_id>", methods=["GET"])
    def buscar_por_id(produto_id):
        produto = controller.buscar_por_id(produto_id)
        return jsonify({"dados": produto_para_resposta(produto), "sucesso": True}), 200

    @bp.route("/produtos", methods=["POST"])
    @requer_papel(TIPO_USUARIO_ADMIN)
    def criar():
        dados = produto_schema.validar(request.get_json(silent=True))
        produto_id = controller.criar(dados)
        return jsonify({
            "dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"
        }), 201

    @bp.route("/produtos/<int:produto_id>", methods=["PUT"])
    @requer_papel(TIPO_USUARIO_ADMIN)
    def atualizar(produto_id):
        dados = produto_schema.validar(request.get_json(silent=True))
        controller.atualizar(produto_id, dados)
        return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200

    @bp.route("/produtos/<int:produto_id>", methods=["DELETE"])
    @requer_papel(TIPO_USUARIO_ADMIN)
    def deletar(produto_id):
        controller.deletar(produto_id)
        return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200

    return bp
