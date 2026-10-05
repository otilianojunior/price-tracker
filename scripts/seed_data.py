from sqlalchemy import select

from src.database.database import SessionLocal
from src.database.models import Categoria, Plataforma


def seed_plataformas(session):
    plataforma = session.scalar(
        select(Plataforma).where(
            Plataforma.codigo == "mercado_livre"
        )
    )

    if plataforma is None:
        session.add(
            Plataforma(
                nome="Mercado Livre",
                codigo="mercado_livre",
                url_base="https://www.mercadolivre.com.br",
            )
        )


def seed_categorias(session):
    categorias = [
        ("Celulares", "celulares"),
        ("Games", "games"),
        ("Informática", "informatica"),
        ("TVs", "tvs"),
        ("Periféricos Gamer", "perifericos-gamer"),
        ("Armazenamento", "armazenamento"),
        ("Componentes de PC", "componentes-pc"),
        ("Monitores", "monitores"),
    ]

    for nome, slug in categorias:
        categoria = session.scalar(
            select(Categoria).where(
                Categoria.slug == slug
            )
        )

        if categoria is None:
            session.add(
                Categoria(
                    nome=nome,
                    slug=slug,
                )
            )


def main():
    with SessionLocal() as session:
        seed_plataformas(session)
        seed_categorias(session)

        session.commit()

    print("Dados iniciais inseridos com sucesso.")


if __name__ == "__main__":
    main()