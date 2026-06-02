import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. O Python procura a URL do banco na nuvem. Se não achar, usa o SQLite local de emergência.
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gesto.db")

# Correção de segurança caso o Render injete a URL com "postgres://" em vez de "postgresql://"
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 2. O SQLite exige uma configuração extra que o PostgreSQL não precisa
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessaoLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()