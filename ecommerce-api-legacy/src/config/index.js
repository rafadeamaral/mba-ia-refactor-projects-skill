'use strict';

/**
 * Configuração da aplicação — lida do ambiente, sem valores sensíveis no código.
 *
 * A versão anterior mantinha `dbPass`, `paymentGatewayKey` (chave `pk_live_` de produção) e
 * `smtpUser` como literais em `src/utils.js`, versionados no repositório.
 */

const flag = (nome, padrao = 'false') =>
    ['1', 'true', 'yes', 'on'].includes(String(process.env[nome] ?? padrao).trim().toLowerCase());

const config = {
    env: process.env.NODE_ENV || 'development',
    port: Number(process.env.PORT || 3000),
    databasePath: process.env.DATABASE_PATH || './data/lms.db',
    logLevel: process.env.LOG_LEVEL || 'info',
    authEnabled: flag('AUTH_ENABLED'),

    payment: {
        // Sem valor default: uma chave de gateway ausente deve falhar de forma visível,
        // nunca cair silenciosamente em um literal do código.
        gatewayKey: process.env.PAYMENT_GATEWAY_KEY || null,
    },

    smtp: {
        user: process.env.SMTP_USER || null,
        host: process.env.SMTP_HOST || null,
    },
};

module.exports = config;
