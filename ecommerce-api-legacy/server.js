'use strict';

const config = require('./src/config');
const { createApp } = require('./src/app');
const { createDatabase } = require('./src/database/connection');
const { initSchema } = require('./src/database/schema');
const logger = require('./src/utils/logger');

/** Bootstrap: abre o banco, inicializa o schema e sobe o servidor. */
async function main() {
    const db = await createDatabase(config.databasePath);
    await initSchema(db);

    if (config.adminApiKeyEfemera) {
        logger.warn('admin_api_key_ausente', {
            msg: 'ADMIN_API_KEY não definida; chave efêmera gerada para esta execução',
            chave: config.adminApiKey,
        });
    }

    const app = createApp({ db });
    const server = app.listen(config.port, () => {
        logger.info('servidor_iniciado', { port: config.port, env: config.env });
    });

    const encerrar = async (sinal) => {
        logger.info('encerrando', { sinal });
        server.close(async () => {
            await db.close();
            process.exit(0);
        });
    };
    process.on('SIGTERM', () => encerrar('SIGTERM'));
    process.on('SIGINT', () => encerrar('SIGINT'));
}

main().catch((erro) => {
    logger.error('falha_no_bootstrap', { msg: erro.message, stack: erro.stack });
    process.exit(1);
});
