from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from security import (
    obter_saas_admin_logado,
    validar_tenant_logado,
)


router = APIRouter(
    tags=["Suporte e Chamados"],
)


TIPOS_CHAMADO_VALIDOS = {
    "erro",
    "bug",
    "sugestao",
    "elogio",
    "outro",
}


STATUS_CHAMADO_VALIDOS = {
    "aberto",
    "em_analise",
    "resolvido",
    "fechado",
}


def get_db():
    db = SessaoLocal()

    try:
        yield db

    finally:
        db.close()


class CriacaoChamadoSuporte(BaseModel):
    tipo: str = "erro"

    titulo: str = Field(
        min_length=3,
        max_length=160,
    )

    descricao: str = Field(
        min_length=5,
        max_length=5000,
    )

    pagina_origem: str | None = None
    contato_nome: str | None = None
    contato_email: EmailStr | None = None


class AtualizacaoStatusChamado(BaseModel):
    status: str
    resposta_suporte: str | None = None


def normalizar_tipo_chamado(tipo: str) -> str:
    tipo_normalizado = str(
        tipo or "erro"
    ).strip().lower()

    if tipo_normalizado not in TIPOS_CHAMADO_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail="Tipo de chamado inválido.",
        )

    return tipo_normalizado


def normalizar_status_chamado(status: str) -> str:
    status_normalizado = str(
        status or "aberto"
    ).strip().lower()

    if status_normalizado not in STATUS_CHAMADO_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail="Status de chamado inválido.",
        )

    return status_normalizado


def serializar_chamado(
    chamado: models.ChamadoSuporte,
) -> dict:
    return {
        "id": chamado.id,
        "tenant_slug": chamado.tenant_slug,
        "tipo": chamado.tipo,
        "titulo": chamado.titulo,
        "descricao": chamado.descricao,
        "status": chamado.status,
        "pagina_origem": chamado.pagina_origem,
        "contato_nome": chamado.contato_nome,
        "contato_email": chamado.contato_email,
        "resposta_suporte": chamado.resposta_suporte,
        "criado_em": (
            chamado.criado_em.isoformat()
            if chamado.criado_em
            else None
        ),
        "atualizado_em": (
            chamado.atualizado_em.isoformat()
            if chamado.atualizado_em
            else None
        ),
        "resolvido_em": (
            chamado.resolvido_em.isoformat()
            if chamado.resolvido_em
            else None
        ),
    }


def buscar_tenant_ou_404(
    db: Session,
    tenant_slug: str,
) -> models.Barbearia:
    tenant = (
        db.query(models.Barbearia)
        .filter(
            models.Barbearia.slug == tenant_slug
        )
        .first()
    )

    if not tenant:
        raise HTTPException(
            status_code=404,
            detail="Empresa não encontrada.",
        )

    return tenant


@router.post(
    "/api/{tenant_slug}/admin/suporte/chamados",
    status_code=201,
)
def criar_chamado_admin(
    tenant_slug: str,
    dados: CriacaoChamadoSuporte,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        validar_tenant_logado
    ),
):
    buscar_tenant_ou_404(
        db,
        tenant_slug,
    )

    tipo = normalizar_tipo_chamado(
        dados.tipo
    )

    chamado = models.ChamadoSuporte(
        tenant_slug=tenant_slug,
        tipo=tipo,
        titulo=dados.titulo.strip(),
        descricao=dados.descricao.strip(),
        status="aberto",
        pagina_origem=(
            dados.pagina_origem.strip()
            if dados.pagina_origem
            else None
        ),
        contato_nome=(
            dados.contato_nome.strip()
            if dados.contato_nome
            else None
        ),
        contato_email=(
            str(dados.contato_email).strip().lower()
            if dados.contato_email
            else None
        ),
    )

    db.add(chamado)
    db.commit()
    db.refresh(chamado)

    return {
        "mensagem": "Chamado aberto com sucesso.",
        "chamado": serializar_chamado(chamado),
    }


@router.get("/api/{tenant_slug}/admin/suporte/chamados")
def listar_chamados_admin(
    tenant_slug: str,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        validar_tenant_logado
    ),
):
    buscar_tenant_ou_404(
        db,
        tenant_slug,
    )

    chamados = (
        db.query(models.ChamadoSuporte)
        .filter(
            models.ChamadoSuporte.tenant_slug == tenant_slug
        )
        .order_by(
            models.ChamadoSuporte.id.desc()
        )
        .all()
    )

    return [
        serializar_chamado(chamado)
        for chamado in chamados
    ]


@router.get("/api/saas/suporte/chamados")
def listar_chamados_saas(
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    chamados = (
        db.query(models.ChamadoSuporte)
        .order_by(
            models.ChamadoSuporte.id.desc()
        )
        .all()
    )

    return [
        serializar_chamado(chamado)
        for chamado in chamados
    ]


@router.put("/api/saas/suporte/chamados/{chamado_id}/status")
def atualizar_status_chamado_saas(
    chamado_id: int,
    dados: AtualizacaoStatusChamado,
    db: Session = Depends(get_db),
    _usuario_admin: str = Depends(
        obter_saas_admin_logado
    ),
):
    chamado = (
        db.query(models.ChamadoSuporte)
        .filter(
            models.ChamadoSuporte.id == chamado_id
        )
        .first()
    )

    if not chamado:
        raise HTTPException(
            status_code=404,
            detail="Chamado não encontrado.",
        )

    status = normalizar_status_chamado(
        dados.status
    )

    chamado.status = status
    chamado.atualizado_em = datetime.utcnow()

    if dados.resposta_suporte is not None:
        chamado.resposta_suporte = dados.resposta_suporte.strip() or None

    if status in {"resolvido", "fechado"}:
        chamado.resolvido_em = datetime.utcnow()
    else:
        chamado.resolvido_em = None

    db.commit()
    db.refresh(chamado)

    return {
        "mensagem": "Status do chamado atualizado com sucesso.",
        "chamado": serializar_chamado(chamado),
    }