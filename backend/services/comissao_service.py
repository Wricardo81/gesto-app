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


def listar_comissoes_pendentes(
    db: Session,
    tenant_slug: str,
    profissional_nome: str | None = None,
) -> dict:
    consulta = (
        db.query(models.ComissaoAtendimento)
        .filter(
            models.ComissaoAtendimento.barbearia_slug
            == tenant_slug,
            models.ComissaoAtendimento.status
            == "pendente",
        )
    )

    if profissional_nome:
        consulta = consulta.filter(
            models.ComissaoAtendimento.profissional_nome
            == profissional_nome
        )

    comissoes = (
        consulta
        .order_by(
            models.ComissaoAtendimento.gerado_em.asc(),
            models.ComissaoAtendimento.id.asc(),
        )
        .all()
    )

    itens = [
        {
            "id": comissao.id,
            "agendamento_id": comissao.agendamento_id,
            "profissional_nome": comissao.profissional_nome,
            "servico": comissao.servico,
            "valor_atendimento": float(
                comissao.valor_atendimento or 0
            ),
            "comissao_tipo": comissao.comissao_tipo,
            "comissao_regra_valor": float(
                comissao.comissao_regra_valor or 0
            ),
            "valor_comissao": float(
                comissao.valor_comissao or 0
            ),
            "status": comissao.status,
            "gerado_em": (
                comissao.gerado_em.isoformat()
                if comissao.gerado_em
                else None
            ),
        }
        for comissao in comissoes
    ]

    total_pendente = round(
        sum(
            float(comissao.valor_comissao or 0)
            for comissao in comissoes
        ),
        2,
    )

    return {
        "tenant_slug": tenant_slug,
        "profissional_nome": profissional_nome,
        "quantidade": len(itens),
        "total_pendente": total_pendente,
        "comissoes": itens,
    }
