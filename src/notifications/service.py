from src.notifications.telegram import TelegramPublisher
from src.notifications.telegram_admin import TelegramAdminPublisher


class NotificationService:
    """Orquestra o envio das notificações."""

    def __init__(self):
        self.telegram = TelegramPublisher()
        self.telegram_admin = TelegramAdminPublisher()

    def send_telegram(
        self,
        image_url: str,
        caption: str,
    ) -> dict:
        """Envia uma publicação com imagem para o Telegram."""

        return self.telegram.send_photo(
            image_url=image_url,
            caption=caption,
        )

    def send_admin_telegram(self, text: str) -> dict:
        """Envia uma notificação administrativa."""

        return self.telegram_admin.send_message(text)