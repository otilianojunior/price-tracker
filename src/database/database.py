from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import config


engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)