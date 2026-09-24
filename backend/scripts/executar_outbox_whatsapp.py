import argparse
import json
import sys
from pathlib import Path


from fastapi import HTTPException


BACKEND_DIR = Path(
    __file__
).resolve().parents[1]

if str(
    BACKEND_DIR
) not in sys.path:
    sys.path.insert(
        0,
        str(
            BACKEND_DIR
        ),
    )


from database import SessaoLocal
from settings import settings

from services import whatsapp_outbound_service
from services import whatsapp_outbox_service


STATUS_HEALTHY = "healthy"
STATUS_PARTIAL = "partial"
STATUS_FATAL = "fatal"

EXIT_OK = 0
EXIT_FATAL = 2


def criar_transporte_configurado():
    return (
        whatsapp_outbound_service
        .criar_transporte_whatsapp(
            modo=
                settings.whatsapp_transport_mode,

            access_token=
                settings.whatsapp_access_token,

            graph_api_version=
                settings.whatsapp_graph_api_version,

            base_url=
                settings.whatsapp_graph_api_base_url,

            timeout_seconds=
                settings.whatsapp_http_timeout_seconds,
        )
    )


def classificar_status_operacional(
    resultado: dict,
) -> str:
    falhas = int(
        resultado.get(
            "falhas",
            0,
        )
        or 0
    )

    if falhas > 0:
        return STATUS_PARTIAL

    return STATUS_HEALTHY


def executar_outbox_whatsapp(
    *,
    limite: int = 50,
    session_factory=SessaoLocal,
    transporte=None,
) -> dict:
    db = session_factory()

    try:
        transporte_efetivo = (
            transporte
            or criar_transporte_configurado()
        )

        resultado = (
            whatsapp_outbox_service
            .processar_lote_outbox(
                db,
                transporte=
                    transporte_efetivo,
                limite=limite,
            )
        )

        status_operacional = (
            classificar_status_operacional(
                resultado
            )
        )

        return {
            "executor":
                "whatsapp_outbox",

            "status_operacional":
                status_operacional,

            "modo_transporte":
                str(
                    settings
                    .whatsapp_transport_mode
                    or ""
                ).strip().lower(),

            "limite":
                limite,

            **resultado,
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def montar_resultado_fatal(
    erro: Exception,
) -> dict:
    status_code = None

    if isinstance(
        erro,
        HTTPException,
    ):
        mensagem = str(
            erro.detail
        )

        status_code = (
            erro.status_code
        )

    else:
        mensagem = str(
            erro
        ).strip()

        if not mensagem:
            mensagem = (
                type(
                    erro
                ).__name__
            )

    return {
        "executor":
            "whatsapp_outbox",

        "status_operacional":
            STATUS_FATAL,

        "modo_transporte":
            str(
                settings
                .whatsapp_transport_mode
                or ""
            ).strip().lower(),

        "erro_tipo":
            type(
                erro
            ).__name__,

        "status_code":
            status_code,

        "erro":
            mensagem,
    }


def imprimir_json(
    dados: dict,
    *,
    arquivo=None,
):
    print(
        json.dumps(
            dados,
            ensure_ascii=False,
            sort_keys=True,
        ),
        file=(
            arquivo
            or sys.stdout
        ),
    )


def main(
    argv=None,
) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Processa um lote recuperavel "
            "da Outbox WhatsApp."
        )
    )

    parser.add_argument(
        "--limite",
        type=int,
        default=50,
        help=(
            "Quantidade maxima de mensagens "
            "a processar. Padrao: 50."
        ),
    )

    args = parser.parse_args(
        argv
    )

    try:
        resultado = (
            executar_outbox_whatsapp(
                limite=args.limite
            )
        )

    except Exception as erro:
        fatal = montar_resultado_fatal(
            erro
        )

        imprimir_json(
            fatal,
            arquivo=sys.stderr,
        )

        return EXIT_FATAL

    imprimir_json(
        resultado
    )

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
