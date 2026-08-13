"""Notificações de task.

Este serviço era código morto: nenhum arquivo o importava, e ainda assim carregava host, usuário
e senha de SMTP hardcoded no construtor — credenciais expostas sem entregar funcionalidade.

A refatoração aplicou a decisão "adotar ou remover" do playbook: ele foi **adotado**, com duas
mudanças — o remetente é injetado (nada de conexão SMTP construída dentro do consumidor) e a
implementação padrão apenas registra em log. Enviar e-mail de verdade seria funcionalidade nova,
fora do escopo; o ponto de extensão fica pronto para receber um `SmtpSender` configurado por
ambiente.
"""
import logging

log = logging.getLogger(__name__)


class LoggingSender:
    """Remetente padrão: registra a notificação em vez de enviá-la."""

    def enviar(self, destino: str, assunto: str, corpo: str) -> bool:
        log.info("notificacao destino=%s assunto=%r", destino, assunto)
        log.debug("notificacao corpo=%r", corpo)
        return True


class NotificationService:
    def __init__(self, sender=None):
        self._sender = sender or LoggingSender()

    def task_atribuida(self, task) -> None:
        if not task.user:
            return
        self._sender.enviar(
            destino=task.user.email,
            assunto=f"Nova task atribuída: {task.title}",
            corpo=(
                f"Olá {task.user.name},\n\n"
                f"A task '{task.title}' foi atribuída a você.\n\n"
                f"Prioridade: {task.priority}\nStatus: {task.status}"
            ),
        )

    def task_atrasada(self, task) -> None:
        if not task.user:
            return
        self._sender.enviar(
            destino=task.user.email,
            assunto=f"Task atrasada: {task.title}",
            corpo=f"Olá {task.user.name},\n\nA task '{task.title}' está atrasada.\n"
                  f"Data limite: {task.due_date}",
        )
