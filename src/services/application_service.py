from src.auth.mercado_livre_browser import MercadoLivreBrowser
from src.auth.exceptions import (
    MercadoLivreLoginRequiredError,
    MercadoLivreNetworkError,
)
from src.collectors.mercado_livre import MercadoLivreCollector
from src.database.database import SessionLocal
from src.database.models import (
    Categoria,
    Produto,
    RotacaoColeta,
)
from src.notifications.service import NotificationService
from src.services.affiliate_link_service import AffiliateLinkService
from src.services.execution_service import ExecutionService
from src.services.mercado_livre_affiliate import MercadoLivreAffiliateClient
from src.services.mercado_livre_service import MercadoLivreService
from src.services.publication_service import PublicationService


class ApplicationService:
    """Ponto central de execução da aplicação."""

    def __init__(self):
        self.execution = ExecutionService()

        affiliate_client = MercadoLivreAffiliateClient()

        self.publication = PublicationService(
            affiliate_link_service=AffiliateLinkService(
                affiliate_client=affiliate_client,
            ),
            notification_service=NotificationService(),
        )

    def run(
        self,
        categorias: list[str] | None = None,
    ):
        """Executa uma rodada do sistema."""

        if categorias is None:
            categorias_ativas = (
                MercadoLivreService()
                .get_active_categories()
            )

            categorias = [
                categoria["slug"]
                for categoria in categorias_ativas
            ]

        print("=" * 60)
        print("INICIANDO RODADA DO PRICE TRACKER")
        print("=" * 60)

        resultado = self.execution.run(
            lambda: self._run(
                categorias=categorias,
            )
        )

        print("=" * 60)
        print("RODADA FINALIZADA")
        print("=" * 60)

        return resultado

    def _get_rotation_position(
        self,
        categoria_slug: str,
    ) -> int:
        """Retorna a próxima posição de coleta da categoria."""

        with SessionLocal() as session:
            categoria = (
                session.query(Categoria)
                .filter(
                    Categoria.slug == categoria_slug,
                    Categoria.ativa.is_(True),
                )
                .first()
            )

            if not categoria:
                raise ValueError(
                    f"Categoria ativa '{categoria_slug}' "
                    f"não encontrada."
                )

            rotacao = (
                session.query(RotacaoColeta)
                .filter(
                    RotacaoColeta.categoria_id == categoria.id
                )
                .first()
            )

            if not rotacao:
                rotacao = RotacaoColeta(
                    categoria_id=categoria.id,
                    proxima_posicao=1,
                )

                session.add(rotacao)
                session.commit()

                return 1

            return rotacao.proxima_posicao

    def _advance_rotation_position(
        self,
        categoria_slug: str,
    ) -> None:
        """Avança para o próximo bloco de produtos."""

        with SessionLocal() as session:
            categoria = (
                session.query(Categoria)
                .filter(
                    Categoria.slug == categoria_slug,
                    Categoria.ativa.is_(True),
                )
                .first()
            )

            if not categoria:
                raise ValueError(
                    f"Categoria ativa '{categoria_slug}' "
                    f"não encontrada."
                )

            rotacao = (
                session.query(RotacaoColeta)
                .filter(
                    RotacaoColeta.categoria_id == categoria.id
                )
                .first()
            )

            if not rotacao:
                rotacao = RotacaoColeta(
                    categoria_id=categoria.id,
                    proxima_posicao=11,
                )

                session.add(rotacao)

            elif rotacao.proxima_posicao == 1:
                rotacao.proxima_posicao = 11

            else:
                rotacao.proxima_posicao = 1

            session.commit()

    def _get_products_for_monitoring(
        self,
        limit: int = 10,
    ) -> list[dict]:
        """Seleciona produtos conhecidos que estão há mais tempo sem verificação."""

        with SessionLocal() as session:
            produtos = (
                session.query(
                    Produto,
                    Categoria.slug,
                )
                .join(
                    Categoria,
                    Categoria.id == Produto.categoria_id,
                )
                .filter(
                    Produto.ativo.is_(True),
                    Categoria.ativa.is_(True),
                )
                .order_by(
                    Produto.ultima_verificacao_em.asc().nulls_first(),
                    Produto.id.asc(),
                )
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": produto.id,
                    "produto_id_externo": (
                        produto.produto_id_externo
                    ),
                    "nome": produto.nome,
                    "categoria_slug": categoria_slug,
                    "ultima_verificacao_em": (
                        produto.ultima_verificacao_em
                    ),
                }
                for produto, categoria_slug in produtos
            ]

    def _mark_product_verified(
        self,
        product_id: int,
    ) -> None:
        """Registra que um produto conhecido foi verificado com sucesso."""

        from datetime import datetime, timezone

        with SessionLocal() as session:
            produto = session.get(
                Produto,
                product_id,
            )

            if produto is None:
                return

            produto.ultima_verificacao_em = datetime.now(
                timezone.utc
            )

            session.commit()

    def _monitor_known_products(
        self,
        collector: MercadoLivreCollector,
        mercado_livre_service: MercadoLivreService,
        limit: int = 10,
    ) -> list[int]:
        """Monitora produtos já conhecidos e retorna novas promoções."""

        produtos = self._get_products_for_monitoring(
            limit=limit
        )

        print()
        print(
            f"Iniciando monitoramento de "
            f"{len(produtos)} produtos conhecidos..."
        )

        promotion_ids = []

        for produto in produtos:
            print()
            print(
                f"Monitorando produto "
                f"{produto['produto_id_externo']}: "
                f"{produto['nome']}"
            )

            try:
                dados = collector.collect_product(
                    produto["produto_id_externo"],
                    produto["categoria_slug"],
                )

                if not dados["ofertas"]:
                    self._mark_product_verified(
                        produto["id"]
                    )

                    print(
                        "  Produto sem oferta disponível."
                    )
                    print(
                        "  Verificação registrada."
                    )
                    continue

                promotions = (
                    mercado_livre_service
                    .process_category([dados])
                )

                promotion_ids.extend(
                    promotions
                )

                print(
                    f"  Monitoramento concluído: "
                    f"{len(promotions)} promoções detectadas."
                )

            except (
                MercadoLivreLoginRequiredError,
                MercadoLivreNetworkError,
            ):
                raise

            except Exception as erro:
                print(
                    f"  ERRO no monitoramento: {erro}"
                )
                print(
                    "  Continuando para o próximo produto..."
                )

        print()
        print(
            "Monitoramento de produtos conhecidos "
            "concluído."
        )
        print(
            f"Promoções detectadas no monitoramento: "
            f"{len(promotion_ids)}"
        )

        return promotion_ids

    def _run(
        self,
        categorias: list[str],
    ):
        """Executa as etapas internas da aplicação."""

        print("Verificando sessão do Mercado Livre...")

        sessao = MercadoLivreBrowser().check_session()

        print("Sessão do Mercado Livre válida.")

        collector = MercadoLivreCollector(
            max_products_per_category=10
        )

        mercado_livre_service = MercadoLivreService()

        total_produtos_coletados = 0
        total_promocoes_detectadas = 0
        promocoes_para_publicacao = []

        for categoria in categorias:
            print()
            print(
                f"Iniciando coleta da categoria: "
                f"{categoria}"
            )

            try:
                start_position = self._get_rotation_position(
                    categoria
                )

                print(
                    f"Bloco de coleta: posições "
                    f"{start_position}-"
                    f"{start_position + 9}"
                )

                dados = collector.collect(
                    categoria,
                    start_position=start_position,
                )

                total_produtos_coletados += len(dados)

                print(
                    f"Coleta concluída: "
                    f"{len(dados)} produtos."
                )

                for item in dados:
                    produto = item["produto"]
                    ofertas = item["ofertas"]

                    print(
                        f"- {produto['produto_id_externo']}: "
                        f"{produto['nome']}"
                    )

                    print(
                        f"  Ofertas: {len(ofertas)}"
                    )

                print(
                    f"Persistindo dados da categoria "
                    f"{categoria}..."
                )

                promotions = (
                    mercado_livre_service
                    .process_category(dados)
                )

                total_promocoes_detectadas += len(
                    promotions
                )

                promocoes_para_publicacao.extend(
                    promotions
                )

                print(
                    f"Persistência concluída: "
                    f"{len(promotions)} promoções "
                    f"detectadas."
                )

                self._advance_rotation_position(
                    categoria
                )

                print(
                    f"Rotação atualizada: próxima coleta "
                    f"após bloco {start_position}-"
                    f"{start_position + 9}."
                )

            except (
                MercadoLivreLoginRequiredError,
                MercadoLivreNetworkError,
            ):
                raise

            except Exception as erro:
                print()
                print(
                    f"ERRO na categoria "
                    f"{categoria}: {erro}"
                )
                print(
                    "Cursor da categoria não será avançado."
                )
                print(
                    "Continuando para a próxima categoria..."
                )

        print()
        print(
            "Iniciando monitoramento de produtos conhecidos..."
        )

        try:
            promocoes_monitoramento = (
                self._monitor_known_products(
                    collector=collector,
                    mercado_livre_service=mercado_livre_service,
                    limit=10,
                )
            )

            total_promocoes_detectadas += len(
                promocoes_monitoramento
            )

            promocoes_para_publicacao.extend(
                promocoes_monitoramento
            )

            print(
                f"Monitoramento adicionou "
                f"{len(promocoes_monitoramento)} "
                f"promoções à fila de publicação."
            )

        except (
            MercadoLivreLoginRequiredError,
            MercadoLivreNetworkError,
        ):
            raise

        except Exception as erro:
            print()
            print(
                f"ERRO no monitoramento de produtos "
                f"conhecidos: {erro}"
            )
            print(
                "Continuando para a etapa de publicação..."
            )

        print()
        print(
            "Verificando promoções detectadas nesta rodada..."
        )

        promocao_ids = list(
            dict.fromkeys(
                promocoes_para_publicacao
            )
        )

        print(
            f"Promoções detectadas nesta rodada: "
            f"{len(promocao_ids)}"
        )

        publicacoes_preparadas = []

        with SessionLocal() as session:
            for promocao_id in promocao_ids:
                try:
                    print(
                        f"Preparando promoção "
                        f"{promocao_id}..."
                    )

                    promotion_data = (
                        mercado_livre_service
                        .prepare_promotion_for_publication(
                            session=session,
                            promocao_id=promocao_id,
                        )
                    )

                    publicacao = (
                        self.publication.prepare_publication(
                            session=session,
                            promotion_data=promotion_data,
                        )
                    )

                    publicacoes_preparadas.append(
                        publicacao.id
                    )

                    print(
                        f"Publicação preparada: "
                        f"{publicacao.id} "
                        f"| promoção: {promocao_id}"
                    )

                    print(
                        f"Publicando publicação "
                        f"{publicacao.id}..."
                    )

                    publicacao = self.publication.publish(
                        session=session,
                        publicacao_id=publicacao.id,
                    )

                    promocao = session.get(
                        Promocao,
                        promocao_id,
                    )

                    if promocao is not None:
                        promocao.status = "publicada"
                        session.commit()

                    print(
                        f"Publicação concluída: "
                        f"{publicacao.id} "
                        f"| status: {publicacao.status} "
                        f"| mensagem: "
                        f"{publicacao.mensagem_externa_id}"
                    )

                except Exception as erro:
                    print()
                    print(
                        f"ERRO na promoção "
                        f"{promocao_id}: {erro}"
                    )
                    print(
                        "Continuando para a próxima promoção..."
                    )

        return {
            "status": "ok",
            "categorias": categorias,
            "sessao_mercado_livre": sessao,
            "produtos_coletados": total_produtos_coletados,
            "promocoes_detectadas": (
                total_promocoes_detectadas
            ),
            "promocoes_elegiveis": len(
                promocao_ids
            ),
            "publicacoes_preparadas": len(
                publicacoes_preparadas
            ),
        }