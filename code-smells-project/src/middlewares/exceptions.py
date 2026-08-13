"""Exceções de domínio — substituem o retorno de erro como valor."""


class AppError(Exception):
    """Erro de aplicação traduzível para uma resposta HTTP."""

    status = 500

    def __init__(self, mensagem: str, status: int | None = None) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem
        if status is not None:
            self.status = status


class ValidationError(AppError):
    status = 400


class UnauthorizedError(AppError):
    status = 401


class ForbiddenError(AppError):
    status = 403


class NotFoundError(AppError):
    status = 404


class BusinessRuleError(AppError):
    """Regra de negócio violada (ex.: estoque insuficiente)."""

    status = 400
