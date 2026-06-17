from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import models
from database import SessaoLocal
from security import validar_tenant_logado
from services import agendamento_service
from pydantic import BaseModel

router = APIRouter()

STATUS_AGENDAMENTO_PERMITIDOS = {
    "confirmado",
    "concluido",
    "cancelado",
    "faltou",
}


class AtualizarStatusAgendamento(BaseModel):
    status: str

class CancelarAgendamentoAdmin(BaseModel):
    motivo_cancelamento: str

class AtualizarObservacaoInternaAgendamento(BaseModel):
    observacao_interna: str = ""

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
        "status": agendamento.status or "confirmado",
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
        "motivo_cancelamento": agendamento.motivo_cancelamento,
        "cancelado_por": agendamento.cancelado_por,
        "cancelado_em": (
            agendamento.cancelado_em.isoformat()
            if agendamento.cancelado_em
            else None
        ),
        "observacao_interna": agendamento.observacao_interna,
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

    agendamentos_faturaveis = [
    agendamento
    for agendamento in agendamentos
    if (agendamento.status or "confirmado") in [
        "confirmado",
        "concluido",
    ]
]

    faturamento_previsto = sum(
    float(agendamento.valor or 0)
    for agendamento in agendamentos_faturaveis
)

    return {
        "total_agendamentos": len(agendamentos),
        "faturamento_previsto": faturamento_previsto,
        "agendamentos": [
            serializar_agendamento_admin(agendamento)
            for agendamento in agendamentos
        ],
    }


@router.put("/api/{tenant_slug}/admin/agendamentos/{agendamento_id}/status")
def atualizar_status_agendamento_admin(
    tenant_slug: str,
    agendamento_id: int,
    dados: AtualizarStatusAgendamento,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    novo_status = dados.status.strip().lower()

    if novo_status not in STATUS_AGENDAMENTO_PERMITIDOS:
        raise HTTPException(
            status_code=422,
            detail="Status de agendamento inválido.",
        )

    agendamento = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.id == agendamento_id,
            models.Agendamento.barbearia_slug == tenant_slug,
        )
        .first()
    )

    if not agendamento:
        raise HTTPException(
            status_code=404,
            detail="Agendamento não encontrado.",
        )

    agendamento.status = novo_status

    if novo_status != "cancelado":
        agendamento.motivo_cancelamento = None
        agendamento.cancelado_por = None
        agendamento.cancelado_em = None

    db.commit()
    db.refresh(agendamento)

    return {
        "mensagem": "Status atualizado com sucesso.",
        "agendamento": serializar_agendamento_admin(agendamento),
    }


@router.put("/api/{tenant_slug}/admin/agendamentos/{agendamento_id}/cancelar")
def cancelar_agendamento_admin(
    tenant_slug: str,
    agendamento_id: int,
    dados: CancelarAgendamentoAdmin,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    motivo = dados.motivo_cancelamento.strip()

    if not motivo:
        raise HTTPException(
            status_code=422,
            detail="Informe o motivo do cancelamento.",
        )

    agendamento = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.id == agendamento_id,
            models.Agendamento.barbearia_slug == tenant_slug,
        )
        .first()
    )

    if not agendamento:
        raise HTTPException(
            status_code=404,
            detail="Agendamento não encontrado.",
        )

    agendamento.status = "cancelado"
    agendamento.motivo_cancelamento = motivo
    agendamento.cancelado_por = "admin"
    agendamento.cancelado_em = datetime.utcnow()

    db.commit()
    db.refresh(agendamento)

    return {
        "mensagem": "Agendamento cancelado com sucesso.",
        "agendamento": serializar_agendamento_admin(agendamento),
    }


@router.put("/api/{tenant_slug}/admin/agendamentos/{agendamento_id}/observacao")
def atualizar_observacao_interna_agendamento(
    tenant_slug: str,
    agendamento_id: int,
    dados: AtualizarObservacaoInternaAgendamento,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    agendamento = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.id == agendamento_id,
            models.Agendamento.barbearia_slug == tenant_slug,
        )
        .first()
    )

    if not agendamento:
        raise HTTPException(
            status_code=404,
            detail="Agendamento não encontrado.",
        )

    agendamento.observacao_interna = dados.observacao_interna.strip()

    db.commit()
    db.refresh(agendamento)

    return {
        "mensagem": "Observação interna atualizada com sucesso.",
        "agendamento": serializar_agendamento_admin(agendamento),
    }


def normalizar_telefone_cliente(telefone: str) -> str:
    return "".join(
        caractere
        for caractere in str(telefone or "")
        if caractere.isdigit()
    )


@router.get("/api/{tenant_slug}/admin/clientes/historico")
def obter_historico_cliente_admin(
    tenant_slug: str,
    telefone: str = Query(...),
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    telefone_normalizado = normalizar_telefone_cliente(telefone)

    if not telefone_normalizado:
        raise HTTPException(
            status_code=422,
            detail="Telefone inválido.",
        )

    agendamentos = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug == tenant_slug,
        )
        .order_by(
            models.Agendamento.data.desc(),
            models.Agendamento.horario.desc(),
        )
        .all()
    )

    historico = [
        agendamento
        for agendamento in agendamentos
        if normalizar_telefone_cliente(
            agendamento.telefone_cliente
        ) == telefone_normalizado
    ]

    faturamento_total = sum(
        float(agendamento.valor or 0)
        for agendamento in historico
        if (agendamento.status or "confirmado") == "concluido"
    )

    cancelamentos = [
        agendamento
        for agendamento in historico
        if (agendamento.status or "") == "cancelado"
    ]

    return {
        "telefone": telefone_normalizado,
        "total_agendamentos": len(historico),
        "total_cancelamentos": len(cancelamentos),
        "faturamento_total_concluido": faturamento_total,
        "agendamentos": [
            serializar_agendamento_admin(agendamento)
            for agendamento in historico
        ],
    }