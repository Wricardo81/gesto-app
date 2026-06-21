from datetime import datetime
from typing import Any
import re

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from security import obter_saas_admin_logado
from services.planos_service import (
    listar_planos_assinatura,
    obter_plano_assinatura,
)
from settings import settings


router = APIRouter(
    tags=["Assinaturas Stripe"],
)


class CriarCheckoutAssinatura(BaseModel):
    barbearia_id: int
    plano_codigo: str


def get_db():
    db = SessaoLocal()

    try:
        yield db

    finally:
        db.close()


def configurar_stripe():
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_SECRET_KEY não configurada.",
        )

    stripe.api_key = settings.stripe_secret_key


def obter_price_id_por_plano(
    plano_codigo: str,
) -> str:
    plano = obter_plano_assinatura(
        plano_codigo
    )

    price_id = getattr(
        settings,
        plano.stripe_price_env,
        None,
    )

    if not price_id:
        raise HTTPException(
            status_code=500,
            detail=f"Price ID do plano {plano.codigo} não configurado no .env.",
        )

    price_id = str(price_id).strip()

    if not re.match(r"^price_[A-Za-z0-9_]+$", price_id):
        raise HTTPException(
            status_code=500,
            detail=(
                f"Price ID inválido para o plano {plano.codigo}. "
                "Use o ID real do Stripe que começa com 'price_', "
                "não o valor em reais."
            ),
        )

    return price_id


def timestamp_para_datetime(
    valor: Any,
) -> datetime | None:
    if not valor:
        return None

    try:
        return datetime.fromtimestamp(
            int(valor)
        )

    except Exception:
        return None


def serializar_plano_empresa(
    barbearia: models.Barbearia,
) -> dict:
    return {
        "id": barbearia.id,
        "nome": barbearia.nome,
        "slug": barbearia.slug,
        "gateway_pagamento": barbearia.gateway_pagamento,
        "plano_codigo": barbearia.plano_codigo,
        "plano_periodicidade": barbearia.plano_periodicidade,
        "status_assinatura": barbearia.status_assinatura,
        "stripe_customer_id": barbearia.stripe_customer_id,
        "stripe_subscription_id": barbearia.stripe_subscription_id,
        "stripe_checkout_session_id": barbearia.stripe_checkout_session_id,
        "assinatura_iniciada_em": (
            barbearia.assinatura_iniciada_em.isoformat()
            if barbearia.assinatura_iniciada_em
            else None
        ),
        "assinatura_renova_em": (
            barbearia.assinatura_renova_em.isoformat()
            if barbearia.assinatura_renova_em
            else None
        ),
        "periodo_trial_ate": (
            barbearia.periodo_trial_ate.isoformat()
            if barbearia.periodo_trial_ate
            else None
        ),
        "ultima_cobranca_status": barbearia.ultima_cobranca_status,
        "status_pagamento": barbearia.status_pagamento,
        "vencimento_plano": (
            barbearia.vencimento_plano.isoformat()
            if barbearia.vencimento_plano
            else None
        ),
        "acesso_ativo": getattr(
            barbearia,
            "plano_ativo",
            None,
        ),
    }


@router.get("/api/saas/assinaturas/planos")
def listar_planos_saas(
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    return listar_planos_assinatura()


@router.post("/api/saas/assinaturas/checkout")
def criar_checkout_assinatura_saas(
    dados: CriarCheckoutAssinatura,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    configurar_stripe()

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

    price_id = obter_price_id_por_plano(
        plano.codigo
    )

    frontend_base_url = settings.frontend_base_url.rstrip("/")

    success_url = (
        f"{frontend_base_url}/saas.html"
        f"?stripe=sucesso"
        f"&empresa_id={barbearia.id}"
    )

    cancel_url = (
        f"{frontend_base_url}/saas.html"
        f"?stripe=cancelado"
        f"&empresa_id={barbearia.id}"
    )

    customer_id = barbearia.stripe_customer_id

    if not customer_id:
        customer = stripe.Customer.create(
            email=barbearia.email,
            name=barbearia.nome,
            metadata={
                "barbearia_id": str(barbearia.id),
                "tenant_slug": barbearia.slug,
            },
        )

        customer_id = customer["id"]
        barbearia.stripe_customer_id = customer_id

    try:
        checkout = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "barbearia_id": str(barbearia.id),
                "tenant_slug": barbearia.slug,
                "plano_codigo": plano.codigo,
            },
            subscription_data={
                "metadata": {
                    "barbearia_id": str(barbearia.id),
                    "tenant_slug": barbearia.slug,
                    "plano_codigo": plano.codigo,
                }
            },
        )

    except stripe.error.InvalidRequestError as erro:
        raise HTTPException(
            status_code=400,
            detail=(
                "Erro ao criar checkout no Stripe. "
                "Verifique se o Price ID existe no painel do Stripe. "
                f"Detalhe: {str(erro)}"
            ),
        )

    except stripe.error.StripeError as erro:
        raise HTTPException(
            status_code=502,
            detail=(
                "Erro de comunicação com o Stripe. "
                f"Detalhe: {str(erro)}"
            ),
        )

    barbearia.gateway_pagamento = "stripe"
    barbearia.plano_codigo = plano.codigo
    barbearia.plano_periodicidade = plano.periodicidade
    barbearia.valor_mensal = plano.valor_mensal_equivalente
    barbearia.status_assinatura = "checkout_criado"
    barbearia.stripe_checkout_session_id = checkout["id"]

    db.commit()
    db.refresh(barbearia)

    return {
        "mensagem": "Checkout criado com sucesso.",
        "checkout_url": checkout["url"],
        "checkout_session_id": checkout["id"],
        "empresa": serializar_plano_empresa(barbearia),
    }


def atualizar_barbearia_por_assinatura(
    db: Session,
    subscription: dict,
):
    metadata = subscription.get("metadata") or {}

    barbearia_id = metadata.get("barbearia_id")
    plano_codigo = metadata.get("plano_codigo")

    if not barbearia_id:
        return

    barbearia = (
        db.query(models.Barbearia)
        .filter(
            models.Barbearia.id == int(barbearia_id)
        )
        .first()
    )

    if not barbearia:
        return

    plano = None

    if plano_codigo:
        try:
            plano = obter_plano_assinatura(
                plano_codigo
            )

        except ValueError:
            plano = None

    status_stripe = subscription.get("status")

    barbearia.gateway_pagamento = "stripe"
    barbearia.stripe_subscription_id = subscription.get("id")
    barbearia.status_assinatura = status_stripe or "desconhecido"

    if plano:
        barbearia.plano_codigo = plano.codigo
        barbearia.plano_periodicidade = plano.periodicidade
        barbearia.valor_mensal = plano.valor_mensal_equivalente

    current_period_start = subscription.get("current_period_start")
    current_period_end = subscription.get("current_period_end")
    trial_end = subscription.get("trial_end")

    barbearia.assinatura_iniciada_em = timestamp_para_datetime(
        current_period_start
    )

    barbearia.assinatura_renova_em = timestamp_para_datetime(
        current_period_end
    )

    barbearia.periodo_trial_ate = timestamp_para_datetime(
        trial_end
    )

    if status_stripe in {
        "active",
        "trialing",
    }:
        barbearia.status_pagamento = "em_dia"
        barbearia.plano_ativo = True
        barbearia.ultimo_pagamento_em = datetime.utcnow()

        if barbearia.assinatura_renova_em:
            barbearia.vencimento_plano = (
                barbearia.assinatura_renova_em.date()
            )

    elif status_stripe in {
        "past_due",
        "unpaid",
    }:
        barbearia.status_pagamento = "pendente"

    elif status_stripe in {
        "canceled",
        "incomplete_expired",
    }:
        barbearia.status_pagamento = "cancelado"
        barbearia.plano_ativo = False

    db.commit()


def atualizar_barbearia_por_invoice(
    db: Session,
    invoice: dict,
):
    subscription_id = invoice.get("subscription")

    if not subscription_id:
        return

    barbearia = (
        db.query(models.Barbearia)
        .filter(
            models.Barbearia.stripe_subscription_id == subscription_id
        )
        .first()
    )

    if not barbearia:
        return

    status_invoice = invoice.get("status")

    barbearia.ultima_cobranca_status = status_invoice

    if status_invoice == "paid":
        barbearia.status_pagamento = "em_dia"
        barbearia.plano_ativo = True
        barbearia.ultimo_pagamento_em = datetime.utcnow()

    elif status_invoice in {
        "open",
        "uncollectible",
        "void",
    }:
        barbearia.status_pagamento = "pendente"

    db.commit()


@router.post("/api/webhooks/stripe")
async def webhook_stripe(
    request: Request,
    stripe_signature: str | None = Header(
        default=None,
        alias="Stripe-Signature",
    ),
    db: Session = Depends(get_db),
):
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="STRIPE_WEBHOOK_SECRET não configurada.",
        )

    payload = await request.body()

    try:
        evento = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.stripe_webhook_secret,
        )

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Payload inválido.",
        )

    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=400,
            detail="Assinatura do webhook inválida.",
        )

    tipo_evento = evento["type"]
    objeto = evento["data"]["object"]

    if tipo_evento in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        atualizar_barbearia_por_assinatura(
            db,
            objeto,
        )

    if tipo_evento in {
        "invoice.paid",
        "invoice.payment_failed",
        "invoice.payment_succeeded",
    }:
        atualizar_barbearia_por_invoice(
            db,
            objeto,
        )

    if tipo_evento == "checkout.session.completed":
        barbearia_id = (
            objeto.get("metadata", {})
            .get("barbearia_id")
        )

        subscription_id = objeto.get("subscription")

        customer_id = objeto.get("customer")

        if barbearia_id:
            barbearia = (
                db.query(models.Barbearia)
                .filter(
                    models.Barbearia.id == int(barbearia_id)
                )
                .first()
            )

            if barbearia:
                barbearia.stripe_subscription_id = subscription_id
                barbearia.stripe_customer_id = customer_id
                barbearia.status_assinatura = "checkout_concluido"
                db.commit()

    return {
        "recebido": True,
    }