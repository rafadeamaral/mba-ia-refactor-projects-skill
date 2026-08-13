'use strict';

const logger = require('../utils/logger');

/**
 * Gateway de pagamento atrás de uma interface.
 *
 * A versão anterior decidia a aprovação com `cc.startsWith("4") ? "PAID" : "DENIED"` inline no
 * handler HTTP, e imprimia o número completo do cartão junto com a chave de produção no log.
 *
 * A regra continua sendo um stub — o que muda é que ela está isolada, nomeada de forma honesta e
 * substituível pela integração real sem tocar no controller.
 */
class FakePaymentGateway {
    constructor({ gatewayKey } = {}) {
        this.gatewayKey = gatewayKey;
    }

    /**
     * @returns {{status: 'PAID'|'DENIED', reference: string}}
     */
    charge({ card, amount }) {
        const numero = String(card ?? '');
        const status = numero.startsWith('4') ? 'PAID' : 'DENIED';

        // Log sem PAN e sem chave: apenas os últimos 4 dígitos e o valor.
        logger.info('pagamento_processado', {
            status, amount, cartao_final: numero.slice(-4), gateway: 'fake',
        });

        return { status, reference: `fake-${Date.now()}` };
    }
}

module.exports = { FakePaymentGateway };
