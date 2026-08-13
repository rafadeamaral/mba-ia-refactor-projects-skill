'use strict';

const { hashPassword } = require('../models/password');
const logger = require('../utils/logger');

/**
 * Schema e carga inicial — explícitos, chamados uma vez no bootstrap.
 *
 * Diferenças em relação à versão anterior:
 * - chaves estrangeiras declaradas, com ON DELETE CASCADE onde a dependência é de posse
 *   (a versão anterior deixava matrículas e pagamentos órfãos ao deletar um usuário);
 * - NOT NULL e UNIQUE onde o domínio exige;
 * - seed idempotente: só popula quando o banco está vazio.
 */
const DDL = `
CREATE TABLE IF NOT EXISTS users (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    pass  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS courses (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    title  TEXT NOT NULL,
    price  REAL NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS enrollments (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS payments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL REFERENCES enrollments(id) ON DELETE CASCADE,
    amount        REAL NOT NULL,
    status        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    action     TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_user   ON enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_enrollment ON payments(enrollment_id);
`;

async function initSchema(db) {
    await db.exec(DDL);

    const { total } = await db.get('SELECT COUNT(*) AS total FROM users');
    if (total > 0) return;

    await db.transaction(async () => {
        const usuario = await db.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            ['Leonan', 'leonan@fullcycle.com.br', hashPassword('123')],
        );
        await db.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1)',
            ['Clean Architecture', 997.0]);
        await db.run('INSERT INTO courses (title, price, active) VALUES (?, ?, 1)',
            ['Docker', 497.0]);
        const matricula = await db.run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)', [usuario.lastID, 1]);
        await db.run('INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)',
            [matricula.lastID, 997.0, 'PAID']);
    });

    logger.info('carga_inicial_concluida', { usuarios: 1, cursos: 2 });
}

module.exports = { initSchema };
