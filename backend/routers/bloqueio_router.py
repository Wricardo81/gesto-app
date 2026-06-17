from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from security import validar_tenant_logado


router = APIRouter(
    prefix="/api",
    tags=["Bloqueios de Agenda"],
)


def get_db():
    db = SessaoLocal()

    try:
        yield db
    finally:
        db.close()


class NovoBloqueioAgenda(BaseModel):
    profissional: str | None = None
    data: str
    horario_inicio: str | None = None
    horario_fim: str | None = None
    dia_inteiro: bool = False
    motivo: str | None = None


def serializar_bloqueio(
    bloqueio: models.BloqueioAgenda,
) -> dict:
    return {
        "id": bloqueio.id,
        "barbearia_slug": bloqueio.barbearia_slug,
        "profissional": bloqueio.profissional,
        "data": bloqueio.data.isoformat() if bloqueio.data else None,
        "horario_inicio": bloqueio.horario_inicio,
        "horario_fim": bloqueio.horario_fim,
        "dia_inteiro": bloqueio.dia_inteiro,
        "motivo": bloqueio.motivo,
        "criado_em": bloqueio.criado_em.isoformat() if bloqueio.criado_em else None,
    }


def converter_data(data_texto: str) -> date:
    try:
        return datetime.strptime(
            data_texto,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Data inválida. Use o formato YYYY-MM-DD.",
        )


def converter_horario(horario: str) -> datetime:
    try:
        return datetime.strptime(
            horario,
            "%H:%M",
        )

    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Horário inválido. Use o formato HH:MM.",
        )


def normalizar_profissional(
    profissional: str | None,
) -> str | None:
    texto = str(profissional or "").strip()

    if not texto:
        return None

    if texto.lower() in [
        "todos",
        "todos os profissionais",
        "todos profissionais",
    ]:
        return None

    return texto


@router.get("/{tenant_slug}/admin/bloqueios")
def listar_bloqueios_admin(
    tenant_slug: str,
    data: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    consulta = db.query(models.BloqueioAgenda).filter(
        models.BloqueioAgenda.barbearia_slug == tenant_slug
    )

    if data:
        data_filtro = converter_data(data)
        consulta = consulta.filter(
            models.BloqueioAgenda.data == data_filtro
        )

    bloqueios = (
        consulta
        .order_by(
            models.BloqueioAgenda.data.desc(),
            models.BloqueioAgenda.horario_inicio.asc(),
        )
        .all()
    )

    return [
        serializar_bloqueio(bloqueio)
        for bloqueio in bloqueios
    ]


@router.post("/{tenant_slug}/admin/bloqueios")
def criar_bloqueio_admin(
    tenant_slug: str,
    dados: NovoBloqueioAgenda,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    data_bloqueio = converter_data(dados.data)

    if data_bloqueio < date.today():
        raise HTTPException(
            status_code=422,
            detail="Não é possível criar bloqueio para data passada.",
        )

    profissional = normalizar_profissional(
        dados.profissional
    )

    if profissional:
        profissional_existe = (
            db.query(models.Profissional)
            .filter(
                models.Profissional.barbearia_slug == tenant_slug,
                models.Profissional.nome == profissional,
            )
            .first()
        )

        if not profissional_existe:
            raise HTTPException(
                status_code=404,
                detail="Profissional não encontrado neste estabelecimento.",
            )

    horario_inicio = None
    horario_fim = None

    if not dados.dia_inteiro:
        if not dados.horario_inicio or not dados.horario_fim:
            raise HTTPException(
                status_code=422,
                detail="Informe horário inicial e final para bloqueio parcial.",
            )

        inicio = converter_horario(dados.horario_inicio)
        fim = converter_horario(dados.horario_fim)

        if fim <= inicio:
            raise HTTPException(
                status_code=422,
                detail="O horário final deve ser maior que o horário inicial.",
            )

        horario_inicio = dados.horario_inicio
        horario_fim = dados.horario_fim

    bloqueio = models.BloqueioAgenda(
        barbearia_slug=tenant_slug,
        profissional=profissional,
        data=data_bloqueio,
        horario_inicio=horario_inicio,
        horario_fim=horario_fim,
        dia_inteiro=dados.dia_inteiro,
        motivo=dados.motivo,
    )

    db.add(bloqueio)
    db.commit()
    db.refresh(bloqueio)

    return {
        "mensagem": "Bloqueio criado com sucesso.",
        "bloqueio": serializar_bloqueio(bloqueio),
    }


@router.delete("/{tenant_slug}/admin/bloqueios/{bloqueio_id}")
def remover_bloqueio_admin(
    tenant_slug: str,
    bloqueio_id: int,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    bloqueio = (
        db.query(models.BloqueioAgenda)
        .filter(
            models.BloqueioAgenda.id == bloqueio_id,
            models.BloqueioAgenda.barbearia_slug == tenant_slug,
        )
        .first()
    )

    if not bloqueio:
        raise HTTPException(
            status_code=404,
            detail="Bloqueio não encontrado.",
        )

    db.delete(bloqueio)
    db.commit()

    return {
        "mensagem": "Bloqueio removido com sucesso.",
    }