from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessaoLocal
from services import servico_service

router = APIRouter()

def get_db():
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/{tenant_slug}/servicos")
def cadastrar_servico(tenant_slug: str, dados: servico_service.NovoServico, db: Session = Depends(get_db)):
    servico_service.cadastrar_novo_servico(db, tenant_slug, dados)
    return {"mensagem": "Serviço cadastrado!"}

@router.get("/api/{tenant_slug}/servicos")
def listar_servicos(tenant_slug: str, db: Session = Depends(get_db)):
    return servico_service.listar_servicos(db, tenant_slug)

@router.delete("/api/{tenant_slug}/servicos/{servico_id}")
def remover_servico(tenant_slug: str, servico_id: int, db: Session = Depends(get_db)):
    return servico_service.deletar_servico(db, servico_id, tenant_slug)