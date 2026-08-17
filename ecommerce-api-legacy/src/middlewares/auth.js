'use strict';

const crypto = require('node:crypto');

const config = require('../config');
const { UnauthorizedError } = require('./errors');

/**
 * Autorização administrativa — ativa por padrão.
 *
 * A auditoria registrou (finding #6) que `GET /api/admin/financial-report` e
 * `DELETE /api/users/:id` respondiam a qualquer cliente anônimo.
 *
 * A primeira tentativa de correção colocou este middleware atrás de `AUTH_ENABLED`, com default
 * `false`. Na prática as duas rotas continuaram abertas em toda execução real, e o relatório
 * passou a informar o contrário — o anti-pattern SEC-10 do catálogo. A flag foi removida: não
 * existe configuração que faça estas rotas voltarem a responder sem credencial.
 *
 * Diferente dos outros dois projetos do repositório, este não tem login, sessão nem tabela de
 * papéis exposta por HTTP — inventar um sistema de usuários seria funcionalidade nova. O que
 * cabe aqui é uma chave administrativa vinda do ambiente, comparada em tempo constante.
 *
 * Fora de escopo, declarado no relatório: identidade por usuário, expiração e rotação de chave.
 */

function comparaSegura(recebido, esperado) {
    const a = Buffer.from(recebido);
    const b = Buffer.from(esperado);
    // timingSafeEqual exige buffers do mesmo tamanho; comparar o tamanho antes não vaza o segredo.
    return a.length === b.length && crypto.timingSafeEqual(a, b);
}

/**
 * Exige `Authorization: Bearer <ADMIN_API_KEY>`.
 *
 * Sem chave configurada a rota fica **fechada**, nunca liberada: `config.adminApiKey` sempre tem
 * valor porque, na ausência da variável, o boot gera uma chave aleatória e a registra no log —
 * o operador continua conseguindo usar a rota em desenvolvimento sem que ela fique anônima.
 */
function requerChaveAdministrativa(req, _res, next) {
    const cabecalho = req.headers.authorization || '';

    if (!cabecalho.startsWith('Bearer ')
        || !comparaSegura(cabecalho.slice('Bearer '.length), config.adminApiKey)) {
        return next(new UnauthorizedError('Credencial administrativa inválida'));
    }

    return next();
}

module.exports = { requerChaveAdministrativa };
