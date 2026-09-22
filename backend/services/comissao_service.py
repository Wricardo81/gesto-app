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

from datetime import datetime
from pydantic import BaseModel, Field


class NovoRepasseProfissional(BaseModel):
    comissoes_ids: list[int] = Field(min_length=1)
    observacao: str | None = None


def registrar_repasse_profissional(
    db: Session,
    tenant_slug: str,
    dados: NovoRepasseProfissional,
    registrado_por: str | None = None,
) -> dict:
    ids_unicos = list(dict.fromkeys(dados.comissoes_ids))

    comissoes = (
        db.query(models.ComissaoAtendimento)
        .filter(
            models.ComissaoAtendimento.barbearia_slug
            == tenant_slug,
            models.ComissaoAtendimento.id.in_(ids_unicos),
        )
        .order_by(models.ComissaoAtendimento.id.asc())
        .with_for_update()
        .all()
    )

    if len(comissoes) != len(ids_unicos):
        raise ValueError(
            "Uma ou mais comissoes nao foram encontradas para este tenant."
        )

    comissoes_nao_pendentes = [
        comissao.id
        for comissao in comissoes
        if comissao.status != "pendente"
        or comissao.repasse_id is not None
    ]

    if comissoes_nao_pendentes:
        raise ValueError(
            "Uma ou mais comissoes ja foram pagas ou vinculadas a outro repasse."
        )

    profissionais = {
        comissao.profissional_nome
        for comissao in comissoes
    }

    if len(profissionais) != 1:
        raise ValueError(
            "Todas as comissoes do repasse devem pertencer ao mesmo profissional."
        )

    profissional_nome = next(iter(profissionais))

    total = round(
        sum(
            float(comissao.valor_comissao or 0)
            for comissao in comissoes
        ),
        2,
    )

    datas_atendimentos = []

    for comissao in comissoes:
        agendamento = (
            db.query(models.Agendamento)
            .filter(
                models.Agendamento.id
                == comissao.agendamento_id,
                models.Agendamento.barbearia_slug
                == tenant_slug,
            )
            .first()
        )

        if agendamento and agendamento.data:
            datas_atendimentos.append(
                agendamento.data
            )

    agora = datetime.utcnow()

    repasse = models.RepasseProfissional(
        barbearia_slug=tenant_slug,
        profissional_nome=profissional_nome,
        valor=total,
        periodo_inicio=(
            min(datas_atendimentos)
            if datas_atendimentos
            else None
        ),
        periodo_fim=(
            max(datas_atendimentos)
            if datas_atendimentos
            else None
        ),
        observacao=(
            dados.observacao.strip()
            if dados.observacao
            else None
        ),
        registrado_por=registrado_por,
        pago_em=agora,
    )

    db.add(repasse)
    db.flush()

    for comissao in comissoes:
        comissao.repasse_id = repasse.id
        comissao.status = "pago"
        comissao.pago_em = agora

    db.commit()
    db.refresh(repasse)

    return {
        "id": repasse.id,
        "tenant_slug": repasse.barbearia_slug,
        "profissional_nome": repasse.profissional_nome,
        "valor": float(repasse.valor or 0),
        "periodo_inicio": (
            repasse.periodo_inicio.isoformat()
            if repasse.periodo_inicio
            else None
        ),
        "periodo_fim": (
            repasse.periodo_fim.isoformat()
            if repasse.periodo_fim
            else None
        ),
        "observacao": repasse.observacao,
        "registrado_por": repasse.registrado_por,
        "pago_em": (
            repasse.pago_em.isoformat()
            if repasse.pago_em
            else None
        ),
        "comissoes_ids": [
            comissao.id
            for comissao in comissoes
        ],
        "quantidade_comissoes": len(comissoes),
    }


def listar_repasses_profissionais(
    db: Session,
    tenant_slug: str,
    profissional_nome: str | None = None,
) -> dict:
    consulta = (
        db.query(models.RepasseProfissional)
        .filter(
            models.RepasseProfissional.barbearia_slug
            == tenant_slug
        )
    )

    if profissional_nome:
        consulta = consulta.filter(
            models.RepasseProfissional.profissional_nome
            == profissional_nome
        )

    repasses = (
        consulta
        .order_by(
            models.RepasseProfissional.pago_em.desc(),
            models.RepasseProfissional.id.desc(),
        )
        .all()
    )

    itens = []

    for repasse in repasses:
        quantidade_comissoes = (
            db.query(models.ComissaoAtendimento)
            .filter(
                models.ComissaoAtendimento.barbearia_slug
                == tenant_slug,
                models.ComissaoAtendimento.repasse_id
                == repasse.id,
            )
            .count()
        )

        itens.append(
            {
                "id": repasse.id,
                "profissional_nome": repasse.profissional_nome,
                "valor": float(repasse.valor or 0),
                "periodo_inicio": (
                    repasse.periodo_inicio.isoformat()
                    if repasse.periodo_inicio
                    else None
                ),
                "periodo_fim": (
                    repasse.periodo_fim.isoformat()
                    if repasse.periodo_fim
                    else None
                ),
                "observacao": repasse.observacao,
                "registrado_por": repasse.registrado_por,
                "pago_em": (
                    repasse.pago_em.isoformat()
                    if repasse.pago_em
                    else None
                ),
                "quantidade_comissoes": quantidade_comissoes,
            }
        )

    total_pago = round(
        sum(
            float(repasse.valor or 0)
            for repasse in repasses
        ),
        2,
    )

    return {
        "tenant_slug": tenant_slug,
        "profissional_nome": profissional_nome,
        "quantidade": len(itens),
        "total_pago": total_pago,
        "repasses": itens,
    }


def obter_repasse_profissional(
    db: Session,
    tenant_slug: str,
    repasse_id: int,
) -> dict | None:
    repasse = (
        db.query(models.RepasseProfissional)
        .filter(
            models.RepasseProfissional.id == repasse_id,
            models.RepasseProfissional.barbearia_slug
            == tenant_slug,
        )
        .first()
    )

    if not repasse:
        return None

    comissoes = (
        db.query(models.ComissaoAtendimento)
        .filter(
            models.ComissaoAtendimento.barbearia_slug
            == tenant_slug,
            models.ComissaoAtendimento.repasse_id
            == repasse.id,
        )
        .order_by(
            models.ComissaoAtendimento.id.asc()
        )
        .all()
    )

    itens_comissoes = [
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
            "pago_em": (
                comissao.pago_em.isoformat()
                if comissao.pago_em
                else None
            ),
        }
        for comissao in comissoes
    ]

    return {
        "id": repasse.id,
        "tenant_slug": repasse.barbearia_slug,
        "profissional_nome": repasse.profissional_nome,
        "valor": float(repasse.valor or 0),
        "periodo_inicio": (
            repasse.periodo_inicio.isoformat()
            if repasse.periodo_inicio
            else None
        ),
        "periodo_fim": (
            repasse.periodo_fim.isoformat()
            if repasse.periodo_fim
            else None
        ),
        "observacao": repasse.observacao,
        "registrado_por": repasse.registrado_por,
        "pago_em": (
            repasse.pago_em.isoformat()
            if repasse.pago_em
            else None
        ),
        "criado_em": (
            repasse.criado_em.isoformat()
            if repasse.criado_em
            else None
        ),
        "quantidade_comissoes": len(itens_comissoes),
        "comissoes": itens_comissoes,
    }
