from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from security import validar_tenant_logado
from services import agendamento_service


router = APIRouter()


# ==========================================
# DEPENDÊNCIA DO BANCO DE DADOS
# ==========================================

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
    db: Session = Depends(get_db),
):
    return agendamento_service.obter_horarios_disponiveis(
        db=db,
        tenant_slug=tenant_slug,
        data_agendamento=data,
        duracao_minutos=duracao_minutos,
        profissional_nome=profissional,
    )


# ==========================================
# 2. ROTA PÚBLICA: CRIAR AGENDAMENTO
# ==========================================

@router.post("/api/{tenant_slug}/agendar")
def confirmar_agendamento(
    tenant_slug: str,
    dados: agendamento_service.FichaAgendamento,
    db: Session = Depends(get_db),
):
    return agendamento_service.criar_novo_agendamento(
        db=db,
        tenant_slug=tenant_slug,
        dados=dados,
    )


# ==========================================
# 3. FUNÇÃO AUXILIAR: SERIALIZAR AGENDAMENTO
# ==========================================

def serializar_agendamento_admin(
    agendamento: models.Agendamento,
) -> dict:
    return {
        "id": agendamento.id,
        "cliente_nome": agendamento.cliente_nome,
        "telefone_cliente": agendamento.telefone_cliente,
        "servico": agendamento.servico,
        "profissional": agendamento.profissional,
        "data": (
            agendamento.data.isoformat()
            if hasattr(agendamento.data, "isoformat")
            else str(agendamento.data)
        ),
        "horario": agendamento.horario,
        "valor": float(agendamento.valor or 0),
        "aceita_lembrete_whatsapp": bool(
            agendamento.aceita_lembrete_whatsapp
        ),
        "aceita_promocoes_whatsapp": bool(
            agendamento.aceita_promocoes_whatsapp
        ),
    }


# ==========================================
# 4. ROTA ADMIN: LISTAR AGENDA E FATURAMENTO
# ==========================================

@router.get("/api/{tenant_slug}/admin/agendamentos")
def listar_agendamentos_admin(
    tenant_slug: str,
    data_inicio: Optional[date] = Query(default=None),
    data_fim: Optional[date] = Query(default=None),
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    consulta = db.query(models.Agendamento).filter(
        models.Agendamento.barbearia_slug == tenant_slug
    )

    if data_inicio:
        consulta = consulta.filter(
            models.Agendamento.data >= data_inicio
        )

    if data_fim:
        consulta = consulta.filter(
            models.Agendamento.data <= data_fim
        )

    agendamentos = (
        consulta
        .order_by(
            models.Agendamento.data.desc(),
            models.Agendamento.horario.desc(),
        )
        .all()
    )

    faturamento_previsto = sum(
        float(agendamento.valor or 0)
        for agendamento in agendamentos
    )

    return {
        "total_agendamentos": len(agendamentos),
        "faturamento_previsto": faturamento_previsto,
        "agendamentos": [
            serializar_agendamento_admin(agendamento)
            for agendamento in agendamentos
        ],
    }