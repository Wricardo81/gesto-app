from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from security import validar_tenant_logado, obter_contexto_usuario_logado
from pydantic import BaseModel


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



class RegistrarInteracaoClienteCRM(BaseModel):
    tipo: str
    cliente_nome: str | None = None


TIPOS_INTERACAO_REATIVACAO_CRM = {
    "reativacao_risco",
    "reativacao_inativo",
}


def usuario_pode_registrar_interacao_crm(
    contexto: dict,
) -> bool:
    papel = str(
        contexto.get("papel")
        or ""
    ).strip().lower()

    permissoes = {
        str(permissao).strip()
        for permissao
        in (
            contexto.get("permissoes")
            or []
        )
        if str(permissao).strip()
    }

    return (
        papel == "gestor"
        or "*" in permissoes
        or "editar_cliente" in permissoes
    )


def usuario_pode_ler_interacoes_crm(
    contexto: dict,
) -> bool:
    papel = str(
        contexto.get("papel")
        or ""
    ).strip().lower()

    permissoes = {
        str(permissao).strip()
        for permissao
        in (
            contexto.get("permissoes")
            or []
        )
        if str(permissao).strip()
    }

    return (
        papel == "gestor"
        or "*" in permissoes
        or "ver_clientes" in permissoes
        or "gerenciar_clientes" in permissoes
        or "editar_cliente" in permissoes
    )


def serializar_interacao_cliente_crm(
    interacao,
) -> dict:
    return {
        "id": interacao.id,
        "telefone_cliente":
            interacao.telefone_cliente,
        "cliente_nome":
            interacao.cliente_nome,
        "tipo": interacao.tipo,
        "canal": interacao.canal,
        "origem": interacao.origem,
        "usuario_nome":
            interacao.usuario_nome,
        "usuario_email":
            interacao.usuario_email,
        "usuario_papel":
            interacao.usuario_papel,
        "criado_em":
            serializar_data(
                interacao.criado_em
            ),
    }


def cliente_existe_no_tenant(
    db: Session,
    tenant_slug: str,
    telefone_normalizado: str,
) -> bool:
    agendamentos = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug
            == tenant_slug
        )
        .all()
    )

    return any(
        normalizar_telefone(
            agendamento.telefone_cliente
        )
        == telefone_normalizado
        for agendamento in agendamentos
    )



@router.post(
    "/{tenant_slug}/admin/clientes/{telefone}/interacoes",
    status_code=201,
)
def registrar_interacao_cliente_crm(
    tenant_slug: str,
    telefone: str,
    dados: RegistrarInteracaoClienteCRM,
    db: Session = Depends(get_db),
    contexto: dict = Depends(
        obter_contexto_usuario_logado
    ),
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
):
    if not usuario_pode_registrar_interacao_crm(
        contexto
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Voce nao possui permissao para "
                "registrar interacoes de clientes."
            ),
        )

    telefone_normalizado = normalizar_telefone(
        telefone
    )

    if not telefone_normalizado:
        raise HTTPException(
            status_code=422,
            detail="Telefone invalido.",
        )

    tipo = str(
        dados.tipo or ""
    ).strip().lower()

    if tipo not in TIPOS_INTERACAO_REATIVACAO_CRM:
        raise HTTPException(
            status_code=422,
            detail=(
                "Tipo de interacao CRM invalido."
            ),
        )

    if not cliente_existe_no_tenant(
        db,
        tenant_slug,
        telefone_normalizado,
    ):
        raise HTTPException(
            status_code=404,
            detail="Cliente nao encontrado.",
        )

    cliente_nome = str(
        dados.cliente_nome or ""
    ).strip() or None

    interacao = models.InteracaoClienteCRM(
        barbearia_slug=tenant_slug,
        telefone_cliente=
            telefone_normalizado,
        cliente_nome=cliente_nome,
        tipo=tipo,
        canal="whatsapp",
        origem="crm_admin",
        usuario_nome=(
            contexto.get("nome")
            or None
        ),
        usuario_email=(
            contexto.get("email")
            or None
        ),
        usuario_papel=(
            contexto.get("papel")
            or None
        ),
    )

    db.add(interacao)
    db.commit()
    db.refresh(interacao)

    return {
        "mensagem":
            "Interacao CRM registrada.",
        "interacao":
            serializar_interacao_cliente_crm(
                interacao
            ),
    }


@router.get(
    "/{tenant_slug}/admin/clientes/{telefone}/interacoes"
)
def listar_interacoes_cliente_crm(
    tenant_slug: str,
    telefone: str,
    limite: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    contexto: dict = Depends(
        obter_contexto_usuario_logado
    ),
    _tenant_autorizado: str = Depends(
        validar_tenant_logado
    ),
):
    if not usuario_pode_ler_interacoes_crm(
        contexto
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                "Voce nao possui permissao "
                "para visualizar interacoes "
                "de clientes."
            ),
        )

    telefone_normalizado = normalizar_telefone(
        telefone
    )

    if not telefone_normalizado:
        raise HTTPException(
            status_code=422,
            detail="Telefone invalido.",
        )

    interacoes = (
        db.query(
            models.InteracaoClienteCRM
        )
        .filter(
            models.InteracaoClienteCRM.barbearia_slug
            == tenant_slug,
            models.InteracaoClienteCRM.telefone_cliente
            == telefone_normalizado,
        )
        .order_by(
            models.InteracaoClienteCRM.criado_em.desc(),
            models.InteracaoClienteCRM.id.desc(),
        )
        .limit(limite)
        .all()
    )

    return {
        "telefone": telefone_normalizado,
        "quantidade": len(interacoes),
        "interacoes": [
            serializar_interacao_cliente_crm(
                interacao
            )
            for interacao in interacoes
        ],
    }


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

    interacoes_crm = (
        db.query(models.InteracaoClienteCRM)
        .filter(
            models.InteracaoClienteCRM.barbearia_slug
            == tenant_slug
        )
        .order_by(
            models.InteracaoClienteCRM.criado_em.desc(),
            models.InteracaoClienteCRM.id.desc(),
        )
        .all()
    )

    ultima_interacao_por_telefone = {}

    for interacao in interacoes_crm:
        telefone_interacao = normalizar_telefone(
            interacao.telefone_cliente
        )

        if (
            telefone_interacao
            and telefone_interacao
            not in ultima_interacao_por_telefone
        ):
            ultima_interacao_por_telefone[
                telefone_interacao
            ] = interacao

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

        ultima_interacao = (
            ultima_interacao_por_telefone.get(
                cliente["telefone"]
            )
        )

        cliente["ultima_interacao_crm"] = (
            serializar_interacao_cliente_crm(
                ultima_interacao
            )
            if ultima_interacao
            else None
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
