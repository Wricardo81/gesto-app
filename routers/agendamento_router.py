from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import SessaoLocal
from services import agendamento_service

router = APIRouter()

def get_db():
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/api/{tenant_slug}/agendar")
def criar_agendamento(
    tenant_slug: str, 
    dados_recebidos: agendamento_service.FichaAgendamento, 
    db: Session = Depends(get_db)
):
    # O Router não entende nada de banco de dados, só aciona o Serviço
    agendamento_service.criar_novo_agendamento(db, tenant_slug, dados_recebidos)
    return {"status": "Sucesso", "mensagem": "Agendamento confirmado!"}


@router.get("/api/{tenant_slug}/horarios/{duracao_minutos}/{profissional}")
def listar_horarios_livres(tenant_slug: str, duracao_minutos: int, profissional: str, db: Session = Depends(get_db)):
    # O router só repassa a bola para o service!
    return agendamento_service.obter_horarios_disponiveis(db, tenant_slug, duracao_minutos, profissional)