'use strict';

const { Router } = require('express');

const { asyncHandler } = require('../middlewares/async-handler');
const { requerAutenticacao } = require('../middlewares/auth');

module.exports = (reportController) => {
    const router = Router();

    router.get('/admin/financial-report', requerAutenticacao, asyncHandler(async (_req, res) => {
        res.status(200).json(await reportController.financial());
    }));

    return router;
};
