from datetime import datetime, timedelta

from sqlalchemy.orm import Session

import models
from settings import settings


STATUS_ASSINATURA_ATIVA = {
    "active",
    "trialing",
    "checkout_concluido",
    "mercado_pago_aprovado",
}

STATUS_PAGAMENTO_ATIVO = {
    "em_dia",
}


def assinatura_esta_ativa(
    barbearia: models.Barbearia,
) -> bool:
    if bool(barbearia.plano_ativo):
        return True

    if barbearia.status_pagamento in STATUS_PAGAMENTO_ATIVO:
        return True

    if barbearia.status_assinatura in STATUS_ASSINATURA_ATIVA:
        return True

    return False


def garantir_periodo_trial(
    db: Session,
    barbearia: models.Barbearia,
) -> models.Barbearia:
    agora = datetime.utcnow()

    if not barbearia.periodo_trial_ate:
        barbearia.periodo_trial_ate = agora + timedelta(
            days=settings.trial_dias_padrao
        )

        if not barbearia.status_pagamento:
            barbearia.status_pagamento = "teste"

        if not barbearia.status_assinatura:
            barbearia.status_assinatura = "trial"

        db.commit()
        db.refresh(barbearia)

    return barbearia


def contar_agendamentos_trial(
    db: Session,
    tenant_slug: str,
) -> int:
    return (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug == tenant_slug
        )
        .count()
    )


def calcular_resumo_trial(
    db: Session,
    barbearia: models.Barbearia,
) -> dict:
    barbearia = garantir_periodo_trial(
        db,
        barbearia,
    )

    agora = datetime.utcnow()

    total_agendamentos = contar_agendamentos_trial(
        db,
        barbearia.slug,
    )

    dias_restantes = 0

    if barbearia.periodo_trial_ate:
        diferenca = (
            barbearia.periodo_trial_ate.date()
            - agora.date()
        )

        dias_restantes = max(
            diferenca.days,
            0,
        )

    agendamentos_restantes = max(
        settings.trial_limite_agendamentos - total_agendamentos,
        0,
    )

    expirado_por_dias = dias_restantes <= 0

    expirado_por_agendamentos = (
        total_agendamentos >= settings.trial_limite_agendamentos
    )

    trial_expirado = (
        expirado_por_dias
        or expirado_por_agendamentos
    )

    ativa = assinatura_esta_ativa(
        barbearia
    )

    acesso_liberado = (
        ativa
        or not trial_expirado
    )

    return {
        "periodo_trial_ate": (
            barbearia.periodo_trial_ate.isoformat()
            if barbearia.periodo_trial_ate
            else None
        ),
        "trial_dias_padrao": settings.trial_dias_padrao,
        "trial_limite_agendamentos": settings.trial_limite_agendamentos,
        "trial_total_agendamentos": total_agendamentos,
        "trial_dias_restantes": dias_restantes,
        "trial_agendamentos_restantes": agendamentos_restantes,
        "trial_expirado": trial_expirado,
        "trial_expirado_por_dias": expirado_por_dias,
        "trial_expirado_por_agendamentos": expirado_por_agendamentos,
        "assinatura_ativa": ativa,
        "acesso_liberado": acesso_liberado,
    }


def tenant_pode_receber_agendamento(
    db: Session,
    tenant_slug: str,
) -> tuple[bool, dict | None]:
    barbearia = (
        db.query(models.Barbearia)
        .filter(
            models.Barbearia.slug == tenant_slug
        )
        .first()
    )

    if not barbearia:
        return False, None

    resumo = calcular_resumo_trial(
        db,
        barbearia,
    )

    return bool(resumo["acesso_liberado"]), resumo