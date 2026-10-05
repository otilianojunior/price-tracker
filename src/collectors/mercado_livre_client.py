import time

import requests

from src.auth.mercado_livre import MercadoLivreAuth


class MercadoLivreClient:
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self):
        self.auth = MercadoLivreAuth()
        self.session = requests.Session()

    def get(
        self,
        path: str,
        params: dict | None = None,
    ) -> dict:
        """Executa uma requisição GET autenticada com retry para 429."""

        access_token = self.auth.get_valid_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        max_retries_429 = 3

        for tentativa in range(max_retries_429 + 1):
            response = self.session.get(
                f"{self.BASE_URL}{path}",
                params=params,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 401:
                self.auth.refresh_access_token()

                access_token = self.auth.get_valid_access_token()

                headers = {
                    "Authorization": f"Bearer {access_token}",
                }

                response = self.session.get(
                    f"{self.BASE_URL}{path}",
                    params=params,
                    headers=headers,
                    timeout=30,
                )

            if response.status_code != 429:
                break

            if tentativa >= max_retries_429:
                break

            retry_after = response.headers.get("Retry-After")

            try:
                espera = float(retry_after)
            except (TypeError, ValueError):
                espera = 2 ** (tentativa + 1)

            print(
                f"429 Too Many Requests em {path}. "
                f"Tentativa {tentativa + 1}/{max_retries_429}. "
                f"Aguardando {espera:.1f}s..."
            )

            time.sleep(espera)

        response.raise_for_status()

        return response.json()