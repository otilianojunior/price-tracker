from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from src.database.database import SessionLocal
from src.database.models import (
    Categoria,
    ConfiguracaoAfiliacao,
    Oferta,
    Plataforma,
    Preco,
    Produto,
    Promocao,
    Publicacao,
)
from src.collectors.mercado_livre_payment import MercadoLivrePaymentCollector


class MercadoLivreService:
    """Persiste dados coletados do Mercado Livre."""

    PLATFORM_CODE = "mercado_livre"

    def __init__(self):
        pass

    def capture_payment_condition(
        self,
        session,
        promocao_id: int,
    ) -> dict | None:
        """
        Captura a condição de pagamento da oferta de uma promoção
        e persiste no último Preco da oferta.

        Retorna os dados capturados ou None quando não houver
        condição de parcelamento confirmada.
        """

        promocao = session.scalar(
            select(Promocao).where(
                Promocao.id == promocao_id
            )
        )

        if promocao is None:
            raise ValueError(
                f"Promoção {promocao_id} não encontrada."
            )

        oferta = session.scalar(
            select(Oferta).where(
                Oferta.id == promocao.oferta_id
            )
        )

        if oferta is None:
            raise ValueError(
                f"Oferta {promocao.oferta_id} não encontrada."
            )

        preco = session.scalar(
            select(Preco)
            .where(
                Preco.oferta_id == oferta.id
            )
            .order_by(
                Preco.coletado_em.desc()
            )
            .limit(1)
        )

        if preco is None:
            raise ValueError(
                f"Nenhum preço encontrado para a oferta {oferta.id}."
            )

        collector = MercadoLivrePaymentCollector()

        pagamento = collector.collect(
            url_oferta=oferta.url_oferta,
            item_id=oferta.item_id_externo,
        )

        if pagamento is None:
            return None

        preco.parcelas = pagamento["parcelas"]
        preco.valor_parcela = pagamento["valor_parcela"]
        preco.sem_juros = pagamento["sem_juros"]
        preco.forma_pagamento = pagamento["forma_pagamento"]

        session.commit()
        session.refresh(preco)

        return pagamento

    def select_best_offer_for_product(
        self,
        session,
        produto_id: int,
    ) -> Oferta | None:
        """
        Retorna a melhor oferta atual de um produto.

        Critério principal:
        1. Menor preço atual.
        2. Em caso de empate, frete grátis.
        3. Em caso de empate, loja oficial.

        Não altera dados e não cria promoção.
        """

        ofertas = session.scalars(
            select(Oferta).where(
                Oferta.produto_id == produto_id,
                Oferta.ativo.is_(True),
            )
        ).all()

        melhores = []

        for oferta in ofertas:
            preco = session.scalar(
                select(Preco)
                .where(
                    Preco.oferta_id == oferta.id
                )
                .order_by(
                    Preco.coletado_em.desc()
                )
                .limit(1)
            )

            if preco is None:
                continue

            melhores.append(
                (
                    preco.preco,
                    not oferta.frete_gratis,
                    oferta.loja_oficial_id is None,
                    oferta,
                )
            )

        if not melhores:
            return None

        melhores.sort(
            key=lambda item: (
                item[0],
                item[1],
                item[2],
            )
        )

        return melhores[0][3]
    
    def select_best_promotion_for_product(
        self,
        session,
        produto_id: int,
    ) -> Promocao | None:
        """
        Retorna a melhor promoção atual de um produto.

        Critério:
        1. Menor preço atual.
        2. Em caso de empate, maior redução percentual.
        3. Em caso de empate, promoção mais recente.

        Considera apenas promoções ainda detectadas.
        """

        promocoes = session.scalars(
            select(Promocao)
            .join(Oferta, Promocao.oferta_id == Oferta.id)
            .where(
                Oferta.produto_id == produto_id,
                Oferta.ativo.is_(True),
                Promocao.status == "detectada",
            )
            .order_by(
                Promocao.preco_atual.asc(),
                Promocao.reducao_percentual.desc(),
                Promocao.detectada_em.desc(),
            )
        ).all()

        if not promocoes:
            return None

        return promocoes[0]

    def process_category(
        self,
        products: list[dict],
    ) -> list[Promocao]:
        """
        Persiste produtos, ofertas e preços.

        Retorna as novas promoções detectadas.
        """

        promotion_ids = []

        with SessionLocal() as session:
            platform = session.scalar(
                select(Plataforma).where(
                    Plataforma.codigo == self.PLATFORM_CODE
                )
            )

            if platform is None:
                raise ValueError(
                    "Plataforma 'mercado_livre' não encontrada."
                )

            for data in products:
                product_data = data["produto"]
                offers = data["ofertas"]

                category = session.scalar(
                    select(Categoria).where(
                        Categoria.slug
                        == product_data["categoria"]
                    )
                )

                if category is None:
                    raise ValueError(
                        f"Categoria "
                        f"'{product_data['categoria']}' "
                        f"não encontrada."
                    )

                produto = self._get_or_create_product(
                    session=session,
                    platform_id=platform.id,
                    category_id=category.id,
                    data=product_data,
                )

                for offer_data in offers:
                    promotion = self._process_offer(
                        session=session,
                        produto=produto,
                        data=offer_data,
                    )

                    if promotion is not None:
                        promotion_ids.append(
                            promotion.id
                        )

                produto.ultima_verificacao_em = datetime.now(
                    timezone.utc
                )

            session.commit()

        return promotion_ids

    def can_publish_offer(
        self,
        session,
        oferta_id: int,
        canal_id: int,
        novo_preco: Decimal,
    ) -> bool:
        """
        Verifica se uma oferta pode ser publicada no canal.

        Regras:
        - Nunca publicada: pode publicar.
        - Última publicação há 24h ou mais: pode publicar.
        - Última publicação há menos de 24h:
            - novo preço menor que o preço publicado: pode publicar;
            - preço igual ou maior: não pode publicar.
        """

        last_publication = session.scalar(
            select(Publicacao)
            .where(
                Publicacao.oferta_id == oferta_id,
                Publicacao.canal_id == canal_id,
                Publicacao.status == "publicado",
                Publicacao.publicado_em.is_not(None),
            )
            .order_by(
                Publicacao.publicado_em.desc()
            )
            .limit(1)
        )

        # Nunca publicada
        if last_publication is None:
            return True

        now = datetime.now(timezone.utc)

        # Publicação há 24 horas ou mais
        if (
            now - last_publication.publicado_em
            >= timedelta(hours=24)
        ):
            return True

        # Ainda está dentro das 24 horas.
        # Só permite nova publicação se o preço caiu.
        if last_publication.preco_publicado is None:
            return False

        return novo_preco < last_publication.preco_publicado

    def can_publish_promotion(
        self,
        session,
        promocao_id: int,
        canal_id: int,
    ) -> bool:
        """
        Verifica se uma promoção pode ser publicada em um canal.

        Usa o preço atual da promoção para aplicar as regras
        de publicação da oferta.
        """

        promocao = session.scalar(
            select(Promocao).where(
                Promocao.id == promocao_id
            )
        )

        if promocao is None:
            raise ValueError(
                f"Promoção {promocao_id} não encontrada."
            )

        return self.can_publish_offer(
            session=session,
            oferta_id=promocao.oferta_id,
            canal_id=canal_id,
            novo_preco=promocao.preco_atual,
        )

    def get_active_categories(
        self,
    ) -> list[dict]:
        """
        Retorna as categorias ativas que possuem
        configuração de afiliação ativa.
        """

        with SessionLocal() as session:
            categorias = session.execute(
                select(
                    Categoria.id,
                    Categoria.nome,
                    Categoria.slug,
                    ConfiguracaoAfiliacao.id.label(
                        "configuracao_afiliacao_id"
                    ),
                    ConfiguracaoAfiliacao.nome.label(
                        "nicho"
                    ),
                    ConfiguracaoAfiliacao.tag_afiliado,
                    ConfiguracaoAfiliacao.canal_id,
                )
                .join(
                    ConfiguracaoAfiliacao,
                    ConfiguracaoAfiliacao.id
                    == Categoria.configuracao_afiliacao_id,
                )
                .where(
                    Categoria.ativa.is_(True),
                    ConfiguracaoAfiliacao.ativa.is_(True),
                )
                .order_by(Categoria.id)
            ).all()

            return [
                {
                    "id": categoria.id,
                    "nome": categoria.nome,
                    "slug": categoria.slug,
                    "configuracao_afiliacao_id": (
                        categoria.configuracao_afiliacao_id
                    ),
                    "nicho": categoria.nicho,
                    "tag_afiliado": categoria.tag_afiliado,
                    "canal_id": categoria.canal_id,
                }
                for categoria in categorias
            ]


    def get_promotions_for_publication(
        self,
    ) -> list[Promocao]:
        """
        Retorna as melhores promoções elegíveis para publicação.

        A categoria do produto determina automaticamente:
        - configuração de afiliação;
        - tag de afiliado;
        - canal de publicação.

        Para cada produto:
        1. considera somente produtos ativos;
        2. exige categoria ativa;
        3. exige configuração de afiliação ativa;
        4. considera somente promoções detectadas;
        5. escolhe a promoção com menor preço atual;
        6. aplica as regras de publicação do canal;
        7. retorna no máximo uma promoção por produto.
        """

        with SessionLocal() as session:
            produtos = session.scalars(
                select(Produto).where(
                    Produto.ativo.is_(True)
                )
            ).all()

            promotions = []

            for produto in produtos:
                categoria = session.scalar(
                    select(Categoria).where(
                        Categoria.id == produto.categoria_id,
                        Categoria.ativa.is_(True),
                    )
                )

                if categoria is None:
                    continue

                if categoria.configuracao_afiliacao_id is None:
                    continue

                configuracao = session.scalar(
                    select(ConfiguracaoAfiliacao).where(
                        ConfiguracaoAfiliacao.id
                        == categoria.configuracao_afiliacao_id,
                        ConfiguracaoAfiliacao.ativa.is_(True),
                    )
                )

                if configuracao is None:
                    continue

                promotion = self.select_best_promotion_for_product(
                    session=session,
                    produto_id=produto.id,
                )

                if promotion is None:
                    continue

                if not self.can_publish_promotion(
                    session=session,
                    promocao_id=promotion.id,
                    canal_id=configuracao.canal_id,
                ):
                    continue

                promotions.append(promotion)

            return promotions

    def prepare_promotion_for_publication(
        self,
        session,
        promocao_id: int,
    ) -> dict:
        """
        Prepara os dados de uma promoção elegível
        para o próximo estágio do fluxo de publicação.

        A configuração de afiliado é determinada automaticamente
        pela categoria do produto.
        """

        promocao = session.scalar(
            select(Promocao).where(
                Promocao.id == promocao_id
            )
        )

        if promocao is None:
            raise ValueError(
                f"Promoção {promocao_id} não encontrada."
            )

        oferta = session.scalar(
            select(Oferta).where(
                Oferta.id == promocao.oferta_id
            )
        )

        if oferta is None:
            raise ValueError(
                f"Oferta {promocao.oferta_id} não encontrada."
            )

        produto = session.scalar(
            select(Produto).where(
                Produto.id == oferta.produto_id
            )
        )

        if produto is None:
            raise ValueError(
                f"Produto da oferta {oferta.id} não encontrado."
            )

        categoria = session.scalar(
            select(Categoria).where(
                Categoria.id == produto.categoria_id
            )
        )

        if categoria is None:
            raise ValueError(
                f"Categoria {produto.categoria_id} não encontrada."
            )

        if categoria.configuracao_afiliacao_id is None:
            raise ValueError(
                f"A categoria '{categoria.nome}' "
                "não possui configuração de afiliado."
            )

        configuracao = session.scalar(
            select(ConfiguracaoAfiliacao).where(
                ConfiguracaoAfiliacao.id
                == categoria.configuracao_afiliacao_id,
                ConfiguracaoAfiliacao.ativa.is_(True),
            )
        )

        if configuracao is None:
            raise ValueError(
                f"A configuração de afiliado da categoria "
                f"'{categoria.nome}' não foi encontrada ou está inativa."
            )

        if not self.can_publish_promotion(
            session=session,
            promocao_id=promocao_id,
            canal_id=configuracao.canal_id,
        ):
            raise ValueError(
                f"Promoção {promocao_id} não está elegível "
                f"para publicação no canal {configuracao.canal_id}."
            )

        self.capture_payment_condition(
            session=session,
            promocao_id=promocao_id,
        )

        preco = session.scalar(
            select(Preco)
            .where(
                Preco.oferta_id == oferta.id
            )
            .order_by(
                Preco.coletado_em.desc()
            )
            .limit(1)
        )

        return {
            "promocao_id": promocao.id,
            "oferta_id": oferta.id,
            "produto_id": produto.id,
            "produto_id_externo": produto.produto_id_externo,
            "nome_produto": produto.nome,
            "preco_atual": str(promocao.preco_atual),
            "parcelas": (
                preco.parcelas
                if preco is not None
                else None
            ),
            "valor_parcela": (
                str(preco.valor_parcela)
                if preco is not None
                and preco.valor_parcela is not None
                else None
            ),
            "sem_juros": (
                preco.sem_juros
                if preco is not None
                else None
            ),
            "forma_pagamento": (
                preco.forma_pagamento
                if preco is not None
                else None
            ),
            "preco_anterior": str(promocao.preco_anterior),
            "preco_original": (
                str(promocao.preco_original)
                if promocao.preco_original is not None
                else None
            ),
            "desconto_percentual": (
                str(promocao.desconto_percentual)
                if promocao.desconto_percentual is not None
                else None
            ),
            "reducao_percentual": (
                str(promocao.reducao_percentual)
                if promocao.reducao_percentual is not None
                else None
            ),
            "url_produto": produto.url_produto,
            "imagem_principal": produto.imagem_principal,
            "url_oferta": oferta.url_oferta,
            "categoria_id": categoria.id,
            "categoria": categoria.nome,
            "categoria_slug": categoria.slug,
            "configuracao_afiliacao_id": configuracao.id,
            "nicho": configuracao.nome,
            "tag_afiliado": configuracao.tag_afiliado,
            "canal_id": configuracao.canal_id,
        }
    
    def _get_or_create_product(
        self,
        session,
        platform_id: int,
        category_id: int,
        data: dict,
    ) -> Produto:
        """Busca um produto existente ou cria um novo."""

        produto = session.scalar(
            select(Produto).where(
                Produto.plataforma_id == platform_id,
                Produto.produto_id_externo
                == data["produto_id_externo"],
            )
        )

        now = datetime.now(timezone.utc)

        if produto is None:
            produto = Produto(
                plataforma_id=platform_id,
                categoria_id=category_id,
                produto_id_externo=data[
                    "produto_id_externo"
                ],
                nome=data["nome"],
                url_produto=data["url_produto"],
                imagem_principal=data[
                    "imagem_principal"
                ],
                criado_em=now,
                atualizado_em=now,
            )

            session.add(produto)
            session.flush()

        else:
            produto.categoria_id = category_id
            produto.nome = data["nome"]
            produto.url_produto = data["url_produto"]
            produto.imagem_principal = data[
                "imagem_principal"
            ]
            produto.atualizado_em = now

        return produto

    def _process_offer(
        self,
        session,
        produto: Produto,
        data: dict,
    ) -> Promocao | None:
        """Persiste uma oferta e registra seu preço."""

        oferta = session.scalar(
            select(Oferta).where(
                Oferta.produto_id == produto.id,
                Oferta.item_id_externo
                == data["item_id"],
            )
        )

        now = datetime.now(timezone.utc)

        if oferta is None:
            oferta = Oferta(
                produto_id=produto.id,
                item_id_externo=data["item_id"],
                vendedor=data.get("seller_id"),
                vendedor_id_externo=data.get(
                    "seller_id"
                ),
                loja_oficial_id=data.get(
                    "loja_oficial_id"
                ),
                url_oferta=data["url_oferta"],
                frete_gratis=data.get(
                    "frete_gratis",
                    False,
                ),
                moeda=data.get(
                    "moeda",
                    "BRL",
                ),
                criado_em=now,
                atualizado_em=now,
            )

            session.add(oferta)
            session.flush()

        else:
            oferta.vendedor_id_externo = data.get(
                "seller_id"
            )
            oferta.loja_oficial_id = data.get(
                "loja_oficial_id"
            )
            oferta.url_oferta = data["url_oferta"]
            oferta.frete_gratis = data.get(
                "frete_gratis",
                False,
            )
            oferta.atualizado_em = now

        current_price = Decimal(
            str(data["preco"])
        )

        original_price = data.get(
            "preco_original"
        )

        if original_price is not None:
            original_price = Decimal(
                str(original_price)
            )

        previous_price = session.scalar(
            select(Preco)
            .where(
                Preco.oferta_id == oferta.id
            )
            .order_by(
                Preco.coletado_em.desc()
            )
            .limit(1)
        )

        preco = Preco(
            oferta_id=oferta.id,
            preco=current_price,
            preco_original=original_price,
            desconto_percentual=(
                self._calculate_discount(
                    current_price,
                    original_price,
                )
            ),
            coletado_em=now,
        )

        session.add(preco)

        promotion_data = self._detect_promotion(
            previous_price=(
                previous_price.preco
                if previous_price is not None
                else None
            ),
            current_price=current_price,
            original_price=original_price,
        )

        if promotion_data is None:
            return None

        promotion = Promocao(
            oferta_id=oferta.id,
            preco_anterior=promotion_data[
                "preco_anterior"
            ],
            preco_atual=promotion_data[
                "preco_atual"
            ],
            preco_original=promotion_data[
                "preco_original"
            ],
            desconto_percentual=promotion_data[
                "desconto_percentual"
            ],
            reducao_percentual=promotion_data[
                "reducao_percentual"
            ],
            detectada_em=now,
            status="detectada",
        )

        session.add(promotion)
        session.flush()

        return promotion


    def _detect_promotion(
        self,
        previous_price: Decimal | None,
        current_price: Decimal,
        original_price: Decimal | None,
    ) -> dict | None:
        """Detecta uma promoção com base no histórico de preços."""

        # Primeira coleta:
        # só considera promoção se existir
        # um preço original maior que o preço atual.
        if previous_price is None:
            if (
                original_price is None
                or original_price <= current_price
            ):
                return None

            discount = self._calculate_discount(
                current_price,
                original_price,
            )

            return {
                "preco_anterior": original_price,
                "preco_atual": current_price,
                "preco_original": original_price,
                "desconto_percentual": discount,
                "reducao_percentual": discount,
            }

        # Coletas seguintes:
        # promoção somente quando o preço atual
        # é menor que o último preço registrado.
        if current_price >= previous_price:
            return None

        reduction = self._calculate_discount(
            current_price,
            previous_price,
        )

        discount = self._calculate_discount(
            current_price,
            original_price,
        )

        return {
            "preco_anterior": previous_price,
            "preco_atual": current_price,
            "preco_original": original_price,
            "desconto_percentual": discount,
            "reducao_percentual": reduction,
        }

    @staticmethod
    def _calculate_discount(
        current_price: Decimal,
        original_price: Decimal | None,
    ) -> Decimal | None:
        """Calcula o percentual de desconto."""

        if original_price is None:
            return None

        if original_price <= current_price:
            return Decimal("0.00")

        discount = (
            (original_price - current_price)
            / original_price
        ) * Decimal("100")

        return discount.quantize(
            Decimal("0.01")
        )