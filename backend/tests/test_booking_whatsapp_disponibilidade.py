from datetime import date, timedelta

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import booking_whatsapp_service


@pytest.fixture()
def ambiente_booking_disponibilidade(
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

    monkeypatch.setattr(
        booking_whatsapp_service
        .agendamento_service,
        "validar_acesso_operacional_tenant",
        lambda *args, **kwargs: None,
    )

    data_alvo = (
        date.today()
        + timedelta(days=5)
    )

    try:
        config = models.ConfiguracaoAgenda(
            barbearia_slug="tenant-a",
            hora_abertura=9,
            hora_fechamento=12,
        )

        corte = models.ServicoBarbearia(
            barbearia_slug="tenant-a",
            nome="Corte",
            preco=50,
            duracao=30,
        )

        ana = models.Profissional(
            barbearia_slug="tenant-a",
            nome="Ana",
        )

        bruno = models.Profissional(
            barbearia_slug="tenant-a",
            nome="Bruno",
        )

        db.add_all([
            config,
            corte,
            ana,
            bruno,
        ])

        db.flush()

        db.add_all([
            models.ServicoProfissional(
                barbearia_slug="tenant-a",
                servico_id=corte.id,
                profissional_id=ana.id,
            ),
            models.ServicoProfissional(
                barbearia_slug="tenant-a",
                servico_id=corte.id,
                profissional_id=bruno.id,
            ),
        ])

        db.commit()

        yield {
            "db": db,
            "data": data_alvo,
        }

    finally:
        db.close()


def preparar_ate_profissional(db):
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


def test_escolha_profissional_avanca_para_data(
    ambiente_booking_disponibilidade,
):
    db = ambiente_booking_disponibilidade[
        "db"
    ]

    preparar_ate_profissional(db)

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="Ana",
        )
    )

    assert (
        resposta["etapa"]
        == "aguardando_data"
    )

    assert resposta["sessao"][
        "profissional"
    ] == "Ana"


def test_profissional_invalido_mantem_etapa(
    ambiente_booking_disponibilidade,
):
    db = ambiente_booking_disponibilidade[
        "db"
    ]

    preparar_ate_profissional(db)

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="Carlos",
        )
    )

    assert (
        resposta["etapa"]
        == "aguardando_profissional"
    )

    assert "Nao encontrei" in resposta[
        "mensagem"
    ]


def test_data_valida_lista_horarios_reais(
    ambiente_booking_disponibilidade,
):
    db = ambiente_booking_disponibilidade[
        "db"
    ]

    data_alvo = ambiente_booking_disponibilidade[
        "data"
    ]

    preparar_ate_profissional(db)

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ana",
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem=data_alvo.strftime(
                "%d/%m/%Y"
            ),
        )
    )

    assert (
        resposta["etapa"]
        == "aguardando_horario"
    )

    assert resposta["sessao"][
        "data"
    ] == data_alvo.isoformat()

    assert "1. 09:00" in resposta[
        "opcoes"
    ]


def test_horario_ocupado_nao_aparece(
    ambiente_booking_disponibilidade,
):
    db = ambiente_booking_disponibilidade[
        "db"
    ]

    data_alvo = ambiente_booking_disponibilidade[
        "data"
    ]

    db.add(
        models.Agendamento(
            barbearia_slug="tenant-a",
            cliente_nome="Existente",
            servico="Corte",
            profissional="Ana",
            data=data_alvo,
            horario="09:30",
            valor=50,
            telefone_cliente="81988888888",
            status="confirmado",
        )
    )

    db.commit()

    preparar_ate_profissional(db)

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ana",
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem=data_alvo.isoformat(),
        )
    )

    assert "09:30" not in " ".join(
        resposta["opcoes"]
    )


def test_bloqueio_nao_aparece_nos_horarios(
    ambiente_booking_disponibilidade,
):
    db = ambiente_booking_disponibilidade[
        "db"
    ]

    data_alvo = ambiente_booking_disponibilidade[
        "data"
    ]

    db.add(
        models.BloqueioAgenda(
            barbearia_slug="tenant-a",
            profissional="Ana",
            data=data_alvo,
            horario_inicio="10:00",
            horario_fim="10:30",
            dia_inteiro=False,
            motivo="Intervalo",
        )
    )

    db.commit()

    preparar_ate_profissional(db)

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ana",
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem=data_alvo.isoformat(),
        )
    )

    assert "10:00" not in " ".join(
        resposta["opcoes"]
    )


def test_escolha_horario_avanca_para_nome(
    ambiente_booking_disponibilidade,
):
    db = ambiente_booking_disponibilidade[
        "db"
    ]

    data_alvo = ambiente_booking_disponibilidade[
        "data"
    ]

    preparar_ate_profissional(db)

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ana",
    )

    resposta_data = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem=data_alvo.isoformat(),
        )
    )

    assert resposta_data["opcoes"]

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="1",
        )
    )

    assert (
        resposta["etapa"]
        == "aguardando_nome"
    )

    assert resposta["sessao"][
        "horario"
    ] == "09:00"


def test_data_invalida_mantem_aguardando_data(
    ambiente_booking_disponibilidade,
):
    db = ambiente_booking_disponibilidade[
        "db"
    ]

    preparar_ate_profissional(db)

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="Ana",
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="amanha de tarde",
        )
    )

    assert (
        resposta["etapa"]
        == "aguardando_data"
    )

    assert "Nao consegui" in resposta[
        "mensagem"
    ]
