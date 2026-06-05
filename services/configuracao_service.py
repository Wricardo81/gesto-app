from sqlalchemy.orm import Session
from repositories import configuracao_repository
import models
from pydantic import BaseModel

class NovaConfiguracao(BaseModel):
    abertura: int
    fechamento: int
    cor_tema: str 
    cor_fundo: str
    endereco: str
    logo_url: str
    instrucoes: str

def atualizar_configuracoes(db: Session, tenant_slug: str, dados: NovaConfiguracao):
    config_atual = configuracao_repository.obter_configuracao(db, tenant_slug)
    
    if config_atual is None:
        nova = models.ConfiguracaoAgenda(
            barbearia_slug=tenant_slug, hora_abertura=dados.abertura, hora_fechamento=dados.fechamento, 
            cor_tema=dados.cor_tema, cor_fundo=dados.cor_fundo, endereco=dados.endereco, 
            logo_url=dados.logo_url, instrucoes=dados.instrucoes
        )
        configuracao_repository.salvar_configuracao(db, nova)
    else:
        config_atual.hora_abertura = dados.abertura
        config_atual.hora_fechamento = dados.fechamento
        config_atual.cor_tema = dados.cor_tema
        config_atual.cor_fundo = dados.cor_fundo
        config_atual.endereco = dados.endereco
        config_atual.logo_url = dados.logo_url
        config_atual.instrucoes = dados.instrucoes
        db.commit()
        
    return {"mensagem": "Configurações atualizadas!"}

def ler_configuracoes(db: Session, tenant_slug: str):
    config_atual = configuracao_repository.obter_configuracao(db, tenant_slug)
    
    if config_atual is None: 
        return {
            "abertura": 9, "fechamento": 18, "cor_tema": "#f59e0b", 
            "cor_fundo": "#0f172a", "endereco": "", "logo_url": "", "instrucoes": ""
        }
        
    return {
        "abertura": config_atual.hora_abertura, "fechamento": config_atual.hora_fechamento, 
        "cor_tema": config_atual.cor_tema, "cor_fundo": config_atual.cor_fundo,
        "endereco": config_atual.endereco, "logo_url": config_atual.logo_url,
        "instrucoes": config_atual.instrucoes
    }