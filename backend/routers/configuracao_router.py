from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from services import configuracao_service
from security import validar_tenant_logado
from settings import settings


router = APIRouter()


def get_db():
    db = SessaoLocal()

    try:
        yield db

    finally:
        db.close()


@router.get("/api/{tenant_slug}/configuracoes")
def ler_configuracoes(
    tenant_slug: str,
    db: Session = Depends(get_db),
):
    configuracao = configuracao_service.ler_configuracoes(
        db,
        tenant_slug,
    )

    barbearia = (
        db.query(models.Barbearia)
        .filter(
            models.Barbearia.slug == tenant_slug
        )
        .first()
    )

    if not barbearia:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada.",
        )

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

    total_agendamentos_trial = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug == tenant_slug
        )
        .count()
    )

    dias_restantes_trial = 0

    if barbearia.periodo_trial_ate:
        diferenca = barbearia.periodo_trial_ate.date() - agora.date()

        dias_restantes_trial = max(
            diferenca.days,
            0,
        )

    agendamentos_restantes_trial = max(
        settings.trial_limite_agendamentos - total_agendamentos_trial,
        0,
    )

    trial_expirado_por_dias = dias_restantes_trial <= 0

    trial_expirado_por_agendamentos = (
        total_agendamentos_trial >= settings.trial_limite_agendamentos
    )

    trial_expirado = (
        trial_expirado_por_dias
        or trial_expirado_por_agendamentos
    )

    if hasattr(configuracao, "model_dump"):
        dados = configuracao.model_dump()

    elif hasattr(configuracao, "dict"):
        dados = configuracao.dict()

    elif isinstance(configuracao, dict):
        dados = configuracao

    else:
        dados = {
            chave: valor
            for chave, valor in vars(configuracao).items()
            if not chave.startswith("_")
        }

    dados.update(
        {
            "gateway_pagamento": barbearia.gateway_pagamento,
            "plano_codigo": barbearia.plano_codigo,
            "plano_periodicidade": barbearia.plano_periodicidade,
            "status_assinatura": barbearia.status_assinatura,
            "status_pagamento": barbearia.status_pagamento,
            "plano_nome": barbearia.plano_nome,
            "valor_mensal": barbearia.valor_mensal,
            "vencimento_plano": (
                barbearia.vencimento_plano.isoformat()
                if barbearia.vencimento_plano
                else None
            ),
            "acesso_ativo": barbearia.plano_ativo,
            "periodo_trial_ate": (
                barbearia.periodo_trial_ate.isoformat()
                if barbearia.periodo_trial_ate
                else None
            ),
            "trial_dias_padrao": settings.trial_dias_padrao,
            "trial_limite_agendamentos": settings.trial_limite_agendamentos,
            "trial_total_agendamentos": total_agendamentos_trial,
            "trial_dias_restantes": dias_restantes_trial,
            "trial_agendamentos_restantes": agendamentos_restantes_trial,
            "trial_expirado": trial_expirado,
            "trial_expirado_por_dias": trial_expirado_por_dias,
            "trial_expirado_por_agendamentos": trial_expirado_por_agendamentos,
        }
    )

    return dados


@router.post("/api/{tenant_slug}/configuracoes")
def salvar_configuracoes(
    tenant_slug: str,
    dados: configuracao_service.NovaConfiguracao,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
):
    return configuracao_service.atualizar_configuracoes(
        db,
        tenant_slug,
        dados,
    )