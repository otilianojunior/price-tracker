from playwright.sync_api import sync_playwright

from src.auth.mercado_livre_browser import MercadoLivreBrowser


class MercadoLivreAffiliateClient:
    """Cliente para geração de links afiliados do Mercado Livre."""

    ENDPOINT = (
        "https://www.mercadolivre.com.br/"
        "affiliate-program/api/v2/affiliates/createLink"
    )

    CDP_URL = "http://127.0.0.1:9222"

    def create_link(self, url: str, tag: str) -> dict:

        with sync_playwright() as playwright:
            browser = playwright.chromium.connect_over_cdp(
                self.CDP_URL
            )

            context = browser.contexts[0]

            page = (
                context.pages[0]
                if context.pages
                else context.new_page()
            )

            resultado = page.evaluate(
                """
                async ({ endpoint, url, tag }) => {
                    const response = await fetch(endpoint, {
                        method: "POST",
                        headers: {
                            "accept": "application/json, text/plain, */*",
                            "content-type": "application/json"
                        },
                        body: JSON.stringify({
                            urls: [url],
                            tag: tag
                        }),
                        credentials: "include"
                    });

                    const text = await response.text();

                    return {
                        status: response.status,
                        contentType: response.headers.get(
                            "content-type"
                        ),
                        body: text
                    };
                }
                """,
                {
                    "endpoint": self.ENDPOINT,
                    "url": url,
                    "tag": tag,
                },
            )

            browser.close()

        if resultado["status"] < 200 or resultado["status"] >= 300:
            raise RuntimeError(
                f"Mercado Livre retornou HTTP "
                f"{resultado['status']}: {resultado['body']}"
            )

        import json

        return json.loads(resultado["body"])