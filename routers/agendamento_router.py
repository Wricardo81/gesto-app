from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessaoLocal
from services import agendamento_service

router = APIRouter()

# Injeção de dependência do banco de dados
def get_db():
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 1. ROTA PÚBLICA: CONSULTAR HORÁRIOS
# ==========================================
@router.get("/api/{tenant_slug}/horarios/{data}/{duracao_minutos}/{profissional}")
def consultar_horarios_livres(
    tenant_slug: str, 
    data: str, 
    duracao_minutos: int, 
    profissional: str, 
    db: Session = Depends(get_db)
):
    """
    O cliente seleciona o dia, o serviço e o barbeiro no frontend, 
    e essa rota devolve exatamente as fatias de tempo disponíveis.
    """
    return agendamento_service.obter_horarios_disponiveis(
        db=db, 
        tenant_slug=tenant_slug, 
        data_str=data, 
        duracao_minutos=duracao_minutos, 
        profissional=profissional
    )

# ==========================================
# 2. ROTA PÚBLICA: TRAVAR AGENDAMENTO
# ==========================================
@router.post("/api/{tenant_slug}/agendar")
def confirmar_agendamento(
    tenant_slug: str, 
    dados: agendamento_service.FichaAgendamento, 
    db: Session = Depends(get_db)
):
    """
    O cliente preenche nome e telefone e clica em "Agendar".
    O serviço assume a bronca de verificar colisões e salvar.
    """
    return agendamento_service.criar_novo_agendamento(
        db=db, 
        tenant_slug=tenant_slug, 
        dados=dados
    )