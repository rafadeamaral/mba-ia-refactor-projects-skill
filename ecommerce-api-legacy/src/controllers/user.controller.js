'use strict';

const { NotFoundError } = require('../middlewares/errors');
const logger = require('../utils/logger');

class UserController {
    constructor({ userModel }) {
        this.users = userModel;
    }

    async delete(id) {
        const usuario = await this.users.findById(id);
        if (!usuario) throw new NotFoundError('Usuário não encontrado');

        // As matrículas e pagamentos saem junto, por ON DELETE CASCADE.
        await this.users.delete(id);
        logger.info('usuario_deletado', { user_id: id });

        return { message: 'Usuário deletado' };
    }
}

module.exports = { UserController };
