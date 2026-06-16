from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Float,
    Integer,
    String,
    UniqueConstraint,
)

from database import Base


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
    barbearia_slug = Column(String, index=True)
    cliente_nome = Column(String)
    servico = Column(String)
    horario = Column(String)
    data = Column(Date)
    valor = Column(Float)
    profissional = Column(String)
    telefone_cliente = Column(String, default="")
    status = Column(String, default="confirmado", nullable=False, index=True)

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