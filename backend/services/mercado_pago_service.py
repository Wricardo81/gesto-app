from datetime import datetime
from typing import Any

import requests
from fastapi import HTTPException

from services.planos_service import obter_plano_assinatura
from settings import settings


MERCADO_PAGO_API_BASE = "https://api.mercadopago.com"


def obter_access_token_mercado_pago() -> str:
    token = settings.mercado_pago_access_token

    if not token:
        raise HTTPException(
            status_code=400,
            detail="MERCADO_PAGO_ACCESS_TOKEN não configurado no .env.",
        )

    token = token.strip()

    if not token:
        raise HTTPException(
            status_code=400,
            detail="MERCADO_PAGO_ACCESS_TOKEN não configurado no .env.",
        )

    return token


def montar_headers_mercado_pago() -> dict:
    return {
        "Authorization": f"Bearer {obter_access_token_mercado_pago()}",
        "Content-Type": "application/json",
    }


def criar_preferencia_mercado_pago(
    *,
    barbearia_id: int,
    tenant_slug: str,
    nome_empresa: str,
    email_empresa: str | None,
    plano_codigo: str,
) -> dict:
    plano = obter_plano_assinatura(
        plano_codigo
    )

    frontend_base_url = settings.frontend_base_url.rstrip("/")

    back_urls = {
        "success": (
            f"{frontend_base_url}/saas.html"
            f"?mercado_pago=sucesso"
            f"&empresa_id={barbearia_id}"
        ),
        "failure": (
            f"{frontend_base_url}/saas.html"
            f"?mercado_pago=falha"
            f"&empresa_id={barbearia_id}"
        ),
        "pending": (
            f"{frontend_base_url}/saas.html"
            f"?mercado_pago=pendente"
            f"&empresa_id={barbearia_id}"
        ),
    }

    metadata = {
        "barbearia_id": str(barbearia_id),
        "tenant_slug": tenant_slug,
        "plano_codigo": plano.codigo,
        "gateway_pagamento": "mercado_pago",
    }

    payload: dict[str, Any] = {
        "items": [
            {
                "id": plano.codigo,
                "title": f"Gesto App - {plano.nome}",
                "description": (
                    f"Assinatura {plano.periodicidade} do Gesto App "
                    f"para {nome_empresa}"
                ),
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(plano.valor_total),
            }
        ],
        "payer": {
            "email": email_empresa or "",
            "name": nome_empresa,
        },
        "back_urls": back_urls,
        "auto_return": "approved",
        "external_reference": f"barbearia:{barbearia_id}:plano:{plano.codigo}",
        "metadata": metadata,
    }

    if settings.mercado_pago_notification_url:
        payload["notification_url"] = settings.mercado_pago_notification_url

    resposta = requests.post(
        f"{MERCADO_PAGO_API_BASE}/checkout/preferences",
        headers=montar_headers_mercado_pago(),
        json=payload,
        timeout=20,
    )

    try:
        dados = resposta.json()

    except Exception:
        dados = {
            "raw": resposta.text,
        }

    if resposta.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail={
                "mensagem": "Erro ao criar preferência no Mercado Pago.",
                "mercado_pago": dados,
            },
        )

    return dados


def buscar_pagamento_mercado_pago(
    payment_id: str,
) -> dict:
    resposta = requests.get(
        f"{MERCADO_PAGO_API_BASE}/v1/payments/{payment_id}",
        headers=montar_headers_mercado_pago(),
        timeout=20,
    )

    try:
        dados = resposta.json()

    except Exception:
        dados = {
            "raw": resposta.text,
        }

    if resposta.status_code >= 400:
        raise HTTPException(
            status_code=400,
            detail={
                "mensagem": "Erro ao buscar pagamento no Mercado Pago.",
                "mercado_pago": dados,
            },
        )

    return dados


def timestamp_iso_para_datetime(
    valor: str | None,
) -> datetime | None:
    if not valor:
        return None

    try:
        return datetime.fromisoformat(
            valor.replace("Z", "+00:00")
        ).replace(tzinfo=None)

    except Exception:
        return None