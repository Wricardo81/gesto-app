from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from services import whatsapp_outbound_service
from services import whatsapp_outbox_service
from services import whatsapp_webhook_service


def obter_contexto_outbox(
    *,
    db: Session,
    resultado: dict,
    mensagem_inbound: dict,
) -> dict:
    message_id = str(
        mensagem_inbound.get(
            "message_id",
            "",
        )
        or ""
    ).strip()

    if not message_id:
        raise HTTPException(
            status_code=500,
            detail=(
                "message_id do inbound "
                "nao disponivel para a outbox."
            ),
        )

    provedor = (
        whatsapp_webhook_service
        .PROVEDOR_WHATSAPP_META
    )

    evento = (
        whatsapp_webhook_service
        .buscar_evento_recebido(
            db=db,
            provedor=provedor,
            message_id=message_id,
        )
    )

    if evento is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "Evento inbound processado "
                "nao encontrado."
            ),
        )

    tenant_slug = str(
        evento.barbearia_slug or ""
    ).strip()

    if not tenant_slug:
        raise HTTPException(
            status_code=500,
            detail=(
                "Tenant do evento inbound "
                "nao disponivel."
            ),
        )

    phone_number_id = str(
        resultado.get(
            "phone_number_id",
            "",
        )
        or mensagem_inbound.get(
            "phone_number_id",
            "",
        )
        or evento.phone_number_id
        or ""
    ).strip()

    telefone_cliente = str(
        resultado.get(
            "telefone_cliente",
            "",
        )
        or mensagem_inbound.get(
            "telefone_cliente",
            "",
        )
        or evento.telefone_cliente
        or ""
    ).strip()

    return {
        "provedor":
            provedor,

        "chave_idempotencia":
            message_id,

        "barbearia_slug":
            tenant_slug,

        "phone_number_id":
            phone_number_id,

        "telefone_destino":
            telefone_cliente,
    }


def processar_payload_meta_e_responder(
    *,
    db: Session,
    payload: dict,
    transporte:
        whatsapp_outbound_service
        .TransporteWhatsApp,
) -> dict:
    mensagens_inbound = (
        whatsapp_webhook_service
        .extrair_mensagens_meta(
            payload
        )
    )

    resultado_webhook = (
        whatsapp_webhook_service
        .processar_payload_meta(
            db=db,
            payload=payload,
        )
    )

    resultados = resultado_webhook.get(
        "resultados",
        [],
    )

    envios = []

    for indice, resultado in enumerate(
        resultados
    ):
        if indice >= len(
            mensagens_inbound
        ):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Resultado do webhook sem "
                    "mensagem inbound correspondente."
                ),
            )

        mensagem_inbound = (
            mensagens_inbound[
                indice
            ]
        )

        resposta_booking = resultado.get(
            "resposta"
        )

        texto_saida = (
            whatsapp_outbound_service
            .formatar_resposta_booking_para_texto(
                resposta_booking
            )
        )

        contexto = obter_contexto_outbox(
            db=db,
            resultado=resultado,
            mensagem_inbound=
                mensagem_inbound,
        )

        mensagem_outbox = (
            whatsapp_outbox_service
            .criar_ou_obter_mensagem_outbox(
                db=db,

                provedor=
                    contexto[
                        "provedor"
                    ],

                chave_idempotencia=
                    contexto[
                        "chave_idempotencia"
                    ],

                barbearia_slug=
                    contexto[
                        "barbearia_slug"
                    ],

                phone_number_id=
                    contexto[
                        "phone_number_id"
                    ],

                telefone_destino=
                    contexto[
                        "telefone_destino"
                    ],

                texto=
                    texto_saida,
            )
        )

        envio = (
            whatsapp_outbox_service
            .tentar_entregar_mensagem_outbox(
                db=db,
                mensagem=
                    mensagem_outbox,
                transporte=
                    transporte,
            )
        )

        if not envio.get(
            "idempotente",
            False,
        ):
            envios.append(
                envio
            )

    return {
        "recebido":
            resultado_webhook.get(
                "recebido",
                False,
            ),

        "processados":
            resultado_webhook.get(
                "processados",
                0,
            ),

        "ignorados":
            resultado_webhook.get(
                "ignorados",
                0,
            ),

        "resultados":
            resultados,

        "envios":
            envios,

        "total_envios":
            len(
                envios
            ),
    }
