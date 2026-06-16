from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import SessaoLocal
from services import configuracao_service
from security import validar_tenant_logado


router = APIRouter()


def get_db():
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/api/{tenant_slug}/configuracoes")
def ler_configuracoes(
    tenant_slug: str,
    db: Session = Depends(get_db),
):
    return configuracao_service.ler_configuracoes(
        db,
        tenant_slug,
    )


@router.post("/api/{tenant_slug}/configuracoes")
def salvar_configuracoes(
    tenant_slug: str,
    dados: configuracao_service.NovaConfiguracao,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
):
    return configuracao_service.atualizar_configuracoes(
        db,
        tenant_slug,
        dados,
    )