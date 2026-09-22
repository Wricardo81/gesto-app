import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import Base, engine
from models import RepasseProfissional


def main():
    RepasseProfissional.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    print("Tabela repasses_profissionais verificada com sucesso.")


if __name__ == "__main__":
    main()
