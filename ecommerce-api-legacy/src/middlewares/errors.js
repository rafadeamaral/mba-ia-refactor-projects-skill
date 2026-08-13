'use strict';

/** Erros de domínio — traduzidos para status HTTP pelo error handler central. */

class AppError extends Error {
    constructor(message, status = 500) {
        super(message);
        this.name = this.constructor.name;
        this.status = status;
    }
}

class ValidationError extends AppError {
    constructor(message = 'Bad Request') { super(message, 400); }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Autenticação obrigatória') { super(message, 401); }
}

class ForbiddenError extends AppError {
    constructor(message = 'Permissão insuficiente') { super(message, 403); }
}

class NotFoundError extends AppError {
    constructor(message = 'Recurso não encontrado') { super(message, 404); }
}

class BusinessRuleError extends AppError {
    constructor(message, status = 400) { super(message, status); }
}

module.exports = {
    AppError, ValidationError, UnauthorizedError, ForbiddenError, NotFoundError, BusinessRuleError,
};
