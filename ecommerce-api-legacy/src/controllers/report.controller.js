'use strict';

/**
 * Relatório financeiro.
 *
 * A versão anterior orquestrava 1 + N + 2M queries com contadores manuais (`coursesPending`,
 * `enrPending`) para decidir quando responder — o que produzia ordem não-determinística e podia
 * disparar `res.json` duas vezes. Aqui é uma query e um agrupamento em memória.
 */
class ReportController {
    constructor({ courseModel }) {
        this.courses = courseModel;
    }

    async financial() {
        const linhas = await this.courses.financialReportRows();

        const porCurso = new Map();
        for (const linha of linhas) {
            if (!porCurso.has(linha.course_id)) {
                porCurso.set(linha.course_id, { course: linha.course, revenue: 0, students: [] });
            }
            if (linha.enrollment_id == null) continue; // curso sem matrícula

            const curso = porCurso.get(linha.course_id);
            if (linha.payment_status === 'PAID') curso.revenue += linha.paid;
            curso.students.push({
                student: linha.student ?? 'Unknown',
                paid: linha.paid ?? 0,
            });
        }

        return [...porCurso.values()];
    }
}

module.exports = { ReportController };
