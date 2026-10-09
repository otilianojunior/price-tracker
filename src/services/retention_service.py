from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import aliased

from src.database.database import SessionLocal
from src.database.models import Preco


class RetentionService:
    """Gerencia a retenção do histórico de preços."""

    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory

    def cleanup_old_prices(
        self,
        retention_days: int = 7,
        dry_run: bool = True,
    ) -> dict:
        """Remove preços antigos preservando uma referência por oferta."""

        if retention_days < 1:
            raise ValueError(
                "O período de retenção deve ser de pelo menos 1 dia."
            )

        cutoff = datetime.now(timezone.utc) - timedelta(
            days=retention_days
        )

        preco_antigo = aliased(Preco)

        ultimo_preco_antigo = (
            select(preco_antigo.id)
            .where(
                preco_antigo.oferta_id == Preco.oferta_id,
                preco_antigo.coletado_em < cutoff,
            )
            .order_by(
                preco_antigo.coletado_em.desc(),
                preco_antigo.id.desc(),
            )
            .limit(1)
            .correlate(Preco)
            .scalar_subquery()
        )

        precos_excluiveis = (
            select(Preco.id)
            .where(
                Preco.coletado_em < cutoff,
                Preco.id != ultimo_preco_antigo,
            )
        )

        with self.session_factory() as session:
            quantidade = session.scalar(
                select(func.count())
                .select_from(Preco)
                .where(Preco.id.in_(precos_excluiveis))
            ) or 0

            removidos = 0

            if not dry_run and quantidade:
                try:
                    resultado = session.execute(
                        delete(Preco).where(
                            Preco.id.in_(precos_excluiveis)
                        )
                    )
                    removidos = resultado.rowcount or 0
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

            status = "simulacao" if dry_run else "ok"

            print(
                f"[RETENÇÃO] status={status} "
                f"| limite={retention_days} dias "
                f"| preços antigos excluíveis={quantidade} "
                f"| registros removidos={removidos}"
            )

            return {
                "status": status,
                "registros_antigos": quantidade,
                "registros_removidos": removidos,
                "limite": cutoff,
            }