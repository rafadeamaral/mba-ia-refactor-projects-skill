'use strict';

const { Router } = require('express');

const { asyncHandler } = require('../middlewares/async-handler');
const { requerChaveAdministrativa } = require('../middlewares/auth');

module.exports = (userController) => {
    const router = Router();

    // Deleção de usuário: rota destrutiva e irreversível (finding #6).
    router.delete('/users/:id', requerChaveAdministrativa, asyncHandler(async (req, res) => {
        res.status(200).json(await userController.delete(Number(req.params.id)));
    }));

    return router;
};
