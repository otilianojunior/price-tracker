from src.notifications.service import NotificationService


class AdminNotificationService:
    """Gerencia notificações administrativas do sistema."""

    def __init__(self):
        self.notifications = NotificationService()

    def notify_mercado_livre_login_required(self) -> dict:
        """Avisa que o Mercado Livre precisa de novo login."""

        mensagem = (
            "🔴 Mercado Livre precisa de login\n\n"
            "A sessão do Mercado Livre não está autenticada.\n"
            "Faça login novamente no Chrome do projeto."
        )

        return self.notifications.send_admin_telegram(mensagem)