'use strict';

const fs = require('node:fs');
const path = require('node:path');
const sqlite3 = require('sqlite3');

/**
 * Driver promisificado.
 *
 * A API de callbacks do sqlite3 é a causa raiz do callback hell, da ausência de transação e dos
 * erros ignorados na versão anterior. Envolvendo-a uma única vez aqui, o resto do código escreve
 * `await` e o erro propaga sozinho para o error handler.
 */
class Database {
    constructor(sqliteDb) {
        this._db = sqliteDb;
    }

    get(sql, params = []) {
        return new Promise((resolve, reject) =>
            this._db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row))));
    }

    all(sql, params = []) {
        return new Promise((resolve, reject) =>
            this._db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows))));
    }

    run(sql, params = []) {
        return new Promise((resolve, reject) =>
            // `function` (não arrow) porque o sqlite3 expõe lastID/changes via `this`.
            this._db.run(sql, params, function (err) {
                if (err) return reject(err);
                resolve({ lastID: this.lastID, changes: this.changes });
            }));
    }

    exec(sql) {
        return new Promise((resolve, reject) =>
            this._db.exec(sql, (err) => (err ? reject(err) : resolve())));
    }

    /** Executa `fn` dentro de uma transação: commit no sucesso, rollback em qualquer exceção. */
    async transaction(fn) {
        await this.run('BEGIN');
        try {
            const resultado = await fn();
            await this.run('COMMIT');
            return resultado;
        } catch (erro) {
            await this.run('ROLLBACK');
            throw erro;
        }
    }

    close() {
        return new Promise((resolve, reject) =>
            this._db.close((err) => (err ? reject(err) : resolve())));
    }
}

async function createDatabase(databasePath) {
    if (databasePath !== ':memory:') {
        fs.mkdirSync(path.dirname(path.resolve(databasePath)), { recursive: true });
    }

    const sqliteDb = await new Promise((resolve, reject) => {
        const instancia = new sqlite3.Database(databasePath, (err) =>
            (err ? reject(err) : resolve(instancia)));
    });

    const db = new Database(sqliteDb);
    await db.run('PRAGMA foreign_keys = ON');
    return db;
}

module.exports = { Database, createDatabase };
