'use strict';

/**
 * Configuração da aplicação — lida do ambiente, sem valores sensíveis no código.
 *
 * A versão anterior mantinha `dbPass`, `paymentGatewayKey` (chave `pk_live_` de produção) e
 * `smtpUser` como literais em `src/utils.js`, versionados no repositório.
 */

const crypto = require('node:crypto');

const chaveAdministrativa = (process.env.ADMIN_API_KEY || '').trim();

const config = {
    env: process.env.NODE_ENV || 'development',
    port: Number(process.env.PORT || 3000),
    databasePath: process.env.DATABASE_PATH || './data/lms.db',
    logLevel: process.env.LOG_LEVEL || 'info',

    // Credencial das rotas administrativas. Não existe chave para desligar a verificação:
    // guarda desligável por configuração não protege nada (SEC-10). Na ausência da variável,
    // uma chave aleatória é gerada e registrada no boot — a rota continua fechada para quem
    // não leu o log, e continua utilizável em desenvolvimento.
    adminApiKey: chaveAdministrativa || crypto.randomBytes(24).toString('hex'),
    adminApiKeyEfemera: !chaveAdministrativa,

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
