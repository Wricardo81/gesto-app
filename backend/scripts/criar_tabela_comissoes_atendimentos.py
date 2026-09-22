import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import engine
from models import ComissaoAtendimento


def main():
    ComissaoAtendimento.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    print("Tabela comissoes_atendimentos verificada com sucesso.")


if __name__ == "__main__":
    main()
