'use strict';

const { ValidationError } = require('../middlewares/errors');

const REGEX_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const REGEX_CARTAO = /^\d{13,19}$/;

/**
 * Valida o corpo do checkout.
 *
 * Os nomes abreviados do payload (`usr`, `eml`, `pwd`, `c_id`, `card`) são mantidos de propósito:
 * renomeá-los quebraria o `api.http` e qualquer cliente existente.
 *
 * A versão anterior só checava presença e, quando a senha vinha ausente, criava a conta com o
 * literal `"123456"` — uma credencial previsível que o dono da conta desconhece.
 */
function validarCheckout(body) {
    if (!body || typeof body !== 'object') throw new ValidationError('Bad Request');

    const { usr, eml, pwd, c_id: cId, card } = body;

    // Mensagem preservada da versão anterior para não quebrar clientes que a comparam.
    if (!usr || !eml || !cId || !card) throw new ValidationError('Bad Request');

    if (!REGEX_EMAIL.test(String(eml))) throw new ValidationError('E-mail inválido');

    const courseId = Number(cId);
    if (!Number.isInteger(courseId) || courseId <= 0) throw new ValidationError('Curso inválido');

    if (!REGEX_CARTAO.test(String(card))) throw new ValidationError('Número de cartão inválido');

    return {
        name: String(usr),
        email: String(eml),
        password: pwd == null ? null : String(pwd),
        courseId,
        card: String(card),
    };
}

module.exports = { validarCheckout };
