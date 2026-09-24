from pathlib import Path
import sys


sys.path.append(
    str(
        Path(__file__)
        .resolve()
        .parents[1]
    )
)


import models
from database import engine


def main():
    models.IntegracaoWhatsAppTenant.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    print(
        "Tabela integracoes_whatsapp pronta."
    )


if __name__ == "__main__":
    main()
