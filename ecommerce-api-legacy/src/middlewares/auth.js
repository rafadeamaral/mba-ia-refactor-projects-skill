'use strict';

const config = require('../config');
const { UnauthorizedError, ForbiddenError } = require('./errors');

/**
 * Ponto de extensão para autenticação e autorização.
 *
 * A auditoria registrou (finding #6) que o relatório financeiro e a deleção de usuário eram
 * acessíveis anonimamente. Emitir e verificar credencial é funcionalidade nova, fora do escopo de
 * uma refatoração — o que existe aqui é o ponto de extensão pronto: basta implementar
 * `resolverUsuario` e ligar `AUTH_ENABLED=true`.
 *
 * Com `AUTH_ENABLED=false` os middlewares são transparentes e o comportamento dos endpoints
 * permanece idêntico ao original.
 */
function resolverUsuario(_authorization) {
    throw new Error('Autenticação não implementada — ver src/middlewares/auth.js');
}

function requerAutenticacao(req, _res, next) {
    if (!config.authEnabled) return next();

    const usuario = resolverUsuario(req.headers.authorization);
    if (!usuario) return next(new UnauthorizedError());

    req.usuario = usuario;
    return next();
}

function requerPapel(...papeis) {
    return (req, res, next) => requerAutenticacao(req, res, (erro) => {
        if (erro) return next(erro);
        if (!config.authEnabled) return next();
        if (!papeis.includes(req.usuario?.role)) return next(new ForbiddenError());
        return next();
    });
}

module.exports = { requerAutenticacao, requerPapel };
