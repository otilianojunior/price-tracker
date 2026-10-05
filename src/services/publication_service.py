from datetime import datetime, timezone
from sqlalchemy import select
from src.database.models import Oferta, Produto, Publicacao
from src.notifications.service import NotificationService
from src.services.affiliate_link_service import AffiliateLinkService
from src.services.publication_formatter import PublicationFormatter


class PublicationService:
    """Prepara e executa publicações."""

    def __init__(
        self,
        affiliate_link_service: AffiliateLinkService,
        notification_service: NotificationService,
    ):
        self.affiliate_link_service = affiliate_link_service
        self.notification_service = notification_service

    def prepare_publication(
        self,
        session,
        promotion_data: dict,
    ) -> Publicacao:
        """
        Gera/reutiliza o link afiliado, formata a mensagem
        e cria uma publicação pendente.

        Se já existir uma publicação pendente para a mesma
        promoção e canal, reutiliza essa publicação.
        """

        publicacao_existente = session.scalar(
            select(Publicacao)
            .where(
                Publicacao.promocao_id
                == promotion_data["promocao_id"],
                Publicacao.canal_id
                == promotion_data["canal_id"],
                Publicacao.status == "pendente",
            )
            .order_by(Publicacao.id.desc())
        )

        if publicacao_existente is not None:
            return publicacao_existente

        link = self.affiliate_link_service.create_from_prepared_promotion(
            promotion_data
        )

        texto = PublicationFormatter.format_telegram(
            promotion_data=promotion_data,
            affiliate_url=link.url_afiliado,
        )

        publicacao = Publicacao(
            promocao_id=promotion_data["promocao_id"],
            oferta_id=promotion_data["oferta_id"],
            link_afiliado_id=link.id,
            canal_id=promotion_data["canal_id"],
            texto_publicado=texto,
            preco_publicado=promotion_data["preco_atual"],
            desconto_publicado=promotion_data["desconto_percentual"],
            status="pendente",
        )

        session.add(publicacao)
        session.commit()
        session.refresh(publicacao)

        return publicacao

    def publish(
        self,
        session,
        publicacao_id: int,
    ) -> Publicacao:
        """Envia uma publicação pendente e atualiza seu status."""

        publicacao = session.get(
            Publicacao,
            publicacao_id,
        )

        if publicacao is None:
            raise ValueError(
                f"Publicação {publicacao_id} não encontrada."
            )

        if publicacao.status != "pendente":
            raise ValueError(
                f"Publicação {publicacao_id} não está pendente. "
                f"Status atual: {publicacao.status}"
            )

        oferta = session.get(
            Oferta,
            publicacao.oferta_id,
        )

        if oferta is None:
            raise ValueError(
                f"Oferta da publicação {publicacao_id} não encontrada."
            )

        produto = session.get(
            Produto,
            oferta.produto_id,
        )

        if produto is None:
            raise ValueError(
                f"Produto da publicação {publicacao_id} não encontrado."
            )

        try:
            resultado = self.notification_service.send_telegram(
                image_url=produto.imagem_principal,
                caption=publicacao.texto_publicado,
            )

            mensagem = resultado.get("result") or {}
            mensagem_id = mensagem.get("message_id")

            publicacao.status = "publicado"
            publicacao.mensagem_externa_id = (
                str(mensagem_id)
                if mensagem_id is not None
                else None
            )
            publicacao.publicado_em = datetime.now(
                timezone.utc
            )
            publicacao.erro = None

            session.commit()
            session.refresh(publicacao)

            return publicacao

        except Exception as exc:
            publicacao.status = "erro"
            publicacao.erro = str(exc)

            session.commit()
            session.refresh(publicacao)

            raise