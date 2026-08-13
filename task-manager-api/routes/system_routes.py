"""Rotas de sistema: índice da API e health check."""
from flask import Blueprint, jsonify

from utils.datetime_utils import utc_now

INDICE = {"message": "Task Manager API", "version": "1.0"}


def criar_blueprint() -> Blueprint:
    bp = Blueprint("system", __name__)

    @bp.route("/", methods=["GET"])
    def index():
        return jsonify(INDICE), 200

    @bp.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "timestamp": str(utc_now())}), 200

    return bp
