import re
from decimal import Decimal
from typing import Any

from playwright.sync_api import sync_playwright

from scripts.start_ml_chrome import ensure_chrome


class MercadoLivrePaymentCollector:
    """Coleta condições de pagamento visíveis em uma oferta do Mercado Livre."""

    CDP_URL = "http://127.0.0.1:9222"

    def collect(
        self,
        url_oferta: str,
        item_id: str,
    ) -> dict[str, Any] | None:
        """
        Coleta uma condição de parcelamento explicitamente exibida
        para a oferta selecionada.
        """

        ensure_chrome()

        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(
                self.CDP_URL
            )

            context = browser.contexts[0]
            page = context.new_page()

            try:
                page.goto(
                    url_oferta,
                    wait_until="domcontentloaded",
                    timeout=60000,
                )

                radio = page.locator(
                    f'input[type="radio"][value="{item_id}"]'
                )

                if radio.count() > 0:
                    if not radio.first.is_checked():
                        radio.first.check()

                    page.wait_for_timeout(500)

                subtitle = page.locator(
                    "#pricing_price_subtitle"
                )

                if subtitle.count() != 1:
                    return None

                texto = subtitle.inner_text().strip()

                return self._parse_payment_text(texto)

            finally:
                page.close()
                browser.close()

    def _parse_payment_text(
        self,
        texto: str,
    ) -> dict[str, Any] | None:
        """Converte o texto visual em dados estruturados."""

        texto_normalizado = " ".join(texto.split())

        parcelas_match = re.search(
            r"(\d+)\s*x",
            texto_normalizado,
            re.IGNORECASE,
        )

        valor_match = re.search(
            r"R\$\s*([\d.]+)\s*,\s*(\d{2})",
            texto_normalizado,
            re.IGNORECASE,
        )

        if not parcelas_match or not valor_match:
            return None

        parcelas = int(parcelas_match.group(1))

        valor_inteiro = valor_match.group(1)
        valor_centavos = valor_match.group(2)

        valor_texto = (
            valor_inteiro.replace(".", "")
            + "."
            + valor_centavos
        )

        valor_parcela = Decimal(valor_texto)

        texto_lower = texto_normalizado.lower()

        sem_juros = "sem juros" in texto_lower

        if "cartão" in texto_lower or "cartao" in texto_lower:
            forma_pagamento = "cartao"
        else:
            forma_pagamento = None

        return {
            "parcelas": parcelas,
            "valor_parcela": valor_parcela,
            "sem_juros": sem_juros,
            "forma_pagamento": forma_pagamento,
            "texto": texto_normalizado,
        }