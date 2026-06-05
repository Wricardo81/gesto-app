from sqlalchemy.orm import Session
from fastapi import HTTPException
from repositories import servico_repository
import models
from pydantic import BaseModel

# O modelo de dados esperado na requisição
class NovoServico(BaseModel):
    nome: str
    preco: float
    duracao: int 

def cadastrar_novo_servico(db: Session, tenant_slug: str, dados: NovoServico):
    novo_servico = models.ServicoBarbearia(
        barbearia_slug=tenant_slug, 
        nome=dados.nome, 
        preco=dados.preco, 
        duracao=dados.duracao
    )
    return servico_repository.criar_servico(db, novo_servico)

def listar_servicos(db: Session, tenant_slug: str):
    return servico_repository.buscar_servicos_por_tenant(db, tenant_slug)

def deletar_servico(db: Session, servico_id: int, tenant_slug: str):
    sucesso = servico_repository.remover_servico(db, servico_id, tenant_slug)
    if not sucesso:
        # A regra de negócio diz que se não achou, retorna erro 404
        raise HTTPException(status_code=404, detail="Serviço não encontrado.")
    return {"mensagem": "Serviço removido!"}