from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import SessaoLocal
from security import (
    obter_contexto_usuario_logado,
    validar_tenant_logado,
)
from services import comissao_service


router = APIRouter()


def get_db():
    db = SessaoLocal()

    try:
        yield db
    finally:
        db.close()


@router.get("/api/{tenant_slug}/comissoes/pendentes")
def listar_comissoes_pendentes(
    tenant_slug: str,
    profissional_nome: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
    _contexto_usuario: dict = Depends(
        obter_contexto_usuario_logado
    ),
):
    return comissao_service.listar_comissoes_pendentes(
        db=db,
        tenant_slug=tenant_slug,
        profissional_nome=profissional_nome,
    )


@router.post("/api/{tenant_slug}/repasses")
def registrar_repasse_profissional(
    tenant_slug: str,
    dados: comissao_service.NovoRepasseProfissional,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
    contexto_usuario: dict = Depends(
        obter_contexto_usuario_logado
    ),
):
    registrado_por = (
        contexto_usuario.get("email")
        or contexto_usuario.get("nome")
        or contexto_usuario.get("sub")
    )

    try:
        return comissao_service.registrar_repasse_profissional(
            db=db,
            tenant_slug=tenant_slug,
            dados=dados,
            registrado_por=registrado_por,
        )

    except ValueError as exc:
        db.rollback()

        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )
