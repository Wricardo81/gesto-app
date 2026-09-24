from datetime import date, timedelta

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import booking_whatsapp_service


@pytest.fixture()
def ambiente_confirmacao_booking(
    monkeypatch,
):
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    tabelas = [
        models.Barbearia.__table__,
        models.ConfiguracaoAgenda.__table__,
        models.ServicoBarbearia.__table__,
        models.Profissional.__table__,
        models.ServicoProfissional.__table__,
        models.Agendamento.__table__,
        models.BloqueioAgenda.__table__,
        models.SessaoBookingWhatsApp.__table__,
    ]

    for tabela in tabelas:
        tabela.create(
            bind=engine,
            checkfirst=True,
        )

    Session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    db = Session()

    data_alvo = (
        date.today()
        + timedelta(days=7)
    )

    monkeypatch.setattr(
        booking_whatsapp_service
        .agendamento_service,
        "validar_acesso_operacional_tenant",
        lambda *args, **kwargs: None,
    )

    try:
        empresa = models.Barbearia(
            nome="Tenant A",
            slug="tenant-a",
            plano_ativo=True,
            status_assinatura="active",
            status_pagamento="em_dia",
        )

        config = models.ConfiguracaoAgenda(
            barbearia_slug="tenant-a",
            hora_abertura=9,
            hora_fechamento=12,
        )

        servico = models.ServicoBarbearia(
            barbearia_slug="tenant-a",
            nome="Corte",
            preco=50,
            duracao=30,
        )

        profissional = models.Profissional(
            barbearia_slug="tenant-a",
            nome="Ana",
        )

        db.add_all([
            empresa,
            config,
            servico,
            profissional,
        ])

        db.flush()

        db.add(
            models.ServicoProfissional(
                barbearia_slug="tenant-a",
                servico_id=servico.id,
                profissional_id=profissional.id,
            )
        )

        db.commit()

        yield {
            "db": db,
            "data": data_alvo,
        }

    finally:
        db.close()


def preparar_ate_nome(
    db,
    data_alvo,
):
    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="oi",
    )

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Corte",
    )

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ana",
    )

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem=data_alvo.isoformat(),
    )

    return (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="1",
        )
    )


def test_nome_avanca_para_confirmacao(
    ambiente_confirmacao_booking,
):
    db = ambiente_confirmacao_booking["db"]
    data_alvo = ambiente_confirmacao_booking["data"]

    resposta_horario = preparar_ate_nome(
        db,
        data_alvo,
    )

    assert (
        resposta_horario["etapa"]
        == "aguardando_nome"
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="Ricardo",
        )
    )

    assert resposta["etapa"] == "confirmacao"

    assert resposta["sessao"][
        "cliente_nome"
    ] == "Ricardo"

    assert "Corte" in resposta["mensagem"]
    assert "Ana" in resposta["mensagem"]
    assert "09:00" in resposta["mensagem"]


def test_confirmar_cria_agendamento_real(
    ambiente_confirmacao_booking,
):
    db = ambiente_confirmacao_booking["db"]
    data_alvo = ambiente_confirmacao_booking["data"]

    preparar_ate_nome(
        db,
        data_alvo,
    )

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ricardo",
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="CONFIRMAR",
        )
    )

    assert resposta["etapa"] == "concluido"

    assert resposta["sessao"][
        "status"
    ] == "concluida"

    assert resposta["agendamento"] is not None

    assert resposta["agendamento"][
        "codigo_publico"
    ]

    agendamento = (
        db.query(models.Agendamento)
        .filter(
            models.Agendamento.barbearia_slug
            == "tenant-a",

            models.Agendamento.telefone_cliente
            == "81999999999",
        )
        .first()
    )

    assert agendamento is not None
    assert agendamento.cliente_nome == "Ricardo"
    assert agendamento.servico == "Corte"
    assert agendamento.profissional == "Ana"
    assert agendamento.horario == "09:00"
    assert agendamento.valor == 50


def test_resposta_invalida_mantem_confirmacao(
    ambiente_confirmacao_booking,
):
    db = ambiente_confirmacao_booking["db"]
    data_alvo = ambiente_confirmacao_booking["data"]

    preparar_ate_nome(
        db,
        data_alvo,
    )

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ricardo",
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="talvez",
        )
    )

    assert resposta["etapa"] == "confirmacao"

    assert (
        db.query(models.Agendamento)
        .count()
        == 0
    )


def test_cancelar_na_confirmacao_nao_cria_agendamento(
    ambiente_confirmacao_booking,
):
    db = ambiente_confirmacao_booking["db"]
    data_alvo = ambiente_confirmacao_booking["data"]

    preparar_ate_nome(
        db,
        data_alvo,
    )

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ricardo",
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="CANCELAR",
        )
    )

    assert resposta["sessao"][
        "status"
    ] == "cancelada"

    assert (
        db.query(models.Agendamento)
        .count()
        == 0
    )


def test_horario_ocupado_antes_da_confirmacao_volta_para_horarios(
    ambiente_confirmacao_booking,
):
    db = ambiente_confirmacao_booking["db"]
    data_alvo = ambiente_confirmacao_booking["data"]

    preparar_ate_nome(
        db,
        data_alvo,
    )

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ricardo",
    )

    db.add(
        models.Agendamento(
            barbearia_slug="tenant-a",
            cliente_nome="Outro Cliente",
            servico="Corte",
            profissional="Ana",
            data=data_alvo,
            horario="09:00",
            valor=50,
            telefone_cliente="81988888888",
            status="confirmado",
        )
    )

    db.commit()

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="CONFIRMAR",
        )
    )

    assert (
        resposta["etapa"]
        == "aguardando_horario"
    )

    assert resposta["agendamento"] is None

    opcoes = " ".join(
        resposta["opcoes"]
    )

    assert "09:00" not in opcoes
    assert "09:30" in opcoes

    assert (
        db.query(models.Agendamento)
        .count()
        == 1
    )


def test_confirmacao_cria_nova_sessao_em_proxima_conversa(
    ambiente_confirmacao_booking,
):
    db = ambiente_confirmacao_booking["db"]
    data_alvo = ambiente_confirmacao_booking["data"]

    preparar_ate_nome(
        db,
        data_alvo,
    )

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ricardo",
    )

    concluida = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="confirmar",
        )
    )

    id_concluido = concluida[
        "sessao"
    ]["id"]

    nova = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="oi",
        )
    )

    assert nova["sessao"]["id"] != id_concluido

    assert (
        nova["etapa"]
        == "aguardando_servico"
    )
