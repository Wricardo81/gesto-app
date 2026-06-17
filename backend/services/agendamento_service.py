from datetime import date, datetime, timedelta

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from uuid import uuid4

import models
from repositories import agendamento_repository


class FichaAgendamento(BaseModel):
    cliente_nome: str
    servico: str
    data: str
    horario: str
    valor: float
    profissional: str
    telefone_cliente: str
    aceita_lembrete_whatsapp: bool = True
    aceita_promocoes_whatsapp: bool = False


def criar_novo_agendamento(
    db: Session,
    tenant_slug: str,
    dados: FichaAgendamento,
):
    empresa = (
        db.query(models.Barbearia)
        .filter(models.Barbearia.slug == tenant_slug)
        .first()
    )

    if not empresa:
        raise HTTPException(
            status_code=404,
            detail="Estabelecimento não encontrado.",
        )

    if not empresa.plano_ativo:
        raise HTTPException(
            status_code=403,
            detail="Agenda temporariamente indisponível. Assinatura pendente.",
        )

    try:
        data_formatada = datetime.strptime(
            dados.data,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Data inválida. Utilize o formato YYYY-MM-DD.",
        )

    if data_formatada < date.today():
        raise HTTPException(
            status_code=422,
            detail="Não é possível agendar para uma data passada.",
        )

    try:
        datetime.strptime(
            dados.horario,
            "%H:%M",
        )
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Horário inválido. Utilize o formato HH:MM.",
        )

    servico = (
        db.query(models.ServicoBarbearia)
        .filter(
            models.ServicoBarbearia.barbearia_slug == tenant_slug,
            models.ServicoBarbearia.nome == dados.servico,
        )
        .first()
    )

    if not servico:
        raise HTTPException(
            status_code=404,
            detail="Serviço não encontrado neste estabelecimento.",
        )

    profissional = (
        db.query(models.Profissional)
        .filter(
            models.Profissional.barbearia_slug == tenant_slug,
            models.Profissional.nome == dados.profissional,
        )
        .first()
    )

    if not profissional:
        raise HTTPException(
            status_code=404,
            detail="Profissional não encontrado neste estabelecimento.",
        )

    resultado = obter_horarios_disponiveis(
        db=db,
        tenant_slug=tenant_slug,
        data_agendamento=dados.data,
        duracao_minutos=servico.duracao,
        profissional_nome=profissional.nome,
    )

    if dados.horario not in resultado["horarios_disponiveis"]:
        raise HTTPException(
            status_code=409,
            detail="Horário indisponível para este serviço e profissional.",
        )

    novo_agendamento = models.Agendamento(
        codigo_publico=uuid4().hex,
        barbearia_slug=tenant_slug,
        cliente_nome=dados.cliente_nome,
        servico=servico.nome,
        data=data_formatada,
        horario=dados.horario,
        valor=servico.preco,
        profissional=profissional.nome,
        telefone_cliente=dados.telefone_cliente,
        aceita_lembrete_whatsapp=dados.aceita_lembrete_whatsapp,
        aceita_promocoes_whatsapp=dados.aceita_promocoes_whatsapp,
        status="confirmado",
    )

    agendamento_salvo = agendamento_repository.salvar_agendamento(
        db=db,
        agendamento=novo_agendamento,
    )

    if isinstance(agendamento_salvo, dict):
        agendamento_salvo["codigo_publico"] = novo_agendamento.codigo_publico
        return agendamento_salvo

    return {
        "barbearia_slug": novo_agendamento.barbearia_slug,
        "cliente_nome": novo_agendamento.cliente_nome,
        "telefone_cliente": novo_agendamento.telefone_cliente,
        "servico": novo_agendamento.servico,
        "profissional": novo_agendamento.profissional,
        "data": (
            novo_agendamento.data.isoformat()
            if hasattr(novo_agendamento.data, "isoformat")
            else str(novo_agendamento.data)
        ),
        "horario": novo_agendamento.horario,
        "valor": novo_agendamento.valor,
        "status": novo_agendamento.status,
        "codigo_publico": novo_agendamento.codigo_publico,
        "id": novo_agendamento.id,
    }



# ==========================================
# MOTOR DE HORÁRIOS DISPONÍVEIS
# ==========================================

def horario_ainda_pode_ser_agendado(
    data_agendamento: date,
    horario: str,
) -> bool:
    if data_agendamento != date.today():
        return True

    horario_obj = datetime.strptime(
        horario,
        "%H:%M",
    ).time()

    agora = datetime.now().time()

    return horario_obj > agora


def obter_horarios_disponiveis(
    db: Session,
    tenant_slug: str,
    data_agendamento: str,
    duracao_minutos: int,
    profissional_nome: str,
):
    if duracao_minutos <= 0:
        raise HTTPException(
            status_code=422,
            detail="A duração do serviço deve ser maior que zero.",
        )

    try:
        data_alvo = datetime.strptime(
            data_agendamento,
            "%Y-%m-%d",
        ).date()
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Data inválida. Utilize o formato YYYY-MM-DD.",
        )

    if data_alvo < date.today():
        return {
            "horarios_disponiveis": []
        }

    config = (
        db.query(models.ConfiguracaoAgenda)
        .filter(
            models.ConfiguracaoAgenda.barbearia_slug == tenant_slug
        )
        .first()
    )

    abertura = config.hora_abertura if config else 9
    fechamento = config.hora_fechamento if config else 18

    agendamentos = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug == tenant_slug,
            models.Agendamento.profissional == profissional_nome,
            models.Agendamento.data == data_alvo,
            models.Agendamento.status != "cancelado",
        )
        .all()
    )

    intervalos_ocupados = []

    for agendamento in agendamentos:
        servico = (
            db.query(models.ServicoBarbearia)
            .filter(
                models.ServicoBarbearia.barbearia_slug == tenant_slug,
                models.ServicoBarbearia.nome == agendamento.servico,
            )
            .first()
        )

        duracao_ocupada = servico.duracao if servico else 30

        inicio_existente = datetime.strptime(
            agendamento.horario,
            "%H:%M",
        )

        fim_existente = inicio_existente + timedelta(
            minutes=duracao_ocupada
        )

        intervalos_ocupados.append(
            (
                inicio_existente,
                fim_existente,
            )
        )

    hora_atual = datetime.strptime(
        f"{abertura:02d}:00",
        "%H:%M",
    )

    hora_fim = datetime.strptime(
        f"{fechamento:02d}:00",
        "%H:%M",
    )

    passo_grade = timedelta(
        minutes=duracao_minutos
    )

    horarios_livres = []

    while hora_atual + passo_grade <= hora_fim:
        inicio_proposto = hora_atual
        fim_proposto = hora_atual + passo_grade

        existe_colisao = any(
            max(inicio_proposto, inicio_existente)
            < min(fim_proposto, fim_existente)
            for inicio_existente, fim_existente
            in intervalos_ocupados
        )

        if not existe_colisao:
            horario_formatado = hora_atual.strftime(
                "%H:%M"
            )

            if horario_ainda_pode_ser_agendado(
                data_alvo,
                horario_formatado,
            ):
                horarios_livres.append(
                    horario_formatado
                )

        hora_atual += passo_grade

    return {
        "horarios_disponiveis": horarios_livres
    }