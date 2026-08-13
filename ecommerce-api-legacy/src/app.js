'use strict';

const express = require('express');

const config = require('./config');
const { CheckoutController } = require('./controllers/checkout.controller');
const { ReportController } = require('./controllers/report.controller');
const { UserController } = require('./controllers/user.controller');
const { errorHandler, notFoundHandler } = require('./middlewares/error-handler');
const { AuditModel } = require('./models/audit.model');
const { CourseModel } = require('./models/course.model');
const { EnrollmentModel } = require('./models/enrollment.model');
const { PaymentModel } = require('./models/payment.model');
const { UserModel } = require('./models/user.model');
const checkoutRoutes = require('./routes/checkout.routes');
const reportRoutes = require('./routes/report.routes');
const userRoutes = require('./routes/user.routes');
const { FakePaymentGateway } = require('./services/payment.gateway');

/**
 * Composition root — monta a aplicação e liga as camadas.
 * Sem SQL, sem rota inline, sem regra de negócio.
 *
 * Recebe o banco pronto por parâmetro: é isso que permite instanciar a aplicação com um banco
 * de teste sem tocar em código de produção.
 */
function createApp({ db, paymentGateway } = {}) {
    const app = express();
    app.use(express.json({ limit: '100kb' }));

    // Camada de dados
    const userModel = new UserModel(db);
    const courseModel = new CourseModel(db);
    const enrollmentModel = new EnrollmentModel(db);
    const paymentModel = new PaymentModel(db);
    const auditModel = new AuditModel(db);

    // Serviços
    const gateway = paymentGateway ?? new FakePaymentGateway({ gatewayKey: config.payment.gatewayKey });

    // Camada de negócio
    const checkoutController = new CheckoutController({
        db, userModel, courseModel, enrollmentModel, paymentModel, auditModel, paymentGateway: gateway,
    });
    const reportController = new ReportController({ courseModel });
    const userController = new UserController({ userModel });

    // Camada de roteamento
    app.use('/api', checkoutRoutes(checkoutController));
    app.use('/api', reportRoutes(reportController));
    app.use('/api', userRoutes(userController));

    app.use(notFoundHandler);
    app.use(errorHandler);

    return app;
}

module.exports = { createApp };
