from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

import models
from database import SessaoLocal
from security import (
    obter_saas_admin_logado,
    validar_tenant_logado,
)


router = APIRouter(
    tags=["Avisos da Plataforma"],
)


TIPOS_AVISO_VALIDOS = {
    "info",
    "atualizacao",
    "promocao",
    "manutencao",
    "instabilidade",
    "financeiro",
    "urgente",
}


def get_db():
    db = SessaoLocal()

    try:
        yield db

    finally:
        db.close()


class CriacaoAvisoPlataforma(BaseModel):
    titulo: str = Field(
        min_length=3,
        max_length=160,
    )

    mensagem: str = Field(
        min_length=3,
        max_length=3000,
    )

    tipo: str = "info"

    tenant_slug: str | None = None

    global_para_todos: bool = True
    fixado: bool = False
    dispensavel: bool = True
    ativo: bool = True

    data_inicio: str | None = None
    data_fim: str | None = None


class AtualizacaoStatusAviso(BaseModel):
    ativo: bool


def converter_data_aviso(
    data_texto: str | None,
) -> date | None:
    if not data_texto:
        return None

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


def normalizar_tipo_aviso(tipo: str) -> str:
    tipo_normalizado = str(
        tipo or "info"
    ).strip().lower()

    if tipo_normalizado not in TIPOS_AVISO_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail="Tipo de aviso inválido.",
        )

    return tipo_normalizado


def serializar_aviso(
    aviso: models.AvisoPlataforma,
) -> dict:
    return {
        "id": aviso.id,
        "titulo": aviso.titulo,
        "mensagem": aviso.mensagem,
        "tipo": aviso.tipo,
        "tenant_slug": aviso.tenant_slug,
        "global_para_todos": aviso.global_para_todos,
        "ativo": aviso.ativo,
        "fixado": aviso.fixado,
        "dispensavel": aviso.dispensavel,
        "data_inicio": (
            aviso.data_inicio.isoformat()
            if aviso.data_inicio
            else None
        ),
        "data_fim": (
            aviso.data_fim.isoformat()
            if aviso.data_fim
            else None
        ),
        "criado_em": (
            aviso.criado_em.isoformat()
            if aviso.criado_em
            else None
        ),
    }


@router.get("/api/saas/avisos")
def listar_avisos_saas(
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    avisos = (
        db.query(models.AvisoPlataforma)
        .order_by(
            models.AvisoPlataforma.id.desc()
        )
        .all()
    )

    return [
        serializar_aviso(aviso)
        for aviso in avisos
    ]


@router.post(
    "/api/saas/avisos",
    status_code=201,
)
def criar_aviso_saas(
    dados: CriacaoAvisoPlataforma,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    tipo = normalizar_tipo_aviso(
        dados.tipo
    )

    data_inicio = converter_data_aviso(
        dados.data_inicio
    )

    data_fim = converter_data_aviso(
        dados.data_fim
    )

    if (
        data_inicio
        and data_fim
        and data_fim < data_inicio
    ):
        raise HTTPException(
            status_code=422,
            detail="A data final não pode ser anterior à data inicial.",
        )

    tenant_slug = (
        dados.tenant_slug.strip().lower()
        if dados.tenant_slug
        else None
    )

    if not dados.global_para_todos:
        if not tenant_slug:
            raise HTTPException(
                status_code=422,
                detail="Informe o tenant_slug para aviso específico.",
            )

        tenant_existe = (
            db.query(models.Barbearia)
            .filter(
                models.Barbearia.slug == tenant_slug
            )
            .first()
        )

        if not tenant_existe:
            raise HTTPException(
                status_code=404,
                detail="Tenant informado não encontrado.",
            )

    aviso = models.AvisoPlataforma(
        titulo=dados.titulo.strip(),
        mensagem=dados.mensagem.strip(),
        tipo=tipo,
        tenant_slug=tenant_slug,
        global_para_todos=dados.global_para_todos,
        fixado=dados.fixado,
        dispensavel=dados.dispensavel,
        ativo=dados.ativo,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    db.add(aviso)
    db.commit()
    db.refresh(aviso)

    return {
        "mensagem": "Aviso criado com sucesso.",
        "aviso": serializar_aviso(aviso),
    }


@router.put("/api/saas/avisos/{aviso_id}/status")
def alterar_status_aviso_saas(
    aviso_id: int,
    dados: AtualizacaoStatusAviso,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    aviso = (
        db.query(models.AvisoPlataforma)
        .filter(
            models.AvisoPlataforma.id == aviso_id
        )
        .first()
    )

    if not aviso:
        raise HTTPException(
            status_code=404,
            detail="Aviso não encontrado.",
        )

    aviso.ativo = dados.ativo

    db.commit()
    db.refresh(aviso)

    return {
        "mensagem": "Status do aviso atualizado com sucesso.",
        "aviso": serializar_aviso(aviso),
    }


@router.get("/api/{tenant_slug}/admin/avisos")
def listar_avisos_admin(
    tenant_slug: str,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        validar_tenant_logado
    ),
):
    hoje = date.today()

    avisos_dispensados = (
        db.query(models.AvisoDispensadoTenant.aviso_id)
        .filter(
            models.AvisoDispensadoTenant.tenant_slug == tenant_slug
        )
        .all()
    )

    ids_dispensados = {
        item[0]
        for item in avisos_dispensados
    }

    avisos = (
        db.query(models.AvisoPlataforma)
        .filter(
            models.AvisoPlataforma.ativo == True,
            or_(
                models.AvisoPlataforma.global_para_todos == True,
                models.AvisoPlataforma.tenant_slug == tenant_slug,
            ),
            or_(
                models.AvisoPlataforma.data_inicio == None,
                models.AvisoPlataforma.data_inicio <= hoje,
            ),
            or_(
                models.AvisoPlataforma.data_fim == None,
                models.AvisoPlataforma.data_fim >= hoje,
            ),
        )
        .order_by(
            models.AvisoPlataforma.fixado.desc(),
            models.AvisoPlataforma.id.desc(),
        )
        .all()
    )

    return [
        serializar_aviso(aviso)
        for aviso in avisos
        if not (
            aviso.dispensavel
            and aviso.id in ids_dispensados
        )
    ]


@router.post("/api/{tenant_slug}/admin/avisos/{aviso_id}/dispensar")
def dispensar_aviso_admin(
    tenant_slug: str,
    aviso_id: int,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        validar_tenant_logado
    ),
):
    aviso = (
        db.query(models.AvisoPlataforma)
        .filter(
            models.AvisoPlataforma.id == aviso_id,
            models.AvisoPlataforma.ativo == True,
        )
        .first()
    )

    if not aviso:
        raise HTTPException(
            status_code=404,
            detail="Aviso não encontrado.",
        )

    pertence_ao_tenant = (
        aviso.global_para_todos
        or aviso.tenant_slug == tenant_slug
    )

    if not pertence_ao_tenant:
        raise HTTPException(
            status_code=403,
            detail="Este aviso não pertence a este estabelecimento.",
        )

    if not aviso.dispensavel:
        raise HTTPException(
            status_code=403,
            detail="Este aviso não pode ser dispensado.",
        )

    registro = models.AvisoDispensadoTenant(
        aviso_id=aviso.id,
        tenant_slug=tenant_slug,
    )

    try:
        db.add(registro)
        db.commit()

    except IntegrityError:
        db.rollback()

    return {
        "mensagem": "Aviso dispensado com sucesso.",
        "aviso_id": aviso.id,
        "tenant_slug": tenant_slug,
    }