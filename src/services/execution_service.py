from collections.abc import Callable

from src.auth.exceptions import (
    MercadoLivreLoginRequiredError,
    MercadoLivreNetworkError,
)
from src.services.admin_notification_service import (
    AdminNotificationService,
)


class ExecutionService:
    """Executa tarefas do sistema e trata eventos operacionais."""

    def __init__(self):
        self.admin_notifications = AdminNotificationService()

    def run(self, operation: Callable):
        """Executa uma operação tratando eventos conhecidos."""

        try:
            return operation()

        except MercadoLivreLoginRequiredError as erro:
            print(
                f"ERRO: Mercado Livre precisa de login: {erro}"
            )

            self.admin_notifications.notify_mercado_livre_login_required()

            raise

        except MercadoLivreNetworkError as erro:
            print(
                f"ERRO: falha de comunicação com o Mercado Livre: {erro}"
            )

            return {
                "status": "erro_operacional",
                "tipo": "mercado_livre_network",
                "mensagem": str(erro),
            }
