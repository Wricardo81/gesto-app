import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from database import SessaoLocal
from settings import settings

from services import whatsapp_webhook_service
from services import whatsapp_orquestracao_service
from services import whatsapp_outbound_service


router = APIRouter(
    tags=["WhatsApp Webhook"],
)


def get_db():
    db = SessaoLocal()

    try:
        yield db
    finally:
        db.close()




def get_transporte_whatsapp():
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


@router.get(
    "/api/webhooks/whatsapp/meta",
    response_class=PlainTextResponse,
)
def verificar_webhook_whatsapp_meta(
    request: Request,
):
    desafio = (
        whatsapp_webhook_service
        .validar_challenge_meta(
            mode=request.query_params.get(
                "hub.mode"
            ),

            verify_token_recebido=
                request.query_params.get(
                    "hub.verify_token"
                ),

            challenge=
                request.query_params.get(
                    "hub.challenge"
                ),

            verify_token_configurado=
                settings.whatsapp_verify_token,
        )
    )

    return PlainTextResponse(
        content=desafio,
        status_code=200,
    )

@router.post(
    "/api/webhooks/whatsapp/meta"
)
async def receber_webhook_whatsapp_meta(
    request: Request,
    db: Session = Depends(get_db),
    transporte = Depends(
        get_transporte_whatsapp
    ),
):
    corpo_bruto = await request.body()

    assinatura = request.headers.get(
        "X-Hub-Signature-256"
    )

    whatsapp_webhook_service.validar_assinatura_meta(
        corpo_bruto=corpo_bruto,
        assinatura_recebida=assinatura,
        app_secret=settings.whatsapp_app_secret,
    )

    try:
        payload = json.loads(
            corpo_bruto.decode(
                "utf-8"
            )
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Payload JSON do webhook "
                "WhatsApp invalido."
            ),
        )

    if not isinstance(
        payload,
        dict,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Payload do webhook WhatsApp "
                "deve ser um objeto JSON."
            ),
        )

    return (
        whatsapp_orquestracao_service
        .processar_payload_meta_e_responder(
            db=db,
            payload=payload,
            transporte=transporte,
        )
    )
