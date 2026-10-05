import os

from dotenv import load_dotenv


load_dotenv()


class Config:
    # PostgreSQL
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Mercado Livre - OAuth
    ML_CLIENT_ID = os.getenv("ML_CLIENT_ID")
    ML_CLIENT_SECRET = os.getenv("ML_CLIENT_SECRET")
    ML_REDIRECT_URI = os.getenv("ML_REDIRECT_URI")

    # Mercado Livre - Afiliados
    ML_AFFILIATE_TAG = os.getenv("ML_AFFILIATE_TAG")

    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Telegram Admin
    TELEGRAM_ADMIN_BOT_TOKEN = os.getenv("TELEGRAM_ADMIN_BOT_TOKEN")
    TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID")

    # Execução
    CHECK_INTERVAL_MINUTES = int(
        os.getenv("CHECK_INTERVAL_MINUTES", "60")
    )


config = Config()