'use strict';

const crypto = require('node:crypto');

/**
 * Hash de senha com scrypt — substitui a função caseira `badCrypto`.
 *
 * `badCrypto` concatenava 10.000 vezes os dois primeiros caracteres do base64 da senha e
 * truncava em 10 caracteres: base64 é encoding (reversível), o espaço de saída era minúsculo e
 * não havia salt.
 *
 * scrypt é uma KDF memory-hard da biblioteca padrão do Node — resolve o CRITICAL sem introduzir
 * dependência nativa nova (bcrypt/argon2 exigem compilação). Formato armazenado: `scrypt$salt$hash`.
 */
const TAMANHO_SALT = 16;
const TAMANHO_HASH = 64;
const PREFIXO = 'scrypt';

function hashPassword(senha) {
    const salt = crypto.randomBytes(TAMANHO_SALT).toString('hex');
    const hash = crypto.scryptSync(senha, salt, TAMANHO_HASH).toString('hex');
    return `${PREFIXO}$${salt}$${hash}`;
}

function verifyPassword(senha, armazenado) {
    if (typeof armazenado !== 'string' || !armazenado.startsWith(`${PREFIXO}$`)) return false;

    const [, salt, hashEsperado] = armazenado.split('$');
    const hash = crypto.scryptSync(senha, salt, TAMANHO_HASH);
    const esperado = Buffer.from(hashEsperado, 'hex');

    // Comparação em tempo constante: evita distinguir senhas por tempo de resposta.
    return hash.length === esperado.length && crypto.timingSafeEqual(hash, esperado);
}

module.exports = { hashPassword, verifyPassword };
