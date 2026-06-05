from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessaoLocal
from services import profissional_service

router = APIRouter()

# Injeção de Dependência: A forma profissional de lidar com conexões no FastAPI
def get_db():
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close() # O 'finally' garante que o banco SEMPRE será fechado, mesmo com erros.

@router.get("/api/{tenant_slug}/profissionais")
def listar_profissionais(tenant_slug: str, db: Session = Depends(get_db)):
    """Recebe a requisição HTTP, delega para o service, e devolve a resposta."""
    equipe = profissional_service.listar_profissionais(db, tenant_slug)
    return equipe

# Adicione no final do arquivo existente:

@router.post("/api/{tenant_slug}/profissionais")
def cadastrar_profissional(tenant_slug: str, dados: profissional_service.NovoProfissional, db: Session = Depends(get_db)):
    return profissional_service.cadastrar_novo_profissional(db, tenant_slug, dados)

@router.delete("/api/{tenant_slug}/profissionais/{prof_id}")
def remover_profissional(tenant_slug: str, prof_id: int, db: Session = Depends(get_db)):
    return profissional_service.deletar_profissional(db, prof_id, tenant_slug)