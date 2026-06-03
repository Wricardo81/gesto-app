from sqlalchemy import Column, Integer, String, Float, Boolean
from database import Base

# ==========================================
# 0. TABELA MESTRE DE CLIENTES (O SAAS)
# ==========================================
class Barbearia(Base):
    __tablename__ = "barbearias"
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String) # Ex: "Barbearia do Marcos"
    slug = Column(String, unique=True, index=True) # Ex: "barbearia-do-marcos"
    plano_ativo = Column(Boolean, default=True) # Gatilho para bloquear por falta de pagamento!

# ==========================================
# 1. TABELA DE AGENDAMENTOS
# ==========================================
class Agendamento(Base):
    __tablename__ = "agendamentos"
    id = Column(Integer, primary_key=True, index=True)
    barbearia_slug = Column(String, index=True) # <-- A ETIQUETA DA EMPRESA
    cliente_nome = Column(String)
    servico = Column(String)
    horario = Column(String)
    valor = Column(Float)
    profissional = Column(String)

# ==========================================
# 2. TABELA DE SERVIÇOS
# ==========================================
class ServicoBarbearia(Base):
    __tablename__ = "servicos"
    id = Column(Integer, primary_key=True, index=True)
    barbearia_slug = Column(String, index=True) # <-- A ETIQUETA DA EMPRESA
    nome = Column(String)  
    preco = Column(Float)
    duracao = Column(Integer)

# ==========================================
# 3. TABELA DE CONFIGURAÇÕES
# ==========================================
class ConfiguracaoAgenda(Base):
    __tablename__ = "configuracoes"
    id = Column(Integer, primary_key=True, index=True)
    barbearia_slug = Column(String, index=True) # <-- A ETIQUETA DA EMPRESA
    hora_abertura = Column(Integer, default=9)   
    hora_fechamento = Column(Integer, default=18) 
    cor_tema = Column(String, default="#f59e0b")
    telefone = Column(String, default="")

# ==========================================
# 4. TABELA DA EQUIPE
# ==========================================
class Profissional(Base):
    __tablename__ = "profissionais"
    id = Column(Integer, primary_key=True, index=True)
    barbearia_slug = Column(String, index=True) # <-- A ETIQUETA DA EMPRESA
    nome = Column(String)