'use strict';

const { hashPassword, verifyPassword } = require('./password');

class UserModel {
    constructor(db) {
        this.db = db; // injetado — a versão anterior instanciava a conexão no construtor
    }

    findByEmail(email) {
        return this.db.get('SELECT id, name, email, pass FROM users WHERE email = ?', [email]);
    }

    findById(id) {
        return this.db.get('SELECT id, name, email FROM users WHERE id = ?', [id]);
    }

    async create({ name, email, password }) {
        const { lastID } = await this.db.run(
            'INSERT INTO users (name, email, pass) VALUES (?, ?, ?)',
            [name, email, hashPassword(password)],
        );
        return { id: lastID, name, email };
    }

    /**
     * Remove o usuário. As matrículas e pagamentos vinculados saem por ON DELETE CASCADE —
     * a versão anterior deixava esses registros órfãos, corrompendo o relatório financeiro.
     */
    async delete(id) {
        const { changes } = await this.db.run('DELETE FROM users WHERE id = ?', [id]);
        return changes > 0;
    }

    verifyPassword(usuario, senha) {
        return verifyPassword(senha, usuario.pass);
    }
}

module.exports = { UserModel };
