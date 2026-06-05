from sqlalchemy.orm import Session
from repositories import profissional_repository
from fastapi import HTTPException
from pydantic import BaseModel


class NovoProfissional(BaseModel):
    nome: str

def listar_profissionais(db: Session, tenant_slug: str):
    """
    Aqui entram as regras de negócio. 
    Se precisássemos verificar se a barbearia está com a assinatura ativa 
    antes de listar a equipe, a lógica ficaria aqui.
    """
    return profissional_repository.buscar_profissionais_por_tenant(db, tenant_slug)



# Adicione no final do arquivo existente:
def cadastrar_novo_profissional(db: Session, tenant_slug: str, dados: NovoProfissional):
    novo_prof = models.Profissional(barbearia_slug=tenant_slug, nome=dados.nome)
    return profissional_repository.criar_profissional(db, novo_prof)

def deletar_profissional(db: Session, prof_id: int, tenant_slug: str):
    sucesso = profissional_repository.remover_profissional(db, prof_id, tenant_slug)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Profissional não encontrado.")
    return {"mensagem": "Profissional removido."}