from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import SessaoLocal
from services import servico_service
from security import validar_tenant_logado


router = APIRouter()


def get_db():
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/api/{tenant_slug}/servicos")
def listar_servicos(
    tenant_slug: str,
    db: Session = Depends(get_db),
):
    return servico_service.listar_servicos(
        db,
        tenant_slug,
    )


@router.post("/api/{tenant_slug}/servicos")
def cadastrar_servico(
    tenant_slug: str,
    dados: servico_service.NovoServico,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
):
    return servico_service.cadastrar_novo_servico(
        db,
        tenant_slug,
        dados,
    )


@router.delete("/api/{tenant_slug}/servicos/{servico_id}")
def remover_servico(
    tenant_slug: str,
    servico_id: int,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
):
    return servico_service.deletar_servico(
        db,
        servico_id,
        tenant_slug,
    )