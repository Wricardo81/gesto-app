import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import booking_whatsapp_service


@pytest.fixture()
def ambiente_processador_booking():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    tabelas = [
        models.ServicoBarbearia.__table__,
        models.Profissional.__table__,
        models.ServicoProfissional.__table__,
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

    try:
        corte = models.ServicoBarbearia(
            barbearia_slug="tenant-a",
            nome="Corte",
            preco=50,
            duracao=30,
        )

        barba = models.ServicoBarbearia(
            barbearia_slug="tenant-a",
            nome="Barba",
            preco=35,
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

        servico_outro_tenant = (
            models.ServicoBarbearia(
                barbearia_slug="tenant-b",
                nome="Servico Tenant B",
                preco=90,
                duracao=60,
            )
        )

        db.add_all([
            corte,
            barba,
            ana,
            bruno,
            servico_outro_tenant,
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

            models.ServicoProfissional(
                barbearia_slug="tenant-a",
                servico_id=barba.id,
                profissional_id=bruno.id,
            ),
        ])

        db.commit()

        yield db

    finally:
        db.close()


def test_primeira_mensagem_inicia_fluxo_e_lista_servicos(
    ambiente_processador_booking,
):
    db = ambiente_processador_booking

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="(81) 99999-9999",
            mensagem="Oi",
        )
    )

    assert (
        resposta["etapa"]
        == "aguardando_servico"
    )

    assert resposta["sessao"][
        "telefone_cliente"
    ] == "81999999999"

    assert resposta["opcoes"] == [
        "1. Barba",
        "2. Corte",
    ]


def test_servicos_de_outro_tenant_nao_aparecem(
    ambiente_processador_booking,
):
    db = ambiente_processador_booking

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="ola",
        )
    )

    texto = " ".join(
        resposta["opcoes"]
    )

    assert "Servico Tenant B" not in texto


def test_servico_invalido_mantem_etapa_e_reexibe_opcoes(
    ambiente_processador_booking,
):
    db = ambiente_processador_booking

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="oi",
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="Banho",
        )
    )

    assert (
        resposta["etapa"]
        == "aguardando_servico"
    )

    assert "Nao encontrei" in resposta[
        "mensagem"
    ]

    assert resposta["opcoes"] == [
        "1. Barba",
        "2. Corte",
    ]


def test_escolha_servico_por_numero_avanca_para_profissional(
    ambiente_processador_booking,
):
    db = ambiente_processador_booking

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="oi",
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="2",
        )
    )

    assert (
        resposta["etapa"]
        == "aguardando_profissional"
    )

    assert resposta["sessao"][
        "servico"
    ] == "Corte"

    assert resposta["opcoes"] == [
        "1. Ana",
        "2. Bruno",
    ]


def test_escolha_servico_por_nome_avanca_para_profissional(
    ambiente_processador_booking,
):
    db = ambiente_processador_booking

    booking_whatsapp_service.processar_mensagem_booking(
        db=db,
        tenant_slug="tenant-a",
        telefone_cliente="81999999999",
        mensagem="oi",
    )

    resposta = (
        booking_whatsapp_service
        .processar_mensagem_booking(
            db=db,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
            mensagem="Barba",
        )
    )

    assert (
        resposta["etapa"]
        == "aguardando_profissional"
    )

    assert resposta["sessao"][
        "servico"
    ] == "Barba"

    assert resposta["opcoes"] == [
        "1. Bruno",
    ]
