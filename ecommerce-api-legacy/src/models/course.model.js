'use strict';

/**
 * Uma única query monta o relatório inteiro.
 *
 * A versão anterior fazia 1 query de cursos + 1 por curso + 2 por matrícula (1 + N + 2M).
 */
const SQL_RELATORIO = `
    SELECT c.id           AS course_id,
           c.title        AS course,
           e.id           AS enrollment_id,
           u.name         AS student,
           p.amount       AS paid,
           p.status       AS payment_status
      FROM courses c
      LEFT JOIN enrollments e ON e.course_id = c.id
      LEFT JOIN users u       ON u.id = e.user_id
      LEFT JOIN payments p    ON p.enrollment_id = e.id
     ORDER BY c.id, e.id
`;

class CourseModel {
    constructor(db) {
        this.db = db;
    }

    findActiveById(id) {
        return this.db.get(
            'SELECT id, title, price FROM courses WHERE id = ? AND active = 1', [id]);
    }

    financialReportRows() {
        return this.db.all(SQL_RELATORIO);
    }
}

module.exports = { CourseModel };
