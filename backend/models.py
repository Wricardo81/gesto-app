from sqlalchemy import Boolean, Column, Date, DateTime, Float, Integer, String, UniqueConstraint

from database import Base
from datetime import datetime


# ==========================================
# 0. TABELA MESTRE DE CLIENTES (O SAAS)
# ==========================================
class Barbearia(Base):
    __tablename__ = "barbearias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, index=True)
    slug = Column(String, unique=True, index=True)
    plano_ativo = Column(Boolean, default=False)
    email = Column(String, unique=True, index=True, nullable=True)
    senha_hash = Column(String, nullable=True)

    plano_nome = Column(String, default="Profissional", nullable=False)
    valor_mensal = Column(Float, default=99.0, nullable=False)

    status_pagamento = Column(String, default="em_dia", nullable=False)
    vencimento_plano = Column(Date, nullable=True)
    dias_tolerancia = Column(Integer, default=3, nullable=False)

    ultimo_pagamento_em = Column(DateTime, nullable=True)


# ==========================================
# 1. TABELA DE AGENDAMENTOS
# ==========================================
class Agendamento(Base):
    __tablename__ = "agendamentos"

    __table_args__ = (
        UniqueConstraint(
            "barbearia_slug",
            "profissional",
            "data",
            "horario",
            name="uq_agendamentos_slot_exato",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    codigo_publico = Column(String, unique=True, index=True, nullable=True)
    barbearia_slug = Column(String, index=True)
    cliente_nome = Column(String)
    servico = Column(String)
    horario = Column(String)
    data = Column(Date)
    valor = Column(Float)
    profissional = Column(String)
    telefone_cliente = Column(String, default="")
    status = Column(String, default="confirmado", nullable=False, index=True)

    motivo_cancelamento = Column(String, nullable=True)
    cancelado_por = Column(String, nullable=True)
    cancelado_em = Column(DateTime, nullable=True)
    observacao_interna = Column(String, nullable=True)

    aceita_lembrete_whatsapp = Column(Boolean, default=True)
    aceita_promocoes_whatsapp = Column(Boolean, default=False)


# ==========================================
# 2. TABELA DE SERVIÇOS
# ==========================================
class ServicoBarbearia(Base):
    __tablename__ = "servicos"

    id = Column(Integer, primary_key=True, index=True)
    barbearia_slug = Column(String, index=True)
    nome = Column(String)
    preco = Column(Float)
    duracao = Column(Integer)


# ==========================================
# 3. TABELA DE CONFIGURAÇÕES
# ==========================================
class ConfiguracaoAgenda(Base):
    __tablename__ = "configuracoes"

    id = Column(Integer, primary_key=True, index=True)
    barbearia_slug = Column(String, index=True)

    hora_abertura = Column(Integer, default=9)
    hora_fechamento = Column(Integer, default=18)
    limite_cancelamento_horas = Column(Integer, default=3, nullable=False)
    cor_tema = Column(String, default="#f59e0b")
    cor_fundo = Column(String, default="#0f172a")
    endereco = Column(String, default="")
    logo_url = Column(String, default="")
    instrucoes = Column(String, default="")
    telefone = Column(String, default="")

    nome_publico = Column(String, nullable=True)
    logomarca_url = Column(String, nullable=True)

    whatsapp_comercial = Column(String, nullable=True)
    instagram_url = Column(String, nullable=True)
    facebook_url = Column(String, nullable=True)
    tiktok_url = Column(String, nullable=True)
    site_url = Column(String, nullable=True)
    google_maps_url = Column(String, nullable=True)

    mensagem_publica = Column(String, nullable=True)
    captar_whatsapp_lembretes = Column(Boolean, default=True)
    captar_whatsapp_promocoes = Column(Boolean, default=False)


# ==========================================
# 4. TABELA DA EQUIPE
# ==========================================
class Profissional(Base):
    __tablename__ = "profissionais"

    id = Column(Integer, primary_key=True, index=True)
    barbearia_slug = Column(String, index=True)
    nome = Column(String)

class BloqueioAgenda(Base):
    __tablename__ = "bloqueios_agenda"

    id = Column(Integer, primary_key=True, index=True)

    barbearia_slug = Column(String, index=True, nullable=False)

    # Se profissional for None ou vazio, o bloqueio vale para todos.
    profissional = Column(String, index=True, nullable=True)

    data = Column(Date, index=True, nullable=False)

    # Para bloqueio parcial.
    horario_inicio = Column(String, nullable=True)
    horario_fim = Column(String, nullable=True)

    # Se True, bloqueia o dia inteiro.
    dia_inteiro = Column(Boolean, default=False, nullable=False)

    motivo = Column(String, nullable=True)

    criado_em = Column(DateTime, default=datetime.utcnow, nullable=False)