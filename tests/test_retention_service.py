from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.database.models import Preco
from src.services.mercado_livre_service import MercadoLivreService
from src.services.retention_service import RetentionService


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Preco.__table__.create(engine)

    factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    yield factory

    engine.dispose()


@pytest.fixture
def service(session_factory):
    return RetentionService(session_factory=session_factory)


def inserir_preco(
    session_factory,
    coletado_em,
    oferta_id=1,
    preco=Decimal("100.00"),
):
    with session_factory() as session:
        session.add(
            Preco(
                oferta_id=oferta_id,
                preco=preco,
                coletado_em=coletado_em,
            )
        )
        session.commit()


def contar_precos(session_factory):
    with session_factory() as session:
        return len(session.scalars(select(Preco)).all())


def test_simulacao_identifica_precos_sem_remove_los(
    service, session_factory
):
    muito_antigo = datetime.now(timezone.utc) - timedelta(days=10)
    antigo = datetime.now(timezone.utc) - timedelta(days=8)
    recente = datetime.now(timezone.utc) - timedelta(days=2)

    inserir_preco(session_factory, muito_antigo, oferta_id=1)
    inserir_preco(session_factory, antigo, oferta_id=1)
    inserir_preco(session_factory, recente, oferta_id=1)

    resultado = service.cleanup_old_prices(
        retention_days=7,
        dry_run=True,
    )

    # O preço antigo mais recente da oferta é preservado.
    assert resultado["registros_antigos"] == 1

    # A simulação identifica o que poderia excluir,
    # mas não apaga nenhum registro.
    assert resultado["registros_removidos"] == 0
    assert contar_precos(session_factory) == 3


def test_remove_precos_com_mais_de_sete_dias(
    service, session_factory
):
    muito_antigo = datetime.now(timezone.utc) - timedelta(days=9)
    antigo = datetime.now(timezone.utc) - timedelta(days=8)
    recente = datetime.now(timezone.utc) - timedelta(days=2)

    inserir_preco(session_factory, muito_antigo)
    inserir_preco(session_factory, antigo)
    inserir_preco(session_factory, recente)

    resultado = service.cleanup_old_prices(dry_run=False)

    assert resultado["registros_antigos"] == 1
    assert resultado["registros_removidos"] == 1
    assert contar_precos(session_factory) == 2


def test_preserva_precos_recentes(service, session_factory):
    recente = datetime.now(timezone.utc) - timedelta(days=2)
    inserir_preco(session_factory, recente)

    resultado = service.cleanup_old_prices(dry_run=False)

    assert resultado["registros_removidos"] == 0
    assert contar_precos(session_factory) == 1


def test_rejeita_periodo_de_retencao_invalido(service):
    with pytest.raises(ValueError):
        service.cleanup_old_prices(retention_days=0)


def test_rejeita_periodo_negativo(service):
    with pytest.raises(ValueError):
        service.cleanup_old_prices(retention_days=-1)


def test_propaga_erro_quando_banco_indisponivel():
    def session_factory_com_erro():
        raise RuntimeError("Banco indisponível")

    service = RetentionService(
        session_factory=session_factory_com_erro,
    )

    with pytest.raises(RuntimeError, match="Banco indisponível"):
        service.cleanup_old_prices(dry_run=True)


def test_preserva_ultima_referencia_de_cada_oferta(
    service, session_factory
):
    oferta_1_antigo = (
        datetime.now(timezone.utc) - timedelta(days=10)
    )
    oferta_1_recente = (
        datetime.now(timezone.utc) - timedelta(days=8)
    )
    oferta_2_antigo = (
        datetime.now(timezone.utc) - timedelta(days=12)
    )
    oferta_2_recente = (
        datetime.now(timezone.utc) - timedelta(days=9)
    )

    inserir_preco(
        session_factory, oferta_1_antigo, oferta_id=1
    )
    inserir_preco(
        session_factory, oferta_1_recente, oferta_id=1
    )
    inserir_preco(
        session_factory, oferta_2_antigo, oferta_id=2
    )
    inserir_preco(
        session_factory, oferta_2_recente, oferta_id=2
    )

    resultado = service.cleanup_old_prices(dry_run=False)

    assert resultado["registros_antigos"] == 2
    assert resultado["registros_removidos"] == 2
    assert contar_precos(session_factory) == 2


def test_retencao_preserva_referencia_para_detectar_queda(
    service,
    session_factory,
):
    agora = datetime.now(timezone.utc)

    inserir_preco(
        session_factory,
        agora - timedelta(days=10),
        preco=Decimal("150.00"),
    )
    inserir_preco(
        session_factory,
        agora - timedelta(days=8),
        preco=Decimal("120.00"),
    )
    inserir_preco(
        session_factory,
        agora - timedelta(days=2),
        preco=Decimal("130.00"),
    )

    resultado = service.cleanup_old_prices(
        retention_days=7,
        dry_run=False,
    )

    assert resultado["registros_removidos"] == 1

    with session_factory() as session:
        ultimo_preco = session.scalar(
            select(Preco)
            .where(Preco.oferta_id == 1)
            .order_by(
                Preco.coletado_em.desc(),
                Preco.id.desc(),
            )
            .limit(1)
        )

        assert ultimo_preco is not None
        assert ultimo_preco.preco == Decimal("130.00")

        promocao = MercadoLivreService()._detect_promotion(
            previous_price=ultimo_preco.preco,
            current_price=Decimal("110.00"),
            original_price=None,
        )

        assert promocao is not None
        assert promocao["preco_anterior"] == Decimal("130.00")
        assert promocao["preco_atual"] == Decimal("110.00")