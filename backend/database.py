from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from settings import settings


def normalizar_database_url(url: str) -> str:
    """
    Normaliza URLs PostgreSQL para utilizar explicitamente
    o driver moderno Psycopg 3 com SQLAlchemy.
    """

    if url.startswith("postgres://"):
        url = url.replace(
            "postgres://",
            "postgresql://",
            1,
        )

    if url.startswith("postgresql://"):
        url = url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    return url


SQLALCHEMY_DATABASE_URL = normalizar_database_url(
    settings.database_url
)

MIGRATION_DATABASE_URL = normalizar_database_url(
    settings.database_direct_url
    or settings.database_url
)


if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={
            "check_same_thread": False,
        },
    )

elif "-pooler." in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        poolclass=NullPool,
    )

else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
    )


SessaoLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


Base = declarative_base()