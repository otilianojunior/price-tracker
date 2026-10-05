import logging
from typing import Any

from src.auth.exceptions import (
    MercadoLivreLoginRequiredError,
    MercadoLivreNetworkError,
)
from src.collectors.mercado_livre_client import MercadoLivreClient
from src.collectors.mercado_livre_categories import (
    MERCADO_LIVRE_CATEGORIAS,
)


logger = logging.getLogger(__name__)


class MercadoLivreCollector:
    """Coleta e normaliza produtos e ofertas do Mercado Livre."""

    BASE_URL = "https://www.mercadolivre.com.br"

    def __init__(
        self,
        max_products_per_category: int = 10,
    ):
        self.client = MercadoLivreClient()
        self.max_products_per_category = max_products_per_category

    def _discover_product_ids(
        self,
        category_slug: str,
        start_position: int = 1,
    ) -> list[str]:
        """Descobre product_ids através do endpoint de highlights."""

        category_id = MERCADO_LIVRE_CATEGORIAS.get(
            category_slug
        )

        if not category_id:
            raise ValueError(
                f"Categoria do Mercado Livre não encontrada: "
                f"{category_slug}"
            )

        data = self.client.get(
            f"/highlights/MLB/category/{category_id}"
        )

        product_ids = []

        for item in data.get("content", []):
            if item.get("type") != "PRODUCT":
                continue

            product_id = item.get("id")

            if product_id:
                product_ids.append(product_id)

        if not product_ids:
            return []

        start_index = start_position - 1

        # Se o cursor estiver além da quantidade disponível,
        # volta para o início da lista.
        if start_index >= len(product_ids):
            start_index = 0

        return product_ids[
            start_index:start_index + self.max_products_per_category
        ]

    def _get_product_details(
        self,
        product_id: str,
    ) -> dict[str, Any]:
        """Busca os dados gerais de um produto."""

        data = self.client.get(
            f"/products/{product_id}"
        )

        pictures = data.get("pictures") or []

        image_urls = [
            picture.get("url")
            for picture in pictures
            if picture.get("url")
        ]

        product_url = (
            f"{self.BASE_URL}/p/{product_id}"
        )

        return {
            "product_id": product_id,
            "nome": (
                data.get("name")
                or data.get("title")
                or "Produto sem título"
            ),
            "imagem_principal": (
                image_urls[0]
                if image_urls
                else None
            ),
            "image_urls": image_urls,
            "url_produto": product_url,
        }

    def _get_offers(
        self,
        product_id: str,
    ) -> list[dict[str, Any]]:
        """Busca somente a melhor oferta disponível para o produto."""

        data = self.client.get(
            f"/products/{product_id}/items"
        )

        items = data.get("results", [])

        if not items:
            return []

        item = items[0]

        item_id = item.get("item_id")
        price = item.get("price")

        if not item_id or price is None:
            return []

        shipping = item.get("shipping") or {}

        return [
            {
                "item_id": item_id,
                "preco": price,
                "preco_original": item.get(
                    "original_price"
                ),
                "seller_id": item.get(
                    "seller_id"
                ),
                "loja_oficial_id": item.get(
                    "official_store_id"
                ),
                "frete_gratis": shipping.get(
                    "free_shipping",
                    False,
                ),
                "moeda": item.get(
                    "currency_id",
                    "BRL",
                ),
                "url_oferta": (
                    f"{self.BASE_URL}/p/"
                    f"{product_id}"
                    f"?pdp_filters=item_id%3A"
                    f"{item_id}"
                    f"&wid={item_id}"
                ),
            }
        ]

    def collect_product(
        self,
        product_id: str,
        category_slug: str,
    ) -> dict[str, Any]:
        """Coleta um produto conhecido pelo product_id."""

        details = self._get_product_details(
            product_id
        )

        offers = self._get_offers(
            product_id
        )

        return {
            "produto": {
                "produto_id_externo": (
                    details["product_id"]
                ),
                "nome": details["nome"],
                "url_produto": (
                    details["url_produto"]
                ),
                "imagem_principal": (
                    details["imagem_principal"]
                ),
                "image_urls": (
                    details["image_urls"]
                ),
                "categoria": category_slug,
            },
            "ofertas": offers,
        }

    def collect(
        self,
        category_slug: str,
        start_position: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Coleta produtos e somente a melhor oferta de cada produto.

        Não grava nada no banco.
        Retorna somente dados normalizados.
        """

        product_ids = self._discover_product_ids(
            category_slug,
            start_position=start_position,
        )

        logger.info(
            "Categoria %s | %s produtos encontrados.",
            category_slug,
            len(product_ids),
        )

        products = []

        processados = 0
        sem_oferta = 0
        falhas = 0

        for product_id in product_ids:
            try:
                details = self._get_product_details(
                    product_id
                )

                offers = self._get_offers(
                    product_id
                )

                if not offers:
                    sem_oferta += 1

                    logger.warning(
                        "Categoria %s | produto %s sem oferta.",
                        category_slug,
                        product_id,
                    )

                    continue

                products.append(
                    {
                        "produto": {
                            "produto_id_externo": (
                                details["product_id"]
                            ),
                            "nome": details["nome"],
                            "url_produto": (
                                details["url_produto"]
                            ),
                            "imagem_principal": (
                                details["imagem_principal"]
                            ),
                            "image_urls": (
                                details["image_urls"]
                            ),
                            "categoria": category_slug,
                        },
                        "ofertas": offers,
                    }
                )

                processados += 1

            except (
                MercadoLivreLoginRequiredError,
                MercadoLivreNetworkError,
            ):
                raise

            except (
                MercadoLivreLoginRequiredError,
                MercadoLivreNetworkError,
            ):
                raise

            except Exception as erro:
                falhas += 1

                logger.exception(
                    "Categoria %s | erro ao coletar produto %s: %s",
                    category_slug,
                    product_id,
                    erro,
                )

        logger.info(
            "Categoria %s | resumo: "
            "encontrados=%s | processados=%s | "
            "sem_oferta=%s | falhas=%s",
            category_slug,
            len(product_ids),
            processados,
            sem_oferta,
            falhas,
        )

        return products