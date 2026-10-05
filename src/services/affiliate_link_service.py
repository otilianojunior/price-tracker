from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from src.database.database import SessionLocal
from src.database.models import LinkAfiliado
from src.services.mercado_livre_affiliate import MercadoLivreAffiliateClient


class AffiliateLinkService:
    """Gerencia criação e persistência de links afiliados."""

    def __init__(
        self,
        affiliate_client: MercadoLivreAffiliateClient,
    ):
        self.affiliate_client = affiliate_client

    def create_and_save(
        self,
        promocao_id: int,
        oferta_id: int,
        url_original: str,
        tag: str,
    ) -> LinkAfiliado:
        """
        Reutiliza um link afiliado ativo por até 24 horas.

        Após 24 horas, desativa o link anterior, gera um novo
        link e salva o novo registro.
        """

        session = SessionLocal()

        try:
            agora = datetime.now(timezone.utc)
            limite_validade = agora - timedelta(hours=24)

            link_existente = session.scalar(
                select(LinkAfiliado)
                .where(
                    LinkAfiliado.oferta_id == oferta_id,
                    LinkAfiliado.tag == tag,
                    LinkAfiliado.ativo.is_(True),
                )
                .order_by(LinkAfiliado.criado_em.desc())
            )

            if (
                link_existente
                and link_existente.criado_em > limite_validade
            ):
                return link_existente

            if link_existente:
                link_existente.ativo = False

            resultado = self.affiliate_client.create_link(
                url=url_original,
                tag=tag,
            )

            links = resultado.get("urls") or []

            if not links:
                raise ValueError(
                    "Mercado Livre não retornou nenhum link afiliado."
                )

            link_data = links[0]

            url_afiliado = link_data.get("short_url")

            if not url_afiliado:
                url_afiliado = link_data.get("long_url")

            if not url_afiliado:
                raise ValueError(
                    "Mercado Livre não retornou short_url nem long_url."
                )

            link = LinkAfiliado(
                promocao_id=promocao_id,
                oferta_id=oferta_id,
                url_original=url_original,
                url_afiliado=url_afiliado,
                tag=tag,
                ativo=True,
            )

            session.add(link)
            session.commit()
            session.refresh(link)

            return link

        except Exception:
            session.rollback()
            raise

        finally:
            session.close()

    def create_from_prepared_promotion(
        self,
        promotion_data: dict,
    ) -> LinkAfiliado:
        """
        Gera e salva o link afiliado usando os dados preparados
        pelo MercadoLivreService.
        """

        return self.create_and_save(
            promocao_id=promotion_data["promocao_id"],
            oferta_id=promotion_data["oferta_id"],
            url_original=promotion_data["url_oferta"],
            tag=promotion_data["tag_afiliado"],
        )