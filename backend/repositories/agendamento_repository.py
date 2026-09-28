from datetime import date

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models


def bloquear_agenda_profissional_dia(
    db: Session,
    *,
    tenant_slug: str,
    profissional_nome: str,
    data_agendamento: date,
) -> None:
    """
    Serializa criacoes concorrentes de agendamento
    para o mesmo tenant, profissional e dia.

    PostgreSQL:
    usa advisory transaction lock, liberado
    automaticamente no commit/rollback.

    Outros bancos:
    no-op para manter compatibilidade de testes.
    """
    bind = db.get_bind()

    dialecto = (
        bind.dialect.name
        if bind is not None
        else ""
    )

    if dialecto != "postgresql":
        return

    chave = (
        f"{tenant_slug}|"
        f"{profissional_nome}|"
        f"{data_agendamento.isoformat()}"
    )

    db.execute(
        text(
            "SELECT pg_advisory_xact_lock("
            "hashtext(:chave)"
            ")"
        ),
        {
            "chave":
                chave,
        },
    )


def verificar_disponibilidade_e_bloquear(
    db: Session,
    tenant_slug: str,
    profissional_nome: str,
    data_agendamento: date,
    horario: str,
):
    """
    Verifica se já existe um agendamento iniciado no mesmo horário.

    Esta correção resolve o erro funcional imediato e inclui a data na busca.
    A proteção definitiva contra concorrência será implementada posteriormente
    no PostgreSQL com uma restrição de integridade.
    """
    return (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug == tenant_slug,
            models.Agendamento.profissional == profissional_nome,
            models.Agendamento.data == data_agendamento,
            models.Agendamento.horario == horario,
        )
        .with_for_update()
        .first()
    )


def salvar_agendamento(
    db: Session,
    agendamento: models.Agendamento,
):
    try:
        db.add(agendamento)
        db.commit()
        db.refresh(agendamento)
        return agendamento

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Este horário acabou de ser reservado por outra pessoa.",
        )