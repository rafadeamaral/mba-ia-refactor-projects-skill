'use strict';

const { AppError, NotFoundError } = require('./errors');
const logger = require('../utils/logger');

/** Rota não encontrada — antes devolvia o HTML de erro padrão do Express. */
function notFoundHandler(req, _res, next) {
    next(new NotFoundError(`Rota não encontrada: ${req.method} ${req.path}`));
}

/**
 * Tratamento de erro centralizado.
 * O cliente recebe a mensagem de domínio; a causa técnica fica apenas no log.
 */
// eslint-disable-next-line no-unused-vars -- o Express exige a assinatura de 4 argumentos
function errorHandler(err, req, res, _next) {
    if (err instanceof AppError) {
        logger.info('erro_de_dominio', { status: err.status, msg: err.message, path: req.path });
        return res.status(err.status).json({ error: err.message });
    }

    logger.error('erro_nao_tratado', { msg: err.message, stack: err.stack, path: req.path });
    return res.status(500).json({ error: 'Erro interno' });
}

module.exports = { notFoundHandler, errorHandler };
