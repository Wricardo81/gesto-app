from datetime import date
from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
import models


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