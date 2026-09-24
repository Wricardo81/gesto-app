from __future__ import annotations

import hashlib
import hmac
import json

from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models

from services import booking_whatsapp_service
from services import whatsapp_canal_service


PROVEDOR_WHATSAPP_SIMULADO = "simulado"
PROVEDOR_WHATSAPP_META = "meta"


class EventoWhatsAppSimulado(BaseModel):
    message_id: str = Field(
        min_length=1,
        max_length=200,
    )

    phone_number_id: str = Field(
        min_length=1,
        max_length=120,
    )

    telefone_cliente: str = Field(
        min_length=8,
        max_length=30,
    )

    texto: str = Field(
        min_length=1,
        max_length=2000,
    )


def agora_utc_naive() -> datetime:
    return datetime.now(
        UTC
    ).replace(
        tzinfo=None
    )


def validar_assinatura_meta(
    *,
    corpo_bruto: bytes,
    assinatura_recebida: str | None,
    app_secret: str | None,
) -> None:
    segredo = str(
        app_secret or ""
    ).strip()

    if not segredo:
        raise HTTPException(
            status_code=503,
            detail=(
                "WHATSAPP_APP_SECRET "
                "nao configurado."
            ),
        )

    assinatura = str(
        assinatura_recebida or ""
    ).strip()

    prefixo = "sha256="

    if not assinatura.startswith(
        prefixo
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Assinatura do webhook "
                "WhatsApp ausente ou invalida."
            ),
        )

    recebido = assinatura[
        len(prefixo):
    ]

    esperado = hmac.new(
        segredo.encode(
            "utf-8"
        ),
        corpo_bruto,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        recebido,
        esperado,
    ):
        raise HTTPException(
            status_code=401,
            detail=(
                "Assinatura do webhook "
                "WhatsApp invalida."
            ),
        )


def validar_challenge_meta(
    *,
    mode: str | None,
    verify_token_recebido: str | None,
    challenge: str | None,
    verify_token_configurado: str | None,
) -> str:
    token_configurado = str(
        verify_token_configurado or ""
    ).strip()

    if not token_configurado:
        raise HTTPException(
            status_code=503,
            detail=(
                "WHATSAPP_VERIFY_TOKEN "
                "nao configurado."
            ),
        )

    if (
        str(mode or "").strip()
        != "subscribe"
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Modo de verificacao "
                "do webhook invalido."
            ),
        )

    token_recebido = str(
        verify_token_recebido or ""
    )

    if not hmac.compare_digest(
        token_recebido,
        token_configurado,
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Verify token do webhook "
                "invalido."
            ),
        )

    desafio = str(
        challenge or ""
    )

    if not desafio:
        raise HTTPException(
            status_code=400,
            detail=(
                "Challenge do webhook "
                "nao informado."
            ),
        )

    return desafio


def buscar_evento_recebido(
    db: Session,
    *,
    provedor: str,
    message_id: str,
):
    return (
        db.query(
            models.EventoWhatsAppRecebido
        )
        .filter(
            models.EventoWhatsAppRecebido.provedor
            == provedor,

            models.EventoWhatsAppRecebido.message_id
            == message_id,
        )
        .first()
    )


def carregar_resposta_evento(
    evento: models.EventoWhatsAppRecebido,
) -> dict | None:
    if (
        evento.status != "processado"
        or not evento.resposta_json
    ):
        return None

    try:
        return json.loads(
            evento.resposta_json
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=(
                "Resposta idempotente armazenada "
                "esta invalida."
            ),
        )


def criar_registro_evento(
    db: Session,
    *,
    provedor: str,
    evento: EventoWhatsAppSimulado,
):
    telefone_normalizado = (
        booking_whatsapp_service
        .normalizar_telefone_booking(
            evento.telefone_cliente
        )
    )

    registro = models.EventoWhatsAppRecebido(
        provedor=provedor,
        message_id=evento.message_id,
        phone_number_id=evento.phone_number_id,
        telefone_cliente=telefone_normalizado,
        status="processando",
        criado_em=agora_utc_naive(),
    )

    db.add(
        registro
    )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        return None

    db.refresh(
        registro
    )

    return registro

def processar_evento_whatsapp_generico(
    db: Session,
    *,
    provedor: str,
    message_id: str,
    phone_number_id: str,
    telefone_cliente: str,
    texto: str,
) -> dict:
    evento_existente = buscar_evento_recebido(
        db=db,
        provedor=provedor,
        message_id=message_id,
    )

    if evento_existente:
        resposta_existente = (
            carregar_resposta_evento(
                evento_existente
            )
        )

        if resposta_existente is not None:
            resposta_existente[
                "idempotente"
            ] = True

            return resposta_existente

        if evento_existente.status == "processando":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Este evento ja esta sendo "
                    "processado."
                ),
            )

        if evento_existente.status == "erro":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Este evento ja foi recebido "
                    "e terminou com erro."
                ),
            )

    evento_model = EventoWhatsAppSimulado(
        message_id=message_id,
        phone_number_id=phone_number_id,
        telefone_cliente=telefone_cliente,
        texto=texto,
    )

    registro = criar_registro_evento(
        db=db,
        provedor=provedor,
        evento=evento_model,
    )

    if registro is None:
        concorrente = buscar_evento_recebido(
            db=db,
            provedor=provedor,
            message_id=message_id,
        )

        if concorrente:
            resposta_concorrente = (
                carregar_resposta_evento(
                    concorrente
                )
            )

            if resposta_concorrente is not None:
                resposta_concorrente[
                    "idempotente"
                ] = True

                return resposta_concorrente

        raise HTTPException(
            status_code=409,
            detail=(
                "Evento duplicado em processamento."
            ),
        )

    try:
        tenant_slug = (
            whatsapp_canal_service
            .resolver_tenant_por_phone_number_id(
                db=db,
                phone_number_id=phone_number_id,
            )
        )

        registro.barbearia_slug = tenant_slug

        db.commit()

        resposta_booking = (
            booking_whatsapp_service
            .processar_mensagem_booking(
                db=db,
                tenant_slug=tenant_slug,
                telefone_cliente=telefone_cliente,
                mensagem=texto,
            )
        )

        resposta = {
            "recebido": True,
            "idempotente": False,
            "message_id": message_id,
            "tenant_slug": tenant_slug,
            "phone_number_id": phone_number_id,
            "telefone_cliente":
                booking_whatsapp_service
                .normalizar_telefone_booking(
                    telefone_cliente
                ),
            "resposta":
                resposta_booking,
        }

        registro.status = "processado"

        registro.resposta_json = json.dumps(
            resposta,
            ensure_ascii=False,
            default=str,
        )

        registro.processado_em = (
            agora_utc_naive()
        )

        registro.erro = None

        db.commit()

        return resposta

    except HTTPException as erro:
        registro.status = "erro"
        registro.erro = str(
            erro.detail
        )
        registro.processado_em = (
            agora_utc_naive()
        )

        db.commit()

        raise

    except Exception as erro:
        registro.status = "erro"
        registro.erro = (
            type(erro).__name__
        )
        registro.processado_em = (
            agora_utc_naive()
        )

        db.commit()

        raise


def processar_evento_whatsapp_simulado(
    db: Session,
    evento: EventoWhatsAppSimulado,
) -> dict:
    return processar_evento_whatsapp_generico(
        db=db,
        provedor=PROVEDOR_WHATSAPP_SIMULADO,
        message_id=evento.message_id,
        phone_number_id=evento.phone_number_id,
        telefone_cliente=evento.telefone_cliente,
        texto=evento.texto,
    )


def extrair_mensagens_meta(
    payload: dict,
) -> list[dict]:
    mensagens_extraidas = []

    entries = payload.get(
        "entry",
        []
    )

    if not isinstance(
        entries,
        list,
    ):
        return mensagens_extraidas

    for entry in entries:
        if not isinstance(
            entry,
            dict,
        ):
            continue

        changes = entry.get(
            "changes",
            []
        )

        if not isinstance(
            changes,
            list,
        ):
            continue

        for change in changes:
            if not isinstance(
                change,
                dict,
            ):
                continue

            value = change.get(
                "value",
                {}
            )

            if not isinstance(
                value,
                dict,
            ):
                continue

            metadata = value.get(
                "metadata",
                {}
            )

            if not isinstance(
                metadata,
                dict,
            ):
                metadata = {}

            phone_number_id = str(
                metadata.get(
                    "phone_number_id",
                    ""
                )
                or ""
            ).strip()

            messages = value.get(
                "messages",
                []
            )

            if not isinstance(
                messages,
                list,
            ):
                continue

            for message in messages:
                if not isinstance(
                    message,
                    dict,
                ):
                    continue

                message_id = str(
                    message.get(
                        "id",
                        ""
                    )
                    or ""
                ).strip()

                telefone_cliente = str(
                    message.get(
                        "from",
                        ""
                    )
                    or ""
                ).strip()

                tipo = str(
                    message.get(
                        "type",
                        ""
                    )
                    or ""
                ).strip().lower()

                if tipo != "text":
                    continue

                text = message.get(
                    "text",
                    {}
                )

                if not isinstance(
                    text,
                    dict,
                ):
                    continue

                corpo = str(
                    text.get(
                        "body",
                        ""
                    )
                    or ""
                ).strip()

                if (
                    not phone_number_id
                    or not message_id
                    or not telefone_cliente
                    or not corpo
                ):
                    continue

                mensagens_extraidas.append(
                    {
                        "message_id":
                            message_id,

                        "phone_number_id":
                            phone_number_id,

                        "telefone_cliente":
                            telefone_cliente,

                        "texto":
                            corpo,
                    }
                )

    return mensagens_extraidas


def processar_payload_meta(
    db: Session,
    payload: dict,
) -> dict:
    mensagens = extrair_mensagens_meta(
        payload
    )

    resultados = []

    for mensagem in mensagens:
        resultado = (
            processar_evento_whatsapp_generico(
                db=db,
                provedor=PROVEDOR_WHATSAPP_META,
                message_id=mensagem[
                    "message_id"
                ],
                phone_number_id=mensagem[
                    "phone_number_id"
                ],
                telefone_cliente=mensagem[
                    "telefone_cliente"
                ],
                texto=mensagem[
                    "texto"
                ],
            )
        )

        resultados.append(
            resultado
        )

    return {
        "recebido": True,
        "processados":
            len(resultados),

        "ignorados":
            0
            if resultados
            else 1,

        "resultados":
            resultados,
    }
