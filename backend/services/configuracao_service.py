from sqlalchemy.orm import Session
from pydantic import BaseModel

import models
from repositories import configuracao_repository


class NovaConfiguracao(BaseModel):
    abertura: int
    fechamento: int

    cor_tema: str = "#f59e0b"
    cor_fundo: str = "#0f172a"

    endereco: str = ""
    logo_url: str | None = None
    logomarca_url: str | None = None
    instrucoes: str = ""

    telefone: str | None = None
    nome_publico: str | None = None

    limite_cancelamento_horas: int = 3

    whatsapp_comercial: str | None = None
    instagram_url: str | None = None
    facebook_url: str | None = None
    tiktok_url: str | None = None
    site_url: str | None = None
    google_maps_url: str | None = None

    mensagem_publica: str | None = None
    captar_whatsapp_lembretes: bool = True
    captar_whatsapp_promocoes: bool = False


def aplicar_dados_configuracao(
    configuracao: models.ConfiguracaoAgenda,
    dados: NovaConfiguracao,
) -> models.ConfiguracaoAgenda:
    limite_cancelamento = max(
        0,
        int(dados.limite_cancelamento_horas or 0),
    )

    configuracao.hora_abertura = dados.abertura
    configuracao.hora_fechamento = dados.fechamento

    configuracao.cor_tema = dados.cor_tema
    configuracao.cor_fundo = dados.cor_fundo

    configuracao.endereco = dados.endereco or ""
    configuracao.logo_url = dados.logo_url or ""
    configuracao.logomarca_url = dados.logomarca_url or ""
    configuracao.instrucoes = dados.instrucoes or ""

    configuracao.telefone = dados.telefone or ""
    configuracao.nome_publico = dados.nome_publico or ""

    configuracao.limite_cancelamento_horas = limite_cancelamento

    configuracao.whatsapp_comercial = dados.whatsapp_comercial or ""
    configuracao.instagram_url = dados.instagram_url or ""
    configuracao.facebook_url = dados.facebook_url or ""
    configuracao.tiktok_url = dados.tiktok_url or ""
    configuracao.site_url = dados.site_url or ""
    configuracao.google_maps_url = dados.google_maps_url or ""

    configuracao.mensagem_publica = dados.mensagem_publica or ""
    configuracao.captar_whatsapp_lembretes = dados.captar_whatsapp_lembretes
    configuracao.captar_whatsapp_promocoes = dados.captar_whatsapp_promocoes

    return configuracao


def atualizar_configuracoes(
    db: Session,
    tenant_slug: str,
    dados: NovaConfiguracao,
):
    config_atual = configuracao_repository.obter_configuracao(
        db,
        tenant_slug,
    )

    if config_atual is None:
        nova_configuracao = models.ConfiguracaoAgenda(
            barbearia_slug=tenant_slug,
        )

        aplicar_dados_configuracao(
            nova_configuracao,
            dados,
        )

        configuracao_repository.salvar_configuracao(
            db,
            nova_configuracao,
        )

    else:
        aplicar_dados_configuracao(
            config_atual,
            dados,
        )

        db.commit()

    return {
        "mensagem": "Configurações atualizadas!",
    }


def ler_configuracoes(
    db: Session,
    tenant_slug: str,
):
    config_atual = configuracao_repository.obter_configuracao(
        db,
        tenant_slug,
    )

    if config_atual is None:
        return {
            "abertura": 9,
            "fechamento": 18,
            "cor_tema": "#f59e0b",
            "cor_fundo": "#0f172a",
            "endereco": "",
            "logo_url": "",
            "logomarca_url": "",
            "instrucoes": "",
            "telefone": "",
            "nome_publico": "",
            "limite_cancelamento_horas": 3,
            "whatsapp_comercial": "",
            "instagram_url": "",
            "facebook_url": "",
            "tiktok_url": "",
            "site_url": "",
            "google_maps_url": "",
            "mensagem_publica": "",
            "captar_whatsapp_lembretes": True,
            "captar_whatsapp_promocoes": False,
        }

    return {
        "abertura": config_atual.hora_abertura,
        "fechamento": config_atual.hora_fechamento,

        "cor_tema": config_atual.cor_tema,
        "cor_fundo": config_atual.cor_fundo,

        "endereco": config_atual.endereco,
        "logo_url": config_atual.logo_url,
        "logomarca_url": config_atual.logomarca_url,
        "instrucoes": config_atual.instrucoes,

        "telefone": config_atual.telefone,
        "nome_publico": config_atual.nome_publico,

        "limite_cancelamento_horas": (
            config_atual.limite_cancelamento_horas
            if config_atual.limite_cancelamento_horas is not None
            else 3
        ),

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