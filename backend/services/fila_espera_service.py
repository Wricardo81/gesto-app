from __future__ import annotations

from datetime import date, datetime
from typing import Iterable

from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import models


STATUS_FILA_ESPERA = {
    "aguardando",
    "chamado",
    "agendado",
    "cancelado",
    "expirado",
    "arquivado",
}

TRANSICOES_STATUS_FILA_ESPERA = {
    "aguardando": {
        "chamado",
        "cancelado",
        "expirado",
        "arquivado",
    },
    "chamado": {
        "aguardando",
        "cancelado",
        "expirado",
        "arquivado",
    },
    "agendado": {
        "arquivado",
    },
    "cancelado": {
        "arquivado",
    },
    "expirado": {
        "arquivado",
    },
    "arquivado": set(),
}

PERIODOS_PREFERIDOS = {
    "manha",
    "tarde",
    "noite",
    "qualquer",
}

PRIORIDADES_FILA_ESPERA = {
    "baixa",
    "normal",
    "alta",
}


class EntradaFilaEsperaPublica(BaseModel):
    cliente_nome: str = Field(min_length=2, max_length=120)
    telefone_cliente: str = Field(min_length=8, max_length=30)
    servico: str = Field(min_length=2, max_length=120)
    profissional_preferido: str | None = Field(default=None, max_length=120)
    data_desejada: date | None = None
    periodo_preferido: str | None = Field(default="qualquer", max_length=20)
    observacao: str | None = Field(default=None, max_length=500)


class ConverterFilaEsperaAgendamento(BaseModel):
    data: str | None = None
    horario: str = Field(min_length=4, max_length=10)
    profissional: str | None = Field(default=None, max_length=120)


class AtualizacaoStatusFilaEspera(BaseModel):
    status: str = Field(min_length=3, max_length=30)


def normalizar_texto(valor: str | None) -> str:
    return (valor or "").strip()


def normalizar_periodo(valor: str | None) -> str:
    periodo = normalizar_texto(valor).lower() or "qualquer"

    if periodo not in PERIODOS_PREFERIDOS:
        raise HTTPException(
            status_code=422,
            detail="Periodo preferido invalido.",
        )

    return periodo


def normalizar_status(valor: str | None) -> str:
    status = normalizar_texto(valor).lower()

    if status not in STATUS_FILA_ESPERA:
        raise HTTPException(
            status_code=422,
            detail="Status da fila de espera invalido.",
        )

    return status


def serializar_item_fila_espera(item: models.FilaEspera) -> dict:
    return {
        "id": item.id,
        "barbearia_slug": item.barbearia_slug,
        "cliente_nome": item.cliente_nome,
        "telefone_cliente": item.telefone_cliente,
        "servico": item.servico,
        "profissional_preferido": item.profissional_preferido,
        "data_desejada": item.data_desejada.isoformat() if item.data_desejada else None,
        "periodo_preferido": item.periodo_preferido,
        "prioridade": item.prioridade,
        "status": item.status,
        "observacao": item.observacao,
        "origem": item.origem,
        "chamado_em": item.chamado_em.isoformat() if item.chamado_em else None,
        "agendado_em": item.agendado_em.isoformat() if item.agendado_em else None,
        "cancelado_em": item.cancelado_em.isoformat() if item.cancelado_em else None,
        "expirado_em": item.expirado_em.isoformat() if item.expirado_em else None,
        "criado_em": item.criado_em.isoformat() if item.criado_em else None,
        "atualizado_em": item.atualizado_em.isoformat() if item.atualizado_em else None,
    }


def criar_entrada_fila_espera(
    db: Session,
    tenant_slug: str,
    dados: EntradaFilaEsperaPublica,
) -> dict:
    cliente_nome = normalizar_texto(dados.cliente_nome)
    telefone_cliente = normalizar_texto(dados.telefone_cliente)
    servico = normalizar_texto(dados.servico)
    profissional_preferido = normalizar_texto(dados.profissional_preferido) or None
    periodo_preferido = normalizar_periodo(dados.periodo_preferido)

    item = models.FilaEspera(
        barbearia_slug=tenant_slug,
        cliente_nome=cliente_nome,
        telefone_cliente=telefone_cliente,
        servico=servico,
        profissional_preferido=profissional_preferido,
        data_desejada=dados.data_desejada,
        periodo_preferido=periodo_preferido,
        prioridade="normal",
        status="aguardando",
        observacao=normalizar_texto(dados.observacao) or None,
        origem="agenda_publica",
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return serializar_item_fila_espera(item)


def listar_fila_espera(
    db: Session,
    tenant_slug: str,
    status: str | None = None,
) -> list[dict]:
    query = (
        db.query(models.FilaEspera)
        .filter(models.FilaEspera.barbearia_slug == tenant_slug)
    )

    if status:
        query = query.filter(models.FilaEspera.status == normalizar_status(status))

    itens = (
        query
        .order_by(models.FilaEspera.criado_em.desc())
        .all()
    )

    return [serializar_item_fila_espera(item) for item in itens]


def atualizar_status_fila_espera(
    db: Session,
    tenant_slug: str,
    item_id: int,
    dados: AtualizacaoStatusFilaEspera,
) -> dict:
    status = normalizar_status(dados.status)

    item = (
        db.query(models.FilaEspera)
        .filter(
            models.FilaEspera.id == item_id,
            models.FilaEspera.barbearia_slug == tenant_slug,
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item da fila de espera nao encontrado.",
        )

    status_atual = normalizar_status(item.status)

    # PUT idempotente: repetir o mesmo status nao altera timestamps.
    if status == status_atual:
        return serializar_item_fila_espera(item)

    # "agendado" somente pode ser alcan?ado pela conversao real
    # fila -> agendamento.
    if status == "agendado":
        raise HTTPException(
            status_code=409,
            detail=(
                "O status agendado so pode ser definido "
                "pela conversao da fila em agendamento."
            ),
        )

    transicoes_permitidas = TRANSICOES_STATUS_FILA_ESPERA.get(
        status_atual,
        set(),
    )

    if status not in transicoes_permitidas:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Transicao de status nao permitida: "
                f"{status_atual} -> {status}."
            ),
        )

    agora = datetime.utcnow()
    item.status = status

    if status == "chamado":
        item.chamado_em = agora
    elif status == "agendado":
        item.agendado_em = agora
    elif status == "cancelado":
        item.cancelado_em = agora
    elif status == "expirado":
        item.expirado_em = agora

    db.commit()
    db.refresh(item)

    return serializar_item_fila_espera(item)


def excluir_item_fila_espera(
    db: Session,
    tenant_slug: str,
    item_id: int,
) -> dict:
    item = (
        db.query(models.FilaEspera)
        .filter(
            models.FilaEspera.id == item_id,
            models.FilaEspera.barbearia_slug == tenant_slug,
        )
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item da fila de espera nao encontrado.",
        )

    status_atual = str(
        item.status or ""
    ).strip().lower()

    if status_atual != "arquivado":
        raise HTTPException(
            status_code=409,
            detail=(
                "Somente itens arquivados podem ser "
                "excluidos definitivamente."
            ),
        )

    item_id_excluido = item.id

    db.delete(item)
    db.commit()

    return {
        "id": item_id_excluido,
        "excluido": True,
    }
