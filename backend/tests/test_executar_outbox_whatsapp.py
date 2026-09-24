import importlib.util
from pathlib import Path

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import whatsapp_outbound_service


SCRIPT_PATH = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "scripts"
    / "executar_outbox_whatsapp.py"
)


def carregar_executor():
    spec = (
        importlib.util
        .spec_from_file_location(
            "executar_outbox_whatsapp",
            SCRIPT_PATH,
        )
    )

    modulo = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        modulo
    )

    return modulo


@pytest.fixture()
def ambiente_executor():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread":
                False,
        },
        poolclass=StaticPool,
    )

    models.OutboxMensagemWhatsApp.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    Session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    return Session


def adicionar_mensagem(
    Session,
    *,
    chave,
):
    db = Session()

    try:
        mensagem = (
            models.OutboxMensagemWhatsApp(
                provedor="meta",
                chave_idempotencia=chave,
                barbearia_slug="tenant-a",
                phone_number_id="phone-a",
                telefone_destino=
                    "5581999999999",
                texto="Mensagem teste",
                status="pendente",
                tentativas=0,
            )
        )

        db.add(
            mensagem
        )

        db.commit()

    finally:
        db.close()


def test_executor_processa_lote_fake(
    ambiente_executor,
):
    executor = carregar_executor()

    adicionar_mensagem(
        ambiente_executor,
        chave="exec-1",
    )

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        executor
        .executar_outbox_whatsapp(
            limite=10,
            session_factory=
                ambiente_executor,
            transporte=
                transporte,
        )
    )

    assert (
        resultado["executor"]
        == "whatsapp_outbox"
    )

    assert (
        resultado["selecionadas"]
        == 1
    )

    assert (
        resultado["enviadas"]
        == 1
    )

    assert (
        resultado["falhas"]
        == 0
    )

    assert len(
        transporte.envios
    ) == 1


def test_executor_sem_mensagens_retorna_zero(
    ambiente_executor,
):
    executor = carregar_executor()

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        executor
        .executar_outbox_whatsapp(
            limite=10,
            session_factory=
                ambiente_executor,
            transporte=
                transporte,
        )
    )

    assert (
        resultado["selecionadas"]
        == 0
    )

    assert (
        resultado["enviadas"]
        == 0
    )

    assert (
        resultado["falhas"]
        == 0
    )


def test_executor_respeita_limite(
    ambiente_executor,
):
    executor = carregar_executor()

    for indice in range(
        3
    ):
        adicionar_mensagem(
            ambiente_executor,
            chave=
                f"exec-limite-{indice}",
        )

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        executor
        .executar_outbox_whatsapp(
            limite=2,
            session_factory=
                ambiente_executor,
            transporte=
                transporte,
        )
    )

    assert (
        resultado["selecionadas"]
        == 2
    )

    assert len(
        transporte.envios
    ) == 2


def test_executor_fecha_sessao(
    ambiente_executor,
):
    executor = carregar_executor()

    estado = {
        "fechou":
            False,
    }

    sessao_real = (
        ambiente_executor()
    )

    close_original = (
        sessao_real.close
    )

    def close_spy():
        estado["fechou"] = True
        return close_original()

    sessao_real.close = close_spy

    def factory():
        return sessao_real

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    executor.executar_outbox_whatsapp(
        limite=1,
        session_factory=factory,
        transporte=transporte,
    )

    assert estado[
        "fechou"
    ] is True


def test_executor_rollback_em_excecao(
    ambiente_executor,
):
    executor = carregar_executor()

    estado = {
        "rollback":
            False,
        "close":
            False,
    }

    sessao_real = (
        ambiente_executor()
    )

    rollback_original = (
        sessao_real.rollback
    )

    close_original = (
        sessao_real.close
    )

    def rollback_spy():
        estado["rollback"] = True
        return rollback_original()

    def close_spy():
        estado["close"] = True
        return close_original()

    sessao_real.rollback = (
        rollback_spy
    )

    sessao_real.close = (
        close_spy
    )

    def factory():
        return sessao_real

    class TransporteQueFalha:
        def enviar_texto(
            self,
            *,
            phone_number_id,
            telefone_destino,
            texto,
        ):
            raise RuntimeError(
                "falha teste"
            )

    adicionar_mensagem(
        ambiente_executor,
        chave="exec-falha",
    )

    resultado = (
        executor
        .executar_outbox_whatsapp(
            limite=1,
            session_factory=factory,
            transporte=
                TransporteQueFalha(),
        )
    )

    assert (
        resultado["falhas"]
        == 1
    )

    assert estado["close"] is True


def test_factory_configurada_default_fake(
    monkeypatch,
):
    executor = carregar_executor()

    monkeypatch.setattr(
        executor.settings,
        "whatsapp_transport_mode",
        "fake",
    )

    transporte = (
        executor
        .criar_transporte_configurado()
    )

    assert isinstance(
        transporte,
        whatsapp_outbound_service
        .TransporteFakeWhatsApp,
    )
