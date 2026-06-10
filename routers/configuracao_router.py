from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessaoLocal
from services import configuracao_service
from security import obter_usuario_logado  # IMPORTAMOS O NOSSO SEGURANÇA

router = APIRouter()

def get_db():
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/{tenant_slug}/configuracoes")
def salvar_configuracoes(
    tenant_slug: str, 
    dados: configuracao_service.NovaConfiguracao, 
    db: Session = Depends(get_db),
    usuario_logado: str = Depends(obter_usuario_logado) # <--- O CADEADO ESTÁ AQUI
):
    # Proteção de Inquilino Cruzado: 
    # O token diz que o usuário é 'barbearia-a', mas ele tentou alterar a 'barbearia-b' (tenant_slug)
    if usuario_logado != tenant_slug:
        raise HTTPException(status_code=403, detail="Você não tem permissão para editar outra barbearia.")
        
    return configuracao_service.atualizar_configuracoes(db, tenant_slug, dados)

@router.get("/api/{tenant_slug}/configuracoes")
def ler_configuracoes(tenant_slug: str, db: Session = Depends(get_db)):
    # O GET costuma ser público para que o cliente da barbearia veja o logo e horários,
    # então NÃO colocamos o segurança aqui!
    return configuracao_service.ler_configuracoes(db, tenant_slug)