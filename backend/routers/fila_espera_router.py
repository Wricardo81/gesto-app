from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import SessaoLocal
from security import validar_tenant_logado
from services import fila_espera_service


router = APIRouter()


def get_db():
    db = SessaoLocal()

    try:
        yield db
    finally:
        db.close()


@router.post("/api/{tenant_slug}/fila-espera", status_code=201)
def criar_entrada_fila_espera_publica(
    tenant_slug: str,
    dados: fila_espera_service.EntradaFilaEsperaPublica,
    db: Session = Depends(get_db),
):
    return fila_espera_service.criar_entrada_fila_espera(
        db=db,
        tenant_slug=tenant_slug,
        dados=dados,
    )


@router.get("/api/{tenant_slug}/admin/fila-espera")
def listar_fila_espera_admin(
    tenant_slug: str,
    status: str | None = None,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    return {
        "fila_espera": fila_espera_service.listar_fila_espera(
            db=db,
            tenant_slug=tenant_slug,
            status=status,
        )
    }


@router.put("/api/{tenant_slug}/admin/fila-espera/{item_id}/status")
def atualizar_status_fila_espera_admin(
    tenant_slug: str,
    item_id: int,
    dados: fila_espera_service.AtualizacaoStatusFilaEspera,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    return {
        "mensagem": "Status da fila de espera atualizado com sucesso.",
        "item": fila_espera_service.atualizar_status_fila_espera(
            db=db,
            tenant_slug=tenant_slug,
            item_id=item_id,
            dados=dados,
        ),
    }
