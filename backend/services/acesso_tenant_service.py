from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models


def calcular_acesso_financeiro(
    barbearia: models.Barbearia,
) -> dict:
    status_pagamento = getattr(
        barbearia,
        "status_pagamento",
        "em_dia",
    ) or "em_dia"

    vencimento = getattr(
        barbearia,
        "vencimento_plano",
        None,
    )

    dias_tolerancia = int(
        getattr(
            barbearia,
            "dias_tolerancia",
            3,
        ) or 0
    )

    hoje = date.today()

    dias_em_atraso = 0
    pagamento_vencido = False
    acesso_financeiro_ativo = True

    if vencimento and hoje > vencimento:
        dias_em_atraso = (hoje - vencimento).days
        pagamento_vencido = True

    if status_pagamento in {
        "cancelado",
        "vencido",
    }:
        acesso_financeiro_ativo = False

    if (
        pagamento_vencido
        and dias_em_atraso > dias_tolerancia
        and status_pagamento != "teste"
    ):
        acesso_financeiro_ativo = False

    return {
        "status_pagamento": status_pagamento,
        "pagamento_vencido": pagamento_vencido,
        "dias_em_atraso": dias_em_atraso,
        "dias_tolerancia": dias_tolerancia,
        "acesso_financeiro_ativo": acesso_financeiro_ativo,
    }


def obter_diagnostico_acesso_tenant(
    barbearia: models.Barbearia,
) -> dict:
    financeiro = calcular_acesso_financeiro(
        barbearia
    )

    plano_ativo_manual = bool(
        getattr(
            barbearia,
            "plano_ativo",
            True,
        )
    )

    acesso_ativo = (
        plano_ativo_manual
        and financeiro["acesso_financeiro_ativo"]
    )

    return {
        "plano_ativo_manual": plano_ativo_manual,
        "acesso_ativo": acesso_ativo,
        **financeiro,
    }


def buscar_tenant_ou_404(
    db: Session,
    tenant_slug: str,
) -> models.Barbearia:
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
            detail="Estabelecimento não encontrado.",
        )

    return barbearia


def validar_acesso_operacional_tenant(
    db: Session,
    tenant_slug: str,
) -> models.Barbearia:
    barbearia = buscar_tenant_ou_404(
        db,
        tenant_slug,
    )

    diagnostico = obter_diagnostico_acesso_tenant(
        barbearia
    )

    if diagnostico["acesso_ativo"]:
        return barbearia

    if not diagnostico["plano_ativo_manual"]:
        mensagem = (
            "O acesso deste estabelecimento está bloqueado manualmente "
            "pela administração da plataforma."
        )
    elif diagnostico["status_pagamento"] == "cancelado":
        mensagem = (
            "A assinatura deste estabelecimento foi cancelada."
        )
    elif diagnostico["status_pagamento"] == "vencido":
        mensagem = (
            "A assinatura deste estabelecimento está vencida."
        )
    elif diagnostico["pagamento_vencido"]:
        mensagem = (
            "A assinatura deste estabelecimento está vencida "
            "fora do período de tolerância."
        )
    else:
        mensagem = (
            "O acesso deste estabelecimento está temporariamente indisponível."
        )

    raise HTTPException(
        status_code=402,
        detail={
            "codigo": "ASSINATURA_INATIVA",
            "mensagem": mensagem,
            "status_pagamento": diagnostico["status_pagamento"],
            "pagamento_vencido": diagnostico["pagamento_vencido"],
            "dias_em_atraso": diagnostico["dias_em_atraso"],
            "dias_tolerancia": diagnostico["dias_tolerancia"],
        },
    )