import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests
from sqlalchemy import select

from src.config import config
from src.database.database import SessionLocal
from src.database.models import AutenticacaoOAuth, Plataforma


class MercadoLivreAuth:
    """Gerencia a autenticação OAuth do Mercado Livre."""

    AUTHORIZATION_URL = (
        "https://auth.mercadolivre.com.br/authorization"
    )

    TOKEN_URL = (
        "https://api.mercadolibre.com/oauth/token"
    )

    PLATFORM_CODE = "mercado_livre"

    def __init__(self):
        self.client_id = config.ML_CLIENT_ID
        self.client_secret = config.ML_CLIENT_SECRET
        self.redirect_uri = config.ML_REDIRECT_URI

    def get_authorization_url(self) -> tuple[str, str]:
        """Gera a URL de autorização e um state seguro."""

        state = secrets.token_urlsafe(32)

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }

        authorization_url = (
            f"{self.AUTHORIZATION_URL}?"
            f"{urlencode(params)}"
        )

        return authorization_url, state

    def exchange_code_for_token(
        self,
        code: str,
    ) -> dict:
        """Troca o authorization code por tokens OAuth."""

        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        response = requests.post(
            self.TOKEN_URL,
            data=payload,
            timeout=30,
        )

        response.raise_for_status()

        tokens = response.json()

        self._save_tokens(tokens)

        return tokens

    def refresh_access_token(self) -> dict:
        """Renova o access token usando o refresh token salvo."""

        with SessionLocal() as session:
            platform_id = self._get_platform_id(session)

            auth = session.scalar(
                select(AutenticacaoOAuth).where(
                    AutenticacaoOAuth.plataforma_id
                    == platform_id
                )
            )

            if not auth:
                raise ValueError(
                    "Nenhuma autenticação OAuth encontrada "
                    "para o Mercado Livre."
                )

            refresh_token = auth.refresh_token

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }

        response = requests.post(
            self.TOKEN_URL,
            data=payload,
            timeout=30,
        )

        response.raise_for_status()

        tokens = response.json()

        self._save_tokens(tokens)

        return tokens

    def get_valid_access_token(self) -> str:
        """Retorna um access token válido."""

        with SessionLocal() as session:
            platform_id = self._get_platform_id(session)

            auth = session.scalar(
                select(AutenticacaoOAuth).where(
                    AutenticacaoOAuth.plataforma_id
                    == platform_id
                )
            )

            if not auth:
                raise ValueError(
                    "Nenhuma autenticação OAuth encontrada "
                    "para o Mercado Livre."
                )

            if self._token_is_valid(auth):
                return auth.access_token

        tokens = self.refresh_access_token()

        return tokens["access_token"]

    def _token_is_valid(
        self,
        auth: AutenticacaoOAuth,
    ) -> bool:
        """Verifica se o access token ainda está válido."""

        now = datetime.now(timezone.utc)

        return auth.expira_em > now

    def _get_platform_id(self, session) -> int:
        """Obtém o ID interno da plataforma pelo código."""

        plataforma = session.scalar(
            select(Plataforma).where(
                Plataforma.codigo == self.PLATFORM_CODE
            )
        )

        if plataforma is None:
            raise ValueError(
                f"Plataforma '{self.PLATFORM_CODE}' não encontrada."
            )

        return plataforma.id

    def _save_tokens(
        self,
        tokens: dict,
    ) -> None:
        """Cria ou atualiza a autenticação OAuth no banco."""

        expires_in = tokens.get(
            "expires_in",
            21600,
        )

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(seconds=expires_in - 60)
        )

        with SessionLocal() as session:
            platform_id = self._get_platform_id(session)

            auth = session.scalar(
                select(AutenticacaoOAuth).where(
                    AutenticacaoOAuth.plataforma_id
                    == platform_id
                )
            )

            if auth is None:
                auth = AutenticacaoOAuth(
                    plataforma_id=platform_id,
                    access_token=tokens["access_token"],
                    refresh_token=tokens["refresh_token"],
                )

                session.add(auth)
            else:
                auth.access_token = tokens["access_token"]

                if tokens.get("refresh_token"):
                    auth.refresh_token = tokens["refresh_token"]

            auth.tipo_token = tokens.get(
                "token_type",
                "Bearer",
            )

            auth.expira_em = expires_at

            auth.escopos = tokens.get(
                "scope"
            )

            session.commit()