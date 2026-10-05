from src.database.database import engine
from src.database.models import Base


def init_db():
    Base.metadata.create_all(engine)
    print("Banco de dados inicializado com sucesso.")


if __name__ == "__main__":
    init_db()