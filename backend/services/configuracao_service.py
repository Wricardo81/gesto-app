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
    nome_publico: str | None = None
    logo_url: str | None = None
    logomarca_url: str | None = None

    whatsapp_comercial: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    tiktok_url: str | None = None
    site_url: str | None = None
    google_maps_url: str | None = None

    mensagem_publica: str | None = None
    captar_whatsapp_lembretes: bool = True
    captar_whatsapp_promocoes: bool = False

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
        config_atual.nome_publico = dados.nome_publico
        config_atual.logo_url = dados.logo_url
        config_atual.logomarca_url = dados.logomarca_url

        config_atual.whatsapp_comercial = dados.whatsapp_comercial
        config_atual.instagram_url = dados.instagram_url
        config_atual.facebook_url = dados.facebook_url
        config_atual.tiktok_url = dados.tiktok_url
        config_atual.site_url = dados.site_url
        config_atual.google_maps_url = dados.google_maps_url

        config_atual.mensagem_publica = dados.mensagem_publica
        config_atual.captar_whatsapp_lembretes = dados.captar_whatsapp_lembretes
        config_atual.captar_whatsapp_promocoes = dados.captar_whatsapp_promocoes
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
        "instrucoes": config_atual.instrucoes,
        "telefone": config_atual.telefone,
        "nome_publico": config_atual.nome_publico,
        "logo_url": config_atual.logo_url,
        "logomarca_url": config_atual.logomarca_url,

        "whatsapp_comercial": config_atual.whatsapp_comercial,
        "instagram_url": config_atual.instagram_url,
        "facebook_url": config_atual.facebook_url,
        "tiktok_url": config_atual.tiktok_url,
        "site_url": config_atual.site_url,
        "google_maps_url": config_atual.google_maps_url,

        "mensagem_publica": config_atual.mensagem_publica,
        "captar_whatsapp_lembretes": config_atual.captar_whatsapp_lembretes,
        "captar_whatsapp_promocoes": config_atual.captar_whatsapp_promocoes,
    }