from datetime import date, timedelta

import pytest

from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from main import app

from routers import agendamento_router

from services import agendamento_service


@pytest.fixture()
def ambiente_booking_publico(
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

    def override_get_db():
        db = Session()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[
        agendamento_router.get_db
    ] = override_get_db

    # O objetivo desta suite e congelar o contrato
    # de disponibilidade/agendamento, nao testar
    # novamente billing/acesso do tenant.
    monkeypatch.setattr(
        agendamento_router,
        "validar_empresa_pode_operar",
        lambda **kwargs: None,
    )

    monkeypatch.setattr(
        agendamento_service,
        "validar_acesso_operacional_tenant",
        lambda *args, **kwargs: None,
    )

    client = TestClient(app)

    data_alvo = (
        date.today()
        + timedelta(days=10)
    )

    db = Session()

    try:
        empresa = models.Barbearia(
            nome="Tenant Booking",
            slug="tenant-booking",
            plano_ativo=True,
            status_assinatura="active",
            status_pagamento="em_dia",
        )

        config = models.ConfiguracaoAgenda(
            barbearia_slug="tenant-booking",
            hora_abertura=9,
            hora_fechamento=12,
        )

        servico = models.ServicoBarbearia(
            barbearia_slug="tenant-booking",
            nome="Corte",
            preco=50,
            duracao=30,
        )

        profissional = models.Profissional(
            barbearia_slug="tenant-booking",
            nome="Ana",
        )

        db.add_all([
            empresa,
            config,
            servico,
            profissional,
        ])

        db.flush()

        vinculo = models.ServicoProfissional(
            barbearia_slug="tenant-booking",
            servico_id=servico.id,
            profissional_id=profissional.id,
        )

        db.add(vinculo)

        db.commit()

    finally:
        db.close()

    try:
        yield {
            "client": client,
            "Session": Session,
            "data": data_alvo,
        }

    finally:
        app.dependency_overrides.pop(
            agendamento_router.get_db,
            None,
        )


def url_horarios(data_alvo):
    return (
        "/api/tenant-booking/horarios/"
        f"{data_alvo.isoformat()}/30/Ana"
    )


def payload_agendamento(
    data_alvo,
    horario,
):
    return {
        "cliente_nome":
            "Cliente Booking",

        "servico":
            "Corte",

        "data":
            data_alvo.isoformat(),

        "horario":
            horario,

        "valor":
            999,

        "profissional":
            "Ana",

        "telefone_cliente":
            "81999999999",

        "aceita_lembrete_whatsapp":
            True,

        "aceita_promocoes_whatsapp":
            False,
    }


def test_horario_livre_aparece_na_disponibilidade(
    ambiente_booking_publico,
):
    client = ambiente_booking_publico[
        "client"
    ]

    data_alvo = ambiente_booking_publico[
        "data"
    ]

    resposta = client.get(
        url_horarios(data_alvo)
    )

    assert resposta.status_code == 200

    horarios = resposta.json()[
        "horarios_disponiveis"
    ]

    assert "09:00" in horarios
    assert "10:00" in horarios
    assert "11:30" in horarios


def test_horario_ocupado_desaparece_da_disponibilidade(
    ambiente_booking_publico,
):
    client = ambiente_booking_publico[
        "client"
    ]

    Session = ambiente_booking_publico[
        "Session"
    ]

    data_alvo = ambiente_booking_publico[
        "data"
    ]

    db = Session()

    try:
        db.add(
            models.Agendamento(
                barbearia_slug=
                    "tenant-booking",

                cliente_nome=
                    "Cliente Existente",

                servico=
                    "Corte",

                profissional=
                    "Ana",

                data=
                    data_alvo,

                horario=
                    "09:30",

                valor=
                    50,

                telefone_cliente=
                    "81988888888",

                status=
                    "confirmado",
            )
        )

        db.commit()

    finally:
        db.close()

    resposta = client.get(
        url_horarios(data_alvo)
    )

    assert resposta.status_code == 200

    horarios = resposta.json()[
        "horarios_disponiveis"
    ]

    assert "09:30" not in horarios

    assert "09:00" in horarios
    assert "10:00" in horarios


def test_bloqueio_remove_horario_da_disponibilidade(
    ambiente_booking_publico,
):
    client = ambiente_booking_publico[
        "client"
    ]

    Session = ambiente_booking_publico[
        "Session"
    ]

    data_alvo = ambiente_booking_publico[
        "data"
    ]

    db = Session()

    try:
        db.add(
            models.BloqueioAgenda(
                barbearia_slug=
                    "tenant-booking",

                profissional=
                    "Ana",

                data=
                    data_alvo,

                horario_inicio=
                    "10:30",

                horario_fim=
                    "11:00",

                dia_inteiro=
                    False,

                motivo=
                    "Intervalo",
            )
        )

        db.commit()

    finally:
        db.close()

    resposta = client.get(
        url_horarios(data_alvo)
    )

    assert resposta.status_code == 200

    horarios = resposta.json()[
        "horarios_disponiveis"
    ]

    assert "10:30" not in horarios

    assert "10:00" in horarios
    assert "11:00" in horarios


def test_agendamento_valido_persiste_com_codigo_publico(
    ambiente_booking_publico,
):
    client = ambiente_booking_publico[
        "client"
    ]

    Session = ambiente_booking_publico[
        "Session"
    ]

    data_alvo = ambiente_booking_publico[
        "data"
    ]

    resposta = client.post(
        "/api/tenant-booking/agendar",
        json=payload_agendamento(
            data_alvo,
            "11:00",
        ),
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["status"] == "confirmado"

    assert dados["servico"] == "Corte"
    assert dados["profissional"] == "Ana"
    assert dados["horario"] == "11:00"

    # O backend deve usar o preco real
    # cadastrado, ignorando o valor enviado
    # pelo cliente.
    assert dados["valor"] == 50

    assert dados["codigo_publico"]

    db = Session()

    try:
        agendamento = (
            db.query(
                models.Agendamento
            )
            .filter(
                models.Agendamento.barbearia_slug
                == "tenant-booking",

                models.Agendamento.profissional
                == "Ana",

                models.Agendamento.data
                == data_alvo,

                models.Agendamento.horario
                == "11:00",
            )
            .first()
        )

        assert agendamento is not None

        assert (
            agendamento.codigo_publico
            == dados["codigo_publico"]
        )

        assert agendamento.valor == 50

    finally:
        db.close()


def test_agendamento_recusa_horario_que_ficou_ocupado(
    ambiente_booking_publico,
):
    client = ambiente_booking_publico[
        "client"
    ]

    data_alvo = ambiente_booking_publico[
        "data"
    ]

    primeira = client.post(
        "/api/tenant-booking/agendar",
        json=payload_agendamento(
            data_alvo,
            "10:00",
        ),
    )

    assert primeira.status_code == 200

    segunda = client.post(
        "/api/tenant-booking/agendar",
        json={
            **payload_agendamento(
                data_alvo,
                "10:00",
            ),
            "cliente_nome":
                "Segundo Cliente",
            "telefone_cliente":
                "81977777777",
        },
    )

    assert segunda.status_code == 409

    detalhe = segunda.json().get(
        "detail"
    )

    assert detalhe
