'use strict';

const { Router } = require('express');

const { asyncHandler } = require('../middlewares/async-handler');
const { validarCheckout } = require('../validators/checkout.validator');

module.exports = (checkoutController) => {
    const router = Router();

    router.post('/checkout', asyncHandler(async (req, res) => {
        const dados = validarCheckout(req.body);
        const resultado = await checkoutController.execute(dados);
        res.status(200).json(resultado);
    }));

    return router;
};
