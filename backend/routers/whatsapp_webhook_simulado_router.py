from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import SessaoLocal

from services import whatsapp_webhook_service


router = APIRouter(
    tags=["WhatsApp Webhook Simulado"],
)


def get_db():
    db = SessaoLocal()

    try:
        yield db
    finally:
        db.close()


@router.post(
    "/api/webhooks/whatsapp/simulado"
)
def receber_webhook_whatsapp_simulado(
    evento:
        whatsapp_webhook_service
        .EventoWhatsAppSimulado,

    db: Session = Depends(get_db),
):
    return (
        whatsapp_webhook_service
        .processar_evento_whatsapp_simulado(
            db=db,
            evento=evento,
        )
    )
