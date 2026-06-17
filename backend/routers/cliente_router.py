from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from security import validar_tenant_logado


router = APIRouter(
    prefix="/api",
    tags=["Clientes / CRM"],
)


def get_db():
    db = SessaoLocal()
    try:
        yield db
    finally:
        db.close()


def normalizar_telefone(telefone: str) -> str:
    return "".join(
        caractere
        for caractere in str(telefone or "")
        if caractere.isdigit()
    )


def serializar_data(data_valor):
    if not data_valor:
        return None

    if hasattr(data_valor, "isoformat"):
        return data_valor.isoformat()

    return str(data_valor)


def calcular_ticket_medio(
    faturamento_total: float,
    total_concluidos: int,
) -> float:
    if total_concluidos <= 0:
        return 0

    return faturamento_total / total_concluidos


@router.get("/{tenant_slug}/admin/clientes")
def listar_clientes_admin(
    tenant_slug: str,
    busca: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    agendamentos = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug == tenant_slug
        )
        .order_by(
            models.Agendamento.data.desc(),
            models.Agendamento.horario.desc(),
        )
        .all()
    )

    clientes_por_telefone = {}

    hoje = date.today()

    for agendamento in agendamentos:
        telefone = normalizar_telefone(
            agendamento.telefone_cliente
        )

        if not telefone:
            continue

        if busca:
            busca_normalizada = normalizar_telefone(busca)
            busca_texto = busca.lower().strip()

            nome_cliente = str(
                agendamento.cliente_nome or ""
            ).lower()

            telefone_bate = (
                busca_normalizada
                and busca_normalizada in telefone
            )

            nome_bate = (
                busca_texto
                and busca_texto in nome_cliente
            )

            if not telefone_bate and not nome_bate:
                continue

        if telefone not in clientes_por_telefone:
            clientes_por_telefone[telefone] = {
                "telefone": telefone,
                "nome": agendamento.cliente_nome or "Cliente",
                "total_agendamentos": 0,
                "total_confirmados": 0,
                "total_concluidos": 0,
                "total_cancelados": 0,
                "total_faltas": 0,
                "faturamento_total_concluido": 0.0,
                "ticket_medio": 0.0,
                "ultima_visita": None,
                "proximo_agendamento": None,
                "ultimo_servico": None,
                "ultimo_profissional": None,
            }

        cliente = clientes_por_telefone[telefone]

        cliente["total_agendamentos"] += 1

        status = agendamento.status or "confirmado"

        if status == "confirmado":
            cliente["total_confirmados"] += 1

        if status == "concluido":
            cliente["total_concluidos"] += 1
            cliente["faturamento_total_concluido"] += float(
                agendamento.valor or 0
            )

        if status == "cancelado":
            cliente["total_cancelados"] += 1

        if status == "faltou":
            cliente["total_faltas"] += 1

        if (
            status == "concluido"
            and agendamento.data
            and agendamento.data <= hoje
        ):
            if (
                cliente["ultima_visita"] is None
                or agendamento.data > cliente["ultima_visita"]
            ):
                cliente["ultima_visita"] = agendamento.data
                cliente["ultimo_servico"] = agendamento.servico
                cliente["ultimo_profissional"] = agendamento.profissional
                cliente["nome"] = agendamento.cliente_nome or cliente["nome"]

        if (
            status == "confirmado"
            and agendamento.data
            and agendamento.data >= hoje
        ):
            if (
                cliente["proximo_agendamento"] is None
                or agendamento.data < cliente["proximo_agendamento"]
            ):
                cliente["proximo_agendamento"] = agendamento.data

    clientes = []

    for cliente in clientes_por_telefone.values():
        cliente["ticket_medio"] = calcular_ticket_medio(
            cliente["faturamento_total_concluido"],
            cliente["total_concluidos"],
        )

        cliente["ultima_visita"] = serializar_data(
            cliente["ultima_visita"]
        )

        cliente["proximo_agendamento"] = serializar_data(
            cliente["proximo_agendamento"]
        )

        clientes.append(cliente)

    clientes.sort(
        key=lambda item: (
            item["faturamento_total_concluido"],
            item["total_agendamentos"],
        ),
        reverse=True,
    )

    total_clientes = len(clientes)

    clientes_recorrentes = len([
        cliente
        for cliente in clientes
        if cliente["total_agendamentos"] >= 2
    ])

    faturamento_total = sum(
        cliente["faturamento_total_concluido"]
        for cliente in clientes
    )

    total_concluidos = sum(
        cliente["total_concluidos"]
        for cliente in clientes
    )

    ticket_medio_geral = calcular_ticket_medio(
        faturamento_total,
        total_concluidos,
    )

    return {
        "total_clientes": total_clientes,
        "clientes_recorrentes": clientes_recorrentes,
        "faturamento_total_concluido": faturamento_total,
        "ticket_medio_geral": ticket_medio_geral,
        "clientes": clientes,
    }


@router.get("/{tenant_slug}/admin/clientes/{telefone}")
def obter_cliente_admin(
    tenant_slug: str,
    telefone: str,
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    telefone_normalizado = normalizar_telefone(telefone)

    agendamentos = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug == tenant_slug
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
        if normalizar_telefone(
            agendamento.telefone_cliente
        ) == telefone_normalizado
    ]

    return {
        "telefone": telefone_normalizado,
        "total": len(historico),
        "agendamentos": [
            {
                "id": agendamento.id,
                "cliente_nome": agendamento.cliente_nome,
                "servico": agendamento.servico,
                "profissional": agendamento.profissional,
                "data": serializar_data(agendamento.data),
                "horario": agendamento.horario,
                "valor": float(agendamento.valor or 0),
                "status": agendamento.status or "confirmado",
                "motivo_cancelamento": agendamento.motivo_cancelamento,
                "observacao_interna": agendamento.observacao_interna,
            }
            for agendamento in historico
        ],
    }