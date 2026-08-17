'use strict';

const { Router } = require('express');

const { asyncHandler } = require('../middlewares/async-handler');
const { requerChaveAdministrativa } = require('../middlewares/auth');

module.exports = (reportController) => {
    const router = Router();

    // Relatório financeiro consolidado: rota administrativa (finding #6).
    router.get('/admin/financial-report', requerChaveAdministrativa, asyncHandler(async (_req, res) => {
        res.status(200).json(await reportController.financial());
    }));

    return router;
};
