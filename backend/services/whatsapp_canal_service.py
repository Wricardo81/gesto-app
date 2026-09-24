from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models


def agora_utc_naive() -> datetime:
    return datetime.now(
        UTC
    ).replace(
        tzinfo=None
    )


def normalizar_identificador(
    valor: str | None,
) -> str:
    return str(
        valor or ""
    ).strip()


def serializar_integracao_whatsapp(
    integracao: models.IntegracaoWhatsAppTenant,
) -> dict:
    return {
        "id":
            integracao.id,

        "barbearia_slug":
            integracao.barbearia_slug,

        "phone_number_id":
            integracao.phone_number_id,

        "business_account_id":
            integracao.business_account_id,

        "numero_exibicao":
            integracao.numero_exibicao,

        "ativo":
            bool(
                integracao.ativo
            ),

        "criado_em":
            (
                integracao.criado_em.isoformat()
                if integracao.criado_em
                else None
            ),

        "atualizado_em":
            (
                integracao.atualizado_em.isoformat()
                if integracao.atualizado_em
                else None
            ),
    }


def obter_integracao_por_tenant(
    db: Session,
    tenant_slug: str,
):
    tenant = normalizar_identificador(
        tenant_slug
    )

    if not tenant:
        return None

    return (
        db.query(
            models.IntegracaoWhatsAppTenant
        )
        .filter(
            models.IntegracaoWhatsAppTenant.barbearia_slug
            == tenant
        )
        .first()
    )


def obter_integracao_por_phone_number_id(
    db: Session,
    phone_number_id: str,
):
    identificador = normalizar_identificador(
        phone_number_id
    )

    if not identificador:
        return None

    return (
        db.query(
            models.IntegracaoWhatsAppTenant
        )
        .filter(
            models.IntegracaoWhatsAppTenant.phone_number_id
            == identificador
        )
        .first()
    )


def resolver_tenant_por_phone_number_id(
    db: Session,
    phone_number_id: str,
) -> str:
    integracao = (
        obter_integracao_por_phone_number_id(
            db=db,
            phone_number_id=phone_number_id,
        )
    )

    if not integracao:
        raise HTTPException(
            status_code=404,
            detail=(
                "Numero receptor do WhatsApp "
                "nao esta vinculado a nenhum tenant."
            ),
        )

    if not integracao.ativo:
        raise HTTPException(
            status_code=409,
            detail=(
                "Integracao WhatsApp deste "
                "estabelecimento esta inativa."
            ),
        )

    return integracao.barbearia_slug


def salvar_integracao_whatsapp(
    db: Session,
    *,
    tenant_slug: str,
    phone_number_id: str,
    business_account_id: str | None = None,
    numero_exibicao: str | None = None,
    ativo: bool = True,
):
    tenant = normalizar_identificador(
        tenant_slug
    )

    numero_id = normalizar_identificador(
        phone_number_id
    )

    conta_id = (
        normalizar_identificador(
            business_account_id
        )
        or None
    )

    numero = (
        normalizar_identificador(
            numero_exibicao
        )
        or None
    )

    if not tenant:
        raise HTTPException(
            status_code=422,
            detail="Tenant invalido.",
        )

    if not numero_id:
        raise HTTPException(
            status_code=422,
            detail="phone_number_id invalido.",
        )

    existente_outro_tenant = (
        db.query(
            models.IntegracaoWhatsAppTenant
        )
        .filter(
            models.IntegracaoWhatsAppTenant.phone_number_id
            == numero_id,

            models.IntegracaoWhatsAppTenant.barbearia_slug
            != tenant,
        )
        .first()
    )

    if existente_outro_tenant:
        raise HTTPException(
            status_code=409,
            detail=(
                "Este phone_number_id ja esta "
                "vinculado a outro tenant."
            ),
        )

    integracao = obter_integracao_por_tenant(
        db=db,
        tenant_slug=tenant,
    )

    agora = agora_utc_naive()

    if integracao:
        integracao.phone_number_id = numero_id
        integracao.business_account_id = conta_id
        integracao.numero_exibicao = numero
        integracao.ativo = bool(ativo)
        integracao.atualizado_em = agora

    else:
        integracao = models.IntegracaoWhatsAppTenant(
            barbearia_slug=tenant,
            phone_number_id=numero_id,
            business_account_id=conta_id,
            numero_exibicao=numero,
            ativo=bool(ativo),
            criado_em=agora,
            atualizado_em=agora,
        )

        db.add(
            integracao
        )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "Nao foi possivel salvar a "
                "integracao WhatsApp por conflito "
                "de identificadores."
            ),
        )

    db.refresh(
        integracao
    )

    return integracao
