from fastapi import HTTPException

from services.trial_service import tenant_pode_receber_agendamento


STATUS_ASSINATURA_LIBERADOS = {
    "trial",
    "teste",
    "trialing",
    "active",
    "mercado_pago_aprovado",
}

STATUS_PAGAMENTO_LIBERADOS = {
    "trial",
    "teste",
    "em_dia",
}


STATUS_ASSINATURA_BLOQUEADOS = {
    "desativada",
    "cancelada",
    "canceled",
    "unpaid",
    "past_due",
    "mercado_pago_cancelled",
    "mercado_pago_rejected",
    "mercado_pago_refunded",
    "mercado_pago_charged_back",
}


def normalizar_status(valor) -> str:
    return str(valor or "").strip().lower()


def obter_diagnostico_acesso_empresa(*, db, empresa) -> dict:
    pode_receber_agendamento, resumo_trial = tenant_pode_receber_agendamento(
        db,
        empresa.slug,
    )

    if resumo_trial is None:
        resumo_trial = {}

    status_assinatura = normalizar_status(
        getattr(empresa, "status_assinatura", "")
    )

    status_pagamento = normalizar_status(
        getattr(empresa, "status_pagamento", "")
    )

    plano_ativo = bool(
        getattr(empresa, "plano_ativo", False)
    )

    empresa_desativada = status_assinatura == "desativada"

    trial_ativo = bool(pode_receber_agendamento) and (
        status_assinatura == "trial"
        or status_pagamento == "trial"
    )

    assinatura_ativa = (
        plano_ativo
        or status_assinatura in STATUS_ASSINATURA_LIBERADOS
        or status_pagamento in STATUS_PAGAMENTO_LIBERADOS
    )

    status_bloqueado = (
        status_assinatura in STATUS_ASSINATURA_BLOQUEADOS
        or status_pagamento in {"cancelado", "vencido"}
    )

    acesso_liberado = bool(
        not empresa_desativada
        and not status_bloqueado
        and (
            plano_ativo
            or trial_ativo
            or assinatura_ativa
        )
    )

    return {
        "acesso_liberado": acesso_liberado,
        "empresa_desativada": empresa_desativada,
        "plano_ativo": plano_ativo,
        "trial_ativo": trial_ativo,
        "assinatura_ativa": assinatura_ativa,
        "status_bloqueado": status_bloqueado,
        "status_assinatura": status_assinatura,
        "status_pagamento": status_pagamento,
        "resumo_trial": resumo_trial,
    }


def validar_empresa_pode_operar(*, db, empresa):
    diagnostico = obter_diagnostico_acesso_empresa(
        db=db,
        empresa=empresa,
    )

    if diagnostico["acesso_liberado"]:
        return diagnostico

    if diagnostico["empresa_desativada"]:
        mensagem = (
            "Esta empresa foi desativada pela administração da plataforma."
        )

    elif diagnostico["resumo_trial"].get("trial_expirado_por_agendamentos"):
        mensagem = (
            "O limite de agendamentos gratuitos desta empresa foi atingido."
        )

    elif diagnostico["resumo_trial"].get("trial_expirado_por_dias"):
        mensagem = (
            "O período gratuito desta empresa expirou."
        )

    elif diagnostico["status_pagamento"] == "cancelado":
        mensagem = (
            "A assinatura desta empresa foi cancelada."
        )

    elif diagnostico["status_pagamento"] == "vencido":
        mensagem = (
            "A assinatura desta empresa está vencida."
        )

    else:
        mensagem = (
            "Agenda temporariamente indisponível para novos agendamentos."
        )

    raise HTTPException(
        status_code=402,
        detail={
            "codigo": "ASSINATURA_INATIVA",
            "mensagem": mensagem,
            "status_assinatura": diagnostico["status_assinatura"],
            "status_pagamento": diagnostico["status_pagamento"],
            "trial_expirado": diagnostico["resumo_trial"].get("trial_expirado"),
            "trial_expirado_por_dias": diagnostico["resumo_trial"].get(
                "trial_expirado_por_dias"
            ),
            "trial_expirado_por_agendamentos": diagnostico["resumo_trial"].get(
                "trial_expirado_por_agendamentos"
            ),
        },
    )
