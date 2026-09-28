import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4


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


def validar_modo_transporte_executor(
    *,
    permitir_meta: bool = False,
) -> str:
    modo = str(
        settings.whatsapp_transport_mode
        or ""
    ).strip().lower()

    if modo == "meta" and not permitir_meta:
        raise HTTPException(
            status_code=503,
            detail=(
                "Transporte Meta bloqueado no executor. "
                "Use --permitir-meta somente apos "
                "ativacao operacional explicita."
            ),
        )

    return modo


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
        mensagem = (
            "Falha interna no executor "
            "da outbox."
        )

        status_code = 500

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


def adicionar_metadados_operacionais(
    dados: dict,
    *,
    inicio_monotonic: float,
    execucao_id: str,
    executado_em=None,
) -> dict:
    fim_monotonic = perf_counter()

    duracao_ms = max(
        0.0,
        (
            fim_monotonic
            - inicio_monotonic
        )
        * 1000,
    )

    momento = (
        executado_em
        or datetime.now(
            UTC
        )
    )

    return {
        **dados,

        "execucao_id":
            str(
                execucao_id
            ),

        "executado_em_utc":
            momento.isoformat(),

        "duracao_ms":
            round(
                duracao_ms,
                3,
            ),
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

    parser.add_argument(
        "--permitir-meta",
        action="store_true",
        help=(
            "Permite explicitamente o transporte "
            "Meta. Nao usar antes da ativacao real."
        ),
    )

    args = parser.parse_args(
        argv
    )

    inicio_monotonic = perf_counter()

    execucao_id = str(
        uuid4()
    )

    try:
        validar_modo_transporte_executor(
            permitir_meta=
                args.permitir_meta,
        )

        resultado = (
            executar_outbox_whatsapp(
                limite=args.limite
            )
        )

    except Exception as erro:
        fatal = montar_resultado_fatal(
            erro
        )

        fatal = adicionar_metadados_operacionais(
            fatal,
            inicio_monotonic=
                inicio_monotonic,
            execucao_id=
                execucao_id,
        )

        imprimir_json(
            fatal,
            arquivo=sys.stderr,
        )

        return EXIT_FATAL

    resultado = adicionar_metadados_operacionais(
        resultado,
        inicio_monotonic=
            inicio_monotonic,
        execucao_id=
            execucao_id,
    )

    imprimir_json(
        resultado
    )

    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
