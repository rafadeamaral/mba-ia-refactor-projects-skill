"""Notificações — efeito colateral isolado atrás de uma interface injetável.

Na versão anterior os disparos de e-mail/SMS/push eram `print()` dentro do controller HTTP,
o que tornava a política de notificação inacessível a qualquer outro consumidor (worker, CLI)
e impossível de testar sem capturar stdout.
"""
import logging

log = logging.getLogger(__name__)


class NotificacaoService:
    """Implementação de desenvolvimento: registra a intenção de notificar.

    A integração real (SMTP, gateway de SMS, push) substitui esta classe sem que o controller
    precise mudar — é isso que a injeção de dependência compra.
    """

    CANAIS = ("email", "sms", "push")

    def pedido_criado(self, pedido_id: int, usuario_id: int) -> None:
        for canal in self.CANAIS:
            log.info("notificacao canal=%s evento=pedido_criado pedido_id=%s usuario_id=%s",
                     canal, pedido_id, usuario_id)

    def status_alterado(self, pedido_id: int, novo_status: str) -> None:
        log.info("notificacao canal=email evento=status_alterado pedido_id=%s status=%s",
                 pedido_id, novo_status)
