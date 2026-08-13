"""Configuração de logging — substitui os print() das rotas."""
import logging


def configurar_logging(nivel: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, nivel, logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
