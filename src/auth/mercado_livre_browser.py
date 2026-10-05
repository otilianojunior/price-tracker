from playwright.sync_api import sync_playwright

from scripts.start_ml_chrome import ensure_chrome
from src.auth.exceptions import (
    MercadoLivreLoginRequiredError,
    MercadoLivreNetworkError,
)


class MercadoLivreBrowser:
    CDP_URL = "http://127.0.0.1:9222"
    HOME_URL = "https://www.mercadolivre.com.br/"

    def check_session(self) -> dict:
        ensure_chrome()

        try:
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

                page.goto(
                    self.HOME_URL,
                    wait_until="domcontentloaded",
                    timeout=30000,
                )

                page.wait_for_timeout(2000)

                cookies = context.cookies(self.HOME_URL)

                cookie_names = {
                    cookie["name"]
                    for cookie in cookies
                }

                csrf_present = "_csrf" in cookie_names

                login_button = page.get_by_text(
                    "Entrar",
                    exact=True,
                )

                login_button_present = login_button.count() > 0

                authenticated = (
                    csrf_present
                    and not login_button_present
                )

                resultado = {
                    "authenticated": authenticated,
                    "cookies": len(cookies),
                    "csrf": csrf_present,
                    "login_button": login_button_present,
                    "title": page.title(),
                    "url": page.url,
                }

                if not authenticated:
                    browser.close()

                    raise MercadoLivreLoginRequiredError(
                        "Sessão do Mercado Livre não está autenticada."
                    )

                browser.close()

                return resultado

        except MercadoLivreLoginRequiredError:
            raise

        except Exception as erro:
            raise MercadoLivreNetworkError(
                f"Falha ao verificar sessão do Mercado Livre: {erro}"
            ) from erro
