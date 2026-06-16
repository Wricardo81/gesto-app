from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessaoLocal
from services import profissional_service
from security import obter_usuario_logado
from security import validar_tenant_logado

router = APIRouter()

def get_db():
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/{tenant_slug}/profissionais")
def cadastrar_profissional(
    tenant_slug: str, 
    dados: profissional_service.NovoProfissional, 
    db: Session = Depends(get_db),
    usuario_logado: str = Depends(obter_usuario_logado), # PORTA TRANCADA
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
):
    # Proteção de Inquilino Cruzado
    if usuario_logado != tenant_slug:
        raise HTTPException(status_code=403, detail="Você não tem permissão para alterar esta barbearia.")
        
    return profissional_service.cadastrar_novo_profissional(db, tenant_slug, dados)

@router.get("/api/{tenant_slug}/profissionais")
def listar_profissionais(tenant_slug: str, db: Session = Depends(get_db)):
    # O GET não precisa do cadeado de segurança, pois o cliente final 
    # precisa ver a lista de barbeiros para conseguir agendar!
    return profissional_service.listar_profissionais(db, tenant_slug)

@router.delete("/api/{tenant_slug}/profissionais/{prof_id}")
def remover_profissional(
    tenant_slug: str, 
    prof_id: int, 
    db: Session = Depends(get_db),
    usuario_logado: str = Depends(obter_usuario_logado), # PORTA TRANCADA
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
):
    # Proteção de Inquilino Cruzado
    if usuario_logado != tenant_slug:
        raise HTTPException(status_code=403, detail="Você não tem permissão para alterar esta barbearia.")
        
    return profissional_service.deletar_profissional(db, prof_id, tenant_slug)