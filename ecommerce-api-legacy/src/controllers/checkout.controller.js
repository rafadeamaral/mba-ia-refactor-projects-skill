'use strict';

const { BusinessRuleError, NotFoundError, ValidationError } = require('../middlewares/errors');
const logger = require('../utils/logger');

/**
 * Fluxo de checkout.
 *
 * A versão anterior tinha este fluxo em cinco níveis de callback aninhado dentro do handler HTTP,
 * sem transação: uma falha ao registrar o pagamento deixava o aluno matriculado mesmo assim.
 */
class CheckoutController {
    constructor({ db, userModel, courseModel, enrollmentModel, paymentModel, auditModel, paymentGateway }) {
        this.db = db;
        this.users = userModel;
        this.courses = courseModel;
        this.enrollments = enrollmentModel;
        this.payments = paymentModel;
        this.audit = auditModel;
        this.gateway = paymentGateway;
    }

    async execute({ name, email, password, courseId, card }) {
        const curso = await this.courses.findActiveById(courseId);
        if (!curso) throw new NotFoundError('Curso não encontrado');

        const usuarioExistente = await this.users.findByEmail(email);
        if (!usuarioExistente && !password) {
            throw new ValidationError('Senha é obrigatória para criar um novo usuário');
        }

        const pagamento = this.gateway.charge({ card, amount: curso.price });
        if (pagamento.status !== 'PAID') {
            // Mensagem e status preservados da versão anterior.
            throw new BusinessRuleError('Pagamento recusado');
        }

        // Tudo ou nada: usuário, matrícula, pagamento e auditoria em uma única transação.
        const matriculaId = await this.db.transaction(async () => {
            const usuario = usuarioExistente
                ?? await this.users.create({ name, email, password });

            const matricula = await this.enrollments.create({
                userId: usuario.id, courseId: curso.id,
            });
            await this.payments.create({
                enrollmentId: matricula.id, amount: curso.price, status: pagamento.status,
            });
            await this.audit.record(`Checkout curso ${curso.id} por ${usuario.id}`);

            return matricula.id;
        });

        logger.info('checkout_concluido', { enrollment_id: matriculaId, course_id: curso.id });
        return { msg: 'Sucesso', enrollment_id: matriculaId };
    }
}

module.exports = { CheckoutController };
