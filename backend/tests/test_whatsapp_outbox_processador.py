import pytest

from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import whatsapp_outbox_service
from services import whatsapp_outbound_service


@pytest.fixture()
def ambiente_processador_outbox():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
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

    db = Session()

    try:
        yield db

    finally:
        db.close()


def criar(
    db,
    *,
    chave,
    status="pendente",
):
    mensagem = (
        whatsapp_outbox_service
        .criar_ou_obter_mensagem_outbox(
            db=db,
            provedor="meta",
            chave_idempotencia=chave,
            barbearia_slug="clinica-a",
            phone_number_id="phone-a",
            telefone_destino=
                "5581999999999",
            texto=
                "Mensagem de teste",
        )
    )

    mensagem.status = status

    db.commit()
    db.refresh(
        mensagem
    )

    return mensagem


def test_lista_pendente_e_erro(
    ambiente_processador_outbox,
):
    db = ambiente_processador_outbox

    criar(
        db,
        chave="msg-1",
        status="pendente",
    )

    criar(
        db,
        chave="msg-2",
        status="erro",
    )

    criar(
        db,
        chave="msg-3",
        status="enviada",
    )

    mensagens = (
        whatsapp_outbox_service
        .listar_mensagens_recuperaveis(
            db,
            limite=10,
        )
    )

    assert len(
        mensagens
    ) == 2

    assert {
        item.status
        for item in mensagens
    } == {
        "pendente",
        "erro",
    }


def test_lote_entrega_pendentes(
    ambiente_processador_outbox,
):
    db = ambiente_processador_outbox

    criar(
        db,
        chave="msg-1",
    )

    criar(
        db,
        chave="msg-2",
    )

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        whatsapp_outbox_service
        .processar_lote_outbox(
            db,
            transporte=transporte,
            limite=10,
        )
    )

    assert resultado[
        "selecionadas"
    ] == 2

    assert resultado[
        "enviadas"
    ] == 2

    assert resultado[
        "falhas"
    ] == 0

    assert len(
        transporte.envios
    ) == 2


def test_lote_nao_pega_mensagem_enviada(
    ambiente_processador_outbox,
):
    db = ambiente_processador_outbox

    mensagem = criar(
        db,
        chave="msg-ja-enviada",
        status="enviada",
    )

    mensagem.provider_message_id = (
        "wamid.existente"
    )

    db.commit()

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        whatsapp_outbox_service
        .processar_lote_outbox(
            db,
            transporte=transporte,
        )
    )

    assert resultado[
        "selecionadas"
    ] == 0

    assert transporte.envios == []


def test_falha_de_uma_nao_interrompe_lote(
    ambiente_processador_outbox,
):
    db = ambiente_processador_outbox

    criar(
        db,
        chave="msg-1",
    )

    criar(
        db,
        chave="msg-2",
    )

    class TransporteIntermitente:
        def __init__(
            self,
        ):
            self.contador = 0

        def enviar_texto(
            self,
            *,
            phone_number_id,
            telefone_destino,
            texto,
        ):
            self.contador += 1

            if self.contador == 1:
                raise HTTPException(
                    status_code=502,
                    detail="falha simulada",
                )

            return {
                "enviado":
                    True,

                "provider":
                    "fake",

                "provider_message_id":
                    "fake-ok",
            }

    resultado = (
        whatsapp_outbox_service
        .processar_lote_outbox(
            db,
            transporte=
                TransporteIntermitente(),
        )
    )

    assert resultado[
        "selecionadas"
    ] == 2

    assert resultado[
        "enviadas"
    ] == 1

    assert resultado[
        "falhas"
    ] == 1

    assert (
        db.query(
            models.OutboxMensagemWhatsApp
        )
        .filter(
            models.OutboxMensagemWhatsApp.status
            == "enviada"
        )
        .count()
        == 1
    )

    assert (
        db.query(
            models.OutboxMensagemWhatsApp
        )
        .filter(
            models.OutboxMensagemWhatsApp.status
            == "erro"
        )
        .count()
        == 1
    )


def test_lote_reprocessa_mensagem_com_erro(
    ambiente_processador_outbox,
):
    db = ambiente_processador_outbox

    mensagem = criar(
        db,
        chave="msg-erro",
        status="erro",
    )

    mensagem.tentativas = 1

    db.commit()

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        whatsapp_outbox_service
        .processar_lote_outbox(
            db,
            transporte=transporte,
        )
    )

    db.refresh(
        mensagem
    )

    assert resultado[
        "enviadas"
    ] == 1

    assert mensagem.status == "enviada"
    assert mensagem.tentativas == 2


def test_limite_e_respeitado(
    ambiente_processador_outbox,
):
    db = ambiente_processador_outbox

    for indice in range(
        5
    ):
        criar(
            db,
            chave=
                f"msg-{indice}",
        )

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        whatsapp_outbox_service
        .processar_lote_outbox(
            db,
            transporte=transporte,
            limite=2,
        )
    )

    assert resultado[
        "selecionadas"
    ] == 2

    assert resultado[
        "enviadas"
    ] == 2

    assert (
        db.query(
            models.OutboxMensagemWhatsApp
        )
        .filter(
            models.OutboxMensagemWhatsApp.status
            == "pendente"
        )
        .count()
        == 3
    )


def test_limite_invalido_rejeitado(
    ambiente_processador_outbox,
):
    with pytest.raises(
        HTTPException
    ) as erro:
        (
            whatsapp_outbox_service
            .listar_mensagens_recuperaveis(
                ambiente_processador_outbox,
                limite=0,
            )
        )

    assert (
        erro.value.status_code
        == 422
    )
