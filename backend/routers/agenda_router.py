from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import models
from database import SessaoLocal
from security import validar_tenant_logado


router = APIRouter(
    prefix="/api",
    tags=["Agenda Diária"],
)


def get_db():
    db = SessaoLocal()

    try:
        yield db
    finally:
        db.close()


def converter_data(data_texto: str) -> date:
    try:
        return datetime.strptime(
            data_texto,
            "%Y-%m-%d",
        ).date()

    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Data inválida. Use o formato YYYY-MM-DD.",
        )


def converter_horario_para_datetime(
    data_referencia: date,
    horario: str,
) -> datetime:
    try:
        horario_obj = datetime.strptime(
            horario,
            "%H:%M",
        ).time()

        return datetime.combine(
            data_referencia,
            horario_obj,
        )

    except ValueError:
        raise HTTPException(
            status_code=500,
            detail="Horário inválido encontrado na agenda.",
        )


def formatar_data_hora(valor: datetime | None) -> str | None:
    if not valor:
        return None

    return valor.isoformat()


def formatar_data(valor: date | None) -> str | None:
    if not valor:
        return None

    return valor.isoformat()


def obter_configuracao_agenda(
    db: Session,
    tenant_slug: str,
) -> models.ConfiguracaoAgenda | None:
    return (
        db.query(models.ConfiguracaoAgenda)
        .filter(
            models.ConfiguracaoAgenda.barbearia_slug == tenant_slug
        )
        .first()
    )


def obter_duracao_servico(
    db: Session,
    tenant_slug: str,
    nome_servico: str,
) -> int:
    servico = (
        db.query(models.ServicoBarbearia)
        .filter(
            models.ServicoBarbearia.barbearia_slug == tenant_slug,
            models.ServicoBarbearia.nome == nome_servico,
        )
        .first()
    )

    if not servico:
        return 30

    return int(servico.duracao or 30)


def serializar_agendamento_agenda(
    db: Session,
    agendamento: models.Agendamento,
) -> dict:
    duracao = obter_duracao_servico(
        db,
        agendamento.barbearia_slug,
        agendamento.servico,
    )

    inicio = converter_horario_para_datetime(
        agendamento.data,
        agendamento.horario,
    )

    fim = inicio + timedelta(
        minutes=duracao,
    )

    return {
        "tipo": "agendamento",
        "id": agendamento.id,
        "codigo_publico": agendamento.codigo_publico,
        "cliente_nome": agendamento.cliente_nome,
        "telefone_cliente": agendamento.telefone_cliente,
        "servico": agendamento.servico,
        "profissional": agendamento.profissional,
        "data": formatar_data(agendamento.data),
        "horario": agendamento.horario,
        "inicio": formatar_data_hora(inicio),
        "fim": formatar_data_hora(fim),
        "duracao_minutos": duracao,
        "valor": float(agendamento.valor or 0),
        "status": agendamento.status or "confirmado",
        "motivo_cancelamento": agendamento.motivo_cancelamento,
        "cancelado_por": agendamento.cancelado_por,
        "cancelado_em": (
            agendamento.cancelado_em.isoformat()
            if agendamento.cancelado_em
            else None
        ),
        "observacao_interna": agendamento.observacao_interna,
    }


def serializar_bloqueio_agenda(
    bloqueio: models.BloqueioAgenda,
    abertura: int,
    fechamento: int,
) -> dict:
    if bloqueio.dia_inteiro:
        horario_inicio = f"{abertura:02d}:00"
        horario_fim = f"{fechamento:02d}:00"
    else:
        horario_inicio = bloqueio.horario_inicio
        horario_fim = bloqueio.horario_fim

    inicio = (
        converter_horario_para_datetime(
            bloqueio.data,
            horario_inicio,
        )
        if horario_inicio
        else None
    )

    fim = (
        converter_horario_para_datetime(
            bloqueio.data,
            horario_fim,
        )
        if horario_fim
        else None
    )

    return {
        "tipo": "bloqueio",
        "id": bloqueio.id,
        "profissional": bloqueio.profissional,
        "profissional_label": bloqueio.profissional or "Todos",
        "data": formatar_data(bloqueio.data),
        "horario_inicio": horario_inicio,
        "horario_fim": horario_fim,
        "inicio": formatar_data_hora(inicio),
        "fim": formatar_data_hora(fim),
        "dia_inteiro": bloqueio.dia_inteiro,
        "motivo": bloqueio.motivo,
        "criado_em": (
            bloqueio.criado_em.isoformat()
            if bloqueio.criado_em
            else None
        ),
    }


def montar_linha_do_tempo(
    data_alvo: date,
    abertura: int,
    fechamento: int,
    intervalo_minutos: int = 30,
) -> list[dict]:
    horario_atual = datetime.combine(
        data_alvo,
        datetime.strptime(
            f"{abertura:02d}:00",
            "%H:%M",
        ).time(),
    )

    horario_final = datetime.combine(
        data_alvo,
        datetime.strptime(
            f"{fechamento:02d}:00",
            "%H:%M",
        ).time(),
    )

    linha_do_tempo = []

    while horario_atual < horario_final:
        linha_do_tempo.append(
            {
                "horario": horario_atual.strftime("%H:%M"),
                "inicio": horario_atual.isoformat(),
            }
        )

        horario_atual += timedelta(
            minutes=intervalo_minutos,
        )

    return linha_do_tempo


def calcular_resumo_agenda(
    agendamentos: list[models.Agendamento],
) -> dict:
    total = len(agendamentos)

    confirmados = 0
    concluidos = 0
    cancelados = 0
    faltas = 0

    faturamento_previsto = 0.0
    faturamento_concluido = 0.0

    for agendamento in agendamentos:
        status = agendamento.status or "confirmado"
        valor = float(agendamento.valor or 0)

        if status == "confirmado":
            confirmados += 1
            faturamento_previsto += valor

        elif status == "concluido":
            concluidos += 1
            faturamento_concluido += valor

        elif status == "cancelado":
            cancelados += 1

        elif status == "faltou":
            faltas += 1

    return {
        "total_agendamentos": total,
        "confirmados": confirmados,
        "concluidos": concluidos,
        "cancelados": cancelados,
        "faltas": faltas,
        "faturamento_previsto": faturamento_previsto,
        "faturamento_concluido": faturamento_concluido,
    }


@router.get("/{tenant_slug}/admin/agenda-dia")
def obter_agenda_diaria_admin(
    tenant_slug: str,
    data: str = Query(...),
    profissional: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _tenant_autorizado: str = Depends(validar_tenant_logado),
):
    data_alvo = converter_data(data)

    configuracao = obter_configuracao_agenda(
        db,
        tenant_slug,
    )

    abertura = (
        int(configuracao.hora_abertura)
        if configuracao
        else 9
    )

    fechamento = (
        int(configuracao.hora_fechamento)
        if configuracao
        else 18
    )

    consulta_agendamentos = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug == tenant_slug,
            models.Agendamento.data == data_alvo,
        )
    )

    if profissional:
        consulta_agendamentos = consulta_agendamentos.filter(
            models.Agendamento.profissional == profissional
        )

    agendamentos = (
        consulta_agendamentos
        .order_by(
            models.Agendamento.horario.asc()
        )
        .all()
    )

    consulta_bloqueios = (
        db.query(models.BloqueioAgenda)
        .filter(
            models.BloqueioAgenda.barbearia_slug == tenant_slug,
            models.BloqueioAgenda.data == data_alvo,
        )
    )

    if profissional:
        consulta_bloqueios = consulta_bloqueios.filter(
            (
                models.BloqueioAgenda.profissional == profissional
            )
            | (
                models.BloqueioAgenda.profissional.is_(None)
            )
        )

    bloqueios = (
        consulta_bloqueios
        .order_by(
            models.BloqueioAgenda.horario_inicio.asc()
        )
        .all()
    )

    profissionais = (
        db.query(models.Profissional)
        .filter(
            models.Profissional.barbearia_slug == tenant_slug
        )
        .order_by(
            models.Profissional.nome.asc()
        )
        .all()
    )

    eventos_agendamentos = [
        serializar_agendamento_agenda(
            db,
            agendamento,
        )
        for agendamento in agendamentos
    ]

    eventos_bloqueios = [
        serializar_bloqueio_agenda(
            bloqueio,
            abertura,
            fechamento,
        )
        for bloqueio in bloqueios
    ]

    eventos = eventos_agendamentos + eventos_bloqueios

    eventos.sort(
        key=lambda item: (
            item.get("inicio") or "",
            item.get("tipo") or "",
        )
    )

    return {
        "tenant_slug": tenant_slug,
        "data": data_alvo.isoformat(),
        "profissional": profissional,
        "abertura": abertura,
        "fechamento": fechamento,
        "profissionais": [
            {
                "id": profissional_item.id,
                "nome": profissional_item.nome,
            }
            for profissional_item in profissionais
        ],
        "resumo": calcular_resumo_agenda(
            agendamentos
        ),
        "linha_do_tempo": montar_linha_do_tempo(
            data_alvo,
            abertura,
            fechamento,
        ),
        "eventos": eventos,
        "agendamentos": eventos_agendamentos,
        "bloqueios": eventos_bloqueios,
    }