'use strict';

/**
 * Encaminha rejeições de handlers `async` para o middleware de erro.
 *
 * O Express 4 não propaga rejeição de promise automaticamente — sem este wrapper, um `await`
 * que falha derruba o processo Node em vez de virar uma resposta de erro. (No Express 5 isso
 * é nativo e o wrapper deixa de ser necessário.)
 */
const asyncHandler = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

module.exports = { asyncHandler };
