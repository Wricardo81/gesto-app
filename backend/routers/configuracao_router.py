from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from services import configuracao_service
from services.trial_service import calcular_resumo_trial
from security import validar_tenant_logado


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

    resumo_trial = calcular_resumo_trial(
        db,
        barbearia,
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
            "plano_ativo": barbearia.plano_ativo,
            "acesso_ativo": resumo_trial.get("acesso_liberado"),
            "assinatura_ativa": resumo_trial.get("assinatura_ativa"),
            **resumo_trial,
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
