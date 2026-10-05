import requests

from src.config import config


class TelegramPublisher:
    """Responsável pelo envio de mensagens ao Telegram."""

    BASE_URL = "https://api.telegram.org"

    def __init__(self):
        if not config.TELEGRAM_BOT_TOKEN:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN não configurado."
            )

        if not config.TELEGRAM_CHAT_ID:
            raise ValueError(
                "TELEGRAM_CHAT_ID não configurado."
            )

        self.bot_token = config.TELEGRAM_BOT_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID

    def send_photo(
        self,
        image_url: str,
        caption: str,
    ) -> dict:
        """Envia uma imagem com legenda HTML."""

        url = (
            f"{self.BASE_URL}/bot"
            f"{self.bot_token}/sendPhoto"
        )

        response = requests.post(
            url,
            json={
                "chat_id": self.chat_id,
                "photo": image_url,
                "caption": caption,
                "parse_mode": "HTML",
            },
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        if not data.get("ok"):
            raise RuntimeError(
                f"Telegram retornou erro: {data}"
            )

        return data