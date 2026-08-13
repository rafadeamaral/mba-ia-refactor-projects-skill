'use strict';

const config = require('../config');

const NIVEIS = { error: 0, warn: 1, info: 2, debug: 3 };

/**
 * Logger estruturado — substitui os console.log espalhados.
 *
 * Nunca receba dado de cartão, senha, token ou chave de gateway aqui: a versão anterior
 * imprimia o número completo do cartão junto com a chave de produção do gateway.
 */
function escrever(nivel, mensagem, contexto = {}) {
    if (NIVEIS[nivel] > (NIVEIS[config.logLevel] ?? NIVEIS.info)) return;
    const linha = { ts: new Date().toISOString(), level: nivel, msg: mensagem, ...contexto };
    const destino = nivel === 'error' ? console.error : console.log;
    destino(JSON.stringify(linha));
}

module.exports = {
    error: (msg, ctx) => escrever('error', msg, ctx),
    warn: (msg, ctx) => escrever('warn', msg, ctx),
    info: (msg, ctx) => escrever('info', msg, ctx),
    debug: (msg, ctx) => escrever('debug', msg, ctx),
};
