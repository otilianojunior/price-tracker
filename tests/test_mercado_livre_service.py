from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.services.mercado_livre_service import MercadoLivreService


@pytest.fixture
def service():
    return MercadoLivreService()


@pytest.fixture
def session():
    return Mock()


def make_publication(preco, horas_atras=1):
    return SimpleNamespace(
        publicado_em=(
            datetime.now(timezone.utc)
            - timedelta(hours=horas_atras)
        ),
        preco_publicado=Decimal(str(preco)),
    )


def test_pode_publicar_quando_nunca_foi_publicada(
    service, session
):
    session.scalar.return_value = None

    resultado = service.can_publish_offer(
        session=session,
        oferta_id=1,
        canal_id=2,
        novo_preco=Decimal("100.00"),
    )

    assert resultado is True


def test_bloqueia_preco_igual_dentro_de_24_horas(
    service, session
):
    session.scalar.return_value = make_publication("100.00")

    resultado = service.can_publish_offer(
        session=session,
        oferta_id=1,
        canal_id=2,
        novo_preco=Decimal("100.00"),
    )

    assert resultado is False


def test_permite_preco_menor_dentro_de_24_horas(
    service, session
):
    session.scalar.return_value = make_publication("100.00")

    resultado = service.can_publish_offer(
        session=session,
        oferta_id=1,
        canal_id=2,
        novo_preco=Decimal("90.00"),
    )

    assert resultado is True


def test_bloqueia_preco_maior_dentro_de_24_horas(
    service, session
):
    session.scalar.return_value = make_publication("100.00")

    resultado = service.can_publish_offer(
        session=session,
        oferta_id=1,
        canal_id=2,
        novo_preco=Decimal("110.00"),
    )

    assert resultado is False


def test_permite_preco_igual_apos_24_horas(
    service, session
):
    session.scalar.return_value = make_publication(
        "100.00",
        horas_atras=25,
    )

    resultado = service.can_publish_offer(
        session=session,
        oferta_id=1,
        canal_id=2,
        novo_preco=Decimal("100.00"),
    )

    assert resultado is True


def test_permite_preco_maior_apos_24_horas(
    service, session
):
    session.scalar.return_value = make_publication(
        "100.00",
        horas_atras=25,
    )

    resultado = service.can_publish_offer(
        session=session,
        oferta_id=1,
        canal_id=2,
        novo_preco=Decimal("110.00"),
    )

    assert resultado is True


def test_bloqueia_quando_preco_publicado_e_nulo(
    service, session
):
    session.scalar.return_value = SimpleNamespace(
        publicado_em=(
            datetime.now(timezone.utc)
            - timedelta(hours=1)
        ),
        preco_publicado=None,
    )

    resultado = service.can_publish_offer(
        session=session,
        oferta_id=1,
        canal_id=2,
        novo_preco=Decimal("90.00"),
    )

    assert resultado is False


def test_permite_preco_menor_apos_24_horas(
    service, session
):
    session.scalar.return_value = make_publication(
        "100.00",
        horas_atras=25,
    )

    resultado = service.can_publish_offer(
        session=session,
        oferta_id=1,
        canal_id=2,
        novo_preco=Decimal("90.00"),
    )

    assert resultado is True


def test_retorna_none_quando_nao_ha_promocoes(
    service, session
):
    session.scalars.return_value.all.return_value = []

    resultado = service.select_best_promotion_for_product(
        session=session,
        produto_id=1,
    )

    assert resultado is None


def test_seleciona_promocao_com_menor_preco(
    service, session
):
    promocao_mais_cara = SimpleNamespace(
        id=1,
        preco_atual=Decimal("150.00"),
        reducao_percentual=Decimal("20.00"),
    )
    promocao_mais_barata = SimpleNamespace(
        id=2,
        preco_atual=Decimal("100.00"),
        reducao_percentual=Decimal("10.00"),
    )
    session.scalars.return_value.all.return_value = [
        promocao_mais_barata,
        promocao_mais_cara,
    ]

    resultado = service.select_best_promotion_for_product(
        session=session,
        produto_id=1,
    )

    assert resultado is promocao_mais_barata


def test_prioriza_maior_reducao_quando_precos_sao_iguais(
    service, session
):
    promocao_menor_reducao = SimpleNamespace(
        id=1,
        preco_atual=Decimal("100.00"),
        reducao_percentual=Decimal("10.00"),
    )
    promocao_maior_reducao = SimpleNamespace(
        id=2,
        preco_atual=Decimal("100.00"),
        reducao_percentual=Decimal("25.00"),
    )
    session.scalars.return_value.all.return_value = [
        promocao_maior_reducao,
        promocao_menor_reducao,
    ]

    resultado = service.select_best_promotion_for_product(
        session=session,
        produto_id=1,
    )

    assert resultado is promocao_maior_reducao


def test_prioriza_promocao_mais_recente_no_desempate(
    service, session
):
    promocao_antiga = SimpleNamespace(
        id=1,
        preco_atual=Decimal("100.00"),
        reducao_percentual=Decimal("20.00"),
        detectada_em=datetime(2026, 10, 8, tzinfo=timezone.utc),
    )
    promocao_recente = SimpleNamespace(
        id=2,
        preco_atual=Decimal("100.00"),
        reducao_percentual=Decimal("20.00"),
        detectada_em=datetime(2026, 10, 9, tzinfo=timezone.utc),
    )
    session.scalars.return_value.all.return_value = [
        promocao_recente,
        promocao_antiga,
    ]

    resultado = service.select_best_promotion_for_product(
        session=session,
        produto_id=1,
    )

    assert resultado is promocao_recente


def test_consulta_filtra_e_ordena_promocoes_corretamente(
    service, session
):
    session.scalars.return_value.all.return_value = []

    service.select_best_promotion_for_product(
        session=session,
        produto_id=42,
    )

    consulta = session.scalars.call_args.args[0]
    sql = str(consulta.compile()).lower()

    assert "ofertas.produto_id" in sql
    assert "ofertas.ativo is true" in sql
    assert "promocoes.status" in sql
    assert "order by" in sql
    assert "promocoes.preco_atual asc" in sql
    assert "promocoes.reducao_percentual desc" in sql
    assert "promocoes.detectada_em desc" in sql
