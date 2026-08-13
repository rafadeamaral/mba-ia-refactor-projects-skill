'use strict';

const { Router } = require('express');

const { asyncHandler } = require('../middlewares/async-handler');
const { requerAutenticacao } = require('../middlewares/auth');

module.exports = (userController) => {
    const router = Router();

    router.delete('/users/:id', requerAutenticacao, asyncHandler(async (req, res) => {
        res.status(200).json(await userController.delete(Number(req.params.id)));
    }));

    return router;
};
