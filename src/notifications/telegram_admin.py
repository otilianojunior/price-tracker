import requests

from src.config import Config


class TelegramAdminPublisher:
    """Publicador de notificações administrativas no Telegram."""

    API_URL = "https://api.telegram.org"

    def send_message(self, text: str) -> dict:
        url = (
            f"{self.API_URL}/bot"
            f"{Config.TELEGRAM_ADMIN_BOT_TOKEN}"
            f"/sendMessage"
        )

        response = requests.post(
            url,
            json={
                "chat_id": Config.TELEGRAM_ADMIN_CHAT_ID,
                "text": text,
            },
            timeout=30,
        )

        response.raise_for_status()

        return response.json()