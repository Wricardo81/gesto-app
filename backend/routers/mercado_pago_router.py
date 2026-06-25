from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from security import (
    obter_saas_admin_logado,
    validar_tenant_logado,
)
from services.mercado_pago_service import (
    buscar_pagamento_mercado_pago,
    criar_preferencia_mercado_pago,
    timestamp_iso_para_datetime,
)
from services.planos_service import obter_plano_assinatura


router = APIRouter(
    tags=["Mercado Pago"],
)


class CriarCheckoutMercadoPago(BaseModel):
    barbearia_id: int
    plano_codigo: str

class CriarCheckoutMercadoPagoAdmin(BaseModel):
    plano_codigo: str


def get_db():
    db = SessaoLocal()

    try:
        yield db

    finally:
        db.close()


def calcular_vencimento_por_plano(
    plano_codigo: str,
):
    plano = obter_plano_assinatura(
        plano_codigo
    )

    return datetime.utcnow().date() + timedelta(
        days=30 * plano.meses
    )


@router.post("/api/saas/mercado-pago/checkout")
def criar_checkout_mercado_pago_saas(
    dados: CriarCheckoutMercadoPago,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    barbearia = (
        db.query(models.Barbearia)
        .filter(
            models.Barbearia.id == dados.barbearia_id
        )
        .first()
    )

    if not barbearia:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada.",
        )

    plano = obter_plano_assinatura(
        dados.plano_codigo
    )

    preferencia = criar_preferencia_mercado_pago(
        barbearia_id=barbearia.id,
        tenant_slug=barbearia.slug,
        nome_empresa=barbearia.nome,
        email_empresa=barbearia.email,
        plano_codigo=plano.codigo,
    )

    checkout_url = (
        preferencia.get("init_point")
        or preferencia.get("sandbox_init_point")
    )

    if not checkout_url:
        raise HTTPException(
            status_code=500,
            detail="Mercado Pago não retornou URL de checkout.",
        )

    barbearia.gateway_pagamento = "mercado_pago"
    barbearia.plano_codigo = plano.codigo
    barbearia.plano_periodicidade = plano.periodicidade
    barbearia.valor_mensal = plano.valor_mensal_equivalente
    barbearia.status_assinatura = "checkout_mercado_pago_criado"
    barbearia.status_pagamento = "pendente"

    db.commit()
    db.refresh(barbearia)

    return {
        "mensagem": "Checkout Mercado Pago criado com sucesso.",
        "checkout_url": checkout_url,
        "preference_id": preferencia.get("id"),
        "empresa": {
            "id": barbearia.id,
            "nome": barbearia.nome,
            "slug": barbearia.slug,
            "gateway_pagamento": barbearia.gateway_pagamento,
            "plano_codigo": barbearia.plano_codigo,
            "status_assinatura": barbearia.status_assinatura,
            "status_pagamento": barbearia.status_pagamento,
        },
    }


@router.post("/api/{tenant_slug}/admin/assinaturas/mercado-pago/checkout")
def criar_checkout_mercado_pago_admin(
    tenant_slug: str,
    dados: CriarCheckoutMercadoPagoAdmin,
    db: Session = Depends(get_db),
    _tenant_logado: str = Depends(validar_tenant_logado),
):
    if tenant_slug != _tenant_logado:
        raise HTTPException(
            status_code=403,
            detail="Tenant inválido para esta sessão.",
        )

    barbearia = (
        db.query(models.Barbearia)
        .filter(models.Barbearia.slug == tenant_slug)
        .first()
    )

    if not barbearia:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada.",
        )

    status_assinatura = (
        barbearia.status_assinatura
        or ""
    ).strip().lower()

    if status_assinatura == "desativada":
        raise HTTPException(
            status_code=403,
            detail=(
                "Esta empresa foi desativada pela administração da plataforma. "
                "Somente o Painel Mestre pode reativar o acesso."
            ),
        )

    plano = obter_plano_assinatura(
        dados.plano_codigo
    )

    preferencia = criar_preferencia_mercado_pago(
        barbearia_id=barbearia.id,
        tenant_slug=barbearia.slug,
        nome_empresa=barbearia.nome,
        email_empresa=barbearia.email,
        plano_codigo=plano.codigo,
    )

    checkout_url = (
        preferencia.get("init_point")
        or preferencia.get("sandbox_init_point")
    )

    if not checkout_url:
        raise HTTPException(
            status_code=500,
            detail="Mercado Pago não retornou URL de checkout.",
        )

    barbearia.gateway_pagamento = "mercado_pago"
    barbearia.plano_codigo = plano.codigo
    barbearia.plano_periodicidade = plano.periodicidade
    barbearia.valor_mensal = plano.valor_mensal_equivalente
    barbearia.status_assinatura = "checkout_mercado_pago_criado"
    barbearia.status_pagamento = "pendente"

    db.commit()
    db.refresh(barbearia)

    return {
        "mensagem": "Checkout Mercado Pago criado com sucesso.",
        "checkout_url": checkout_url,
        "preference_id": preferencia.get("id"),
        "barbearia_id": barbearia.id,
        "plano_codigo": plano.codigo,
    }




@router.post("/api/webhooks/mercado-pago")
async def webhook_mercado_pago(
    request: Request,
    db: Session = Depends(get_db),
):
    payload = await request.json()

    tipo = payload.get("type") or payload.get("topic")
    data = payload.get("data") or {}

    payment_id = (
        data.get("id")
        or payload.get("id")
        or payload.get("resource")
    )

    if tipo not in {
        "payment",
        "payments",
    }:
        return {
            "recebido": True,
            "ignorado": True,
            "motivo": "Evento não tratado nesta sprint.",
        }

    if not payment_id:
        return {
            "recebido": True,
            "ignorado": True,
            "motivo": "Payment ID ausente.",
        }

    pagamento = buscar_pagamento_mercado_pago(
        str(payment_id)
    )

    metadata = pagamento.get("metadata") or {}
    external_reference = pagamento.get("external_reference") or ""

    barbearia_id = metadata.get("barbearia_id")

    if not barbearia_id and external_reference.startswith("barbearia:"):
        partes = external_reference.split(":")

        if len(partes) >= 2:
            barbearia_id = partes[1]

    if not barbearia_id:
        return {
            "recebido": True,
            "ignorado": True,
            "motivo": "barbearia_id ausente.",
        }

    barbearia = (
        db.query(models.Barbearia)
        .filter(
            models.Barbearia.id == int(barbearia_id)
        )
        .first()
    )

    if not barbearia:
        return {
            "recebido": True,
            "ignorado": True,
            "motivo": "Empresa não encontrada.",
        }
    
    status_assinatura_atual = (
        barbearia.status_assinatura
        or ""
    ).strip().lower()

    if status_assinatura_atual == "desativada":
        return {
            "recebido": True,
            "ignorado": True,
            "motivo": "Empresa desativada manualmente pelo SaaS Master.",
        }

    plano_codigo = (
        metadata.get("plano_codigo")
        or barbearia.plano_codigo
    )

    status = pagamento.get("status")

    barbearia.gateway_pagamento = "mercado_pago"
    barbearia.ultima_cobranca_status = status

    if status == "approved":
        barbearia.status_pagamento = "em_dia"
        barbearia.status_assinatura = "mercado_pago_aprovado"
        barbearia.plano_ativo = True
        barbearia.ultimo_pagamento_em = datetime.utcnow()
        barbearia.vencimento_plano = calcular_vencimento_por_plano(
            plano_codigo
        )

        data_aprovacao = timestamp_iso_para_datetime(
            pagamento.get("date_approved")
        )

        if data_aprovacao:
            barbearia.assinatura_iniciada_em = data_aprovacao

    elif status in {
        "pending",
        "in_process",
    }:
        barbearia.status_pagamento = "pendente"
        barbearia.status_assinatura = "mercado_pago_pendente"

    elif status in {
        "rejected",
        "cancelled",
        "refunded",
        "charged_back",
    }:
        barbearia.status_pagamento = "cancelado"
        barbearia.status_assinatura = f"mercado_pago_{status}"

    db.commit()

    return {
        "recebido": True,
        "status": status,
        "barbearia_id": barbearia.id,
    }