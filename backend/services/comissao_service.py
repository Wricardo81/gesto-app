from sqlalchemy.orm import Session

import models


def calcular_valor_comissao(
    valor_atendimento: float,
    comissao_tipo: str,
    comissao_valor: float,
) -> float:
    tipo = str(comissao_tipo or "nenhuma").strip().lower()
    valor_regra = float(comissao_valor or 0)
    valor_atendimento = float(valor_atendimento or 0)

    if tipo == "percentual":
        return round(
            valor_atendimento * valor_regra / 100,
            2,
        )

    if tipo == "valor_fixo":
        return round(valor_regra, 2)

    return 0.0


def gerar_comissao_atendimento_se_necessario(
    db: Session,
    agendamento: models.Agendamento,
) -> models.ComissaoAtendimento:
    existente = (
        db.query(models.ComissaoAtendimento)
        .filter(
            models.ComissaoAtendimento.barbearia_slug
            == agendamento.barbearia_slug,
            models.ComissaoAtendimento.agendamento_id
            == agendamento.id,
        )
        .first()
    )

    if existente:
        return existente

    profissional = (
        db.query(models.Profissional)
        .filter(
            models.Profissional.barbearia_slug
            == agendamento.barbearia_slug,
            models.Profissional.nome
            == agendamento.profissional,
        )
        .first()
    )

    tipo = (
        profissional.comissao_tipo
        if profissional
        else "nenhuma"
    )

    valor_regra = float(
        profissional.comissao_valor or 0
        if profissional
        else 0
    )

    valor_atendimento = float(
        agendamento.valor or 0
    )

    valor_comissao = calcular_valor_comissao(
        valor_atendimento,
        tipo,
        valor_regra,
    )

    comissao = models.ComissaoAtendimento(
        barbearia_slug=agendamento.barbearia_slug,
        agendamento_id=agendamento.id,
        profissional_nome=agendamento.profissional,
        servico=agendamento.servico,
        valor_atendimento=valor_atendimento,
        comissao_tipo=tipo,
        comissao_regra_valor=valor_regra,
        valor_comissao=valor_comissao,
        status="pendente",
    )

    db.add(comissao)

    return comissao
