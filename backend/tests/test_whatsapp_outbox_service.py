import pytest

from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import whatsapp_outbox_service
from services import whatsapp_outbound_service


@pytest.fixture()
def ambiente_outbox():
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


def criar_mensagem(
    db,
    *,
    chave="meta:wamid.in.001",
):
    return (
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
                "Escolha um servico.",
        )
    )


def test_cria_mensagem_pendente(
    ambiente_outbox,
):
    mensagem = criar_mensagem(
        ambiente_outbox
    )

    assert mensagem.status == "pendente"
    assert mensagem.tentativas == 0

    assert (
        mensagem.provider_message_id
        is None
    )


def test_mesma_chave_reutiliza_registro(
    ambiente_outbox,
):
    primeira = criar_mensagem(
        ambiente_outbox
    )

    segunda = criar_mensagem(
        ambiente_outbox
    )

    assert primeira.id == segunda.id

    assert (
        ambiente_outbox.query(
            models.OutboxMensagemWhatsApp
        ).count()
        == 1
    )


def test_fake_entrega_marca_enviada(
    ambiente_outbox,
):
    mensagem = criar_mensagem(
        ambiente_outbox
    )

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        whatsapp_outbox_service
        .tentar_entregar_mensagem_outbox(
            db=ambiente_outbox,
            mensagem=mensagem,
            transporte=transporte,
        )
    )

    ambiente_outbox.refresh(
        mensagem
    )

    assert resultado["enviado"] is True
    assert mensagem.status == "enviada"
    assert mensagem.tentativas == 1

    assert (
        mensagem.provider_message_id
        == "fake-1"
    )

    assert mensagem.enviado_em is not None


def test_mensagem_enviada_nao_duplica_envio(
    ambiente_outbox,
):
    mensagem = criar_mensagem(
        ambiente_outbox
    )

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    (
        whatsapp_outbox_service
        .tentar_entregar_mensagem_outbox(
            db=ambiente_outbox,
            mensagem=mensagem,
            transporte=transporte,
        )
    )

    resultado = (
        whatsapp_outbox_service
        .tentar_entregar_mensagem_outbox(
            db=ambiente_outbox,
            mensagem=mensagem,
            transporte=transporte,
        )
    )

    assert len(
        transporte.envios
    ) == 1

    assert resultado[
        "idempotente"
    ] is True


def test_falha_marca_erro_e_preserva_mensagem(
    ambiente_outbox,
):
    mensagem = criar_mensagem(
        ambiente_outbox
    )

    class TransporteFalha:
        def enviar_texto(
            self,
            *,
            phone_number_id,
            telefone_destino,
            texto,
        ):
            raise HTTPException(
                status_code=502,
                detail="falha simulada",
            )

    with pytest.raises(
        HTTPException
    ):
        (
            whatsapp_outbox_service
            .tentar_entregar_mensagem_outbox(
                db=ambiente_outbox,
                mensagem=mensagem,
                transporte=TransporteFalha(),
            )
        )

    ambiente_outbox.refresh(
        mensagem
    )

    assert mensagem.status == "erro"
    assert mensagem.tentativas == 1

    assert (
        mensagem.ultimo_erro
        == "falha simulada"
    )


def test_mensagem_com_erro_pode_ser_retentada(
    ambiente_outbox,
):
    mensagem = criar_mensagem(
        ambiente_outbox
    )

    class TransporteFalha:
        def enviar_texto(
            self,
            *,
            phone_number_id,
            telefone_destino,
            texto,
        ):
            raise HTTPException(
                status_code=502,
                detail="falha temporaria",
            )

    with pytest.raises(
        HTTPException
    ):
        (
            whatsapp_outbox_service
            .tentar_entregar_mensagem_outbox(
                db=ambiente_outbox,
                mensagem=mensagem,
                transporte=TransporteFalha(),
            )
        )

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        whatsapp_outbox_service
        .tentar_entregar_mensagem_outbox(
            db=ambiente_outbox,
            mensagem=mensagem,
            transporte=transporte,
        )
    )

    ambiente_outbox.refresh(
        mensagem
    )

    assert resultado["enviado"] is True
    assert mensagem.status == "enviada"
    assert mensagem.tentativas == 2

    assert (
        mensagem.provider_message_id
        == "fake-1"
    )


def test_chave_vazia_rejeitada(
    ambiente_outbox,
):
    with pytest.raises(
        HTTPException
    ) as erro:
        (
            whatsapp_outbox_service
            .criar_ou_obter_mensagem_outbox(
                db=ambiente_outbox,
                provedor="meta",
                chave_idempotencia="",
                barbearia_slug="clinica-a",
                phone_number_id="phone-a",
                telefone_destino=
                    "5581999999999",
                texto="Teste",
            )
        )

    assert erro.value.status_code == 422


def test_dois_eventos_criam_duas_mensagens(
    ambiente_outbox,
):
    primeira = criar_mensagem(
        ambiente_outbox,
        chave="meta:wamid.001",
    )

    segunda = criar_mensagem(
        ambiente_outbox,
        chave="meta:wamid.002",
    )

    assert primeira.id != segunda.id

    assert (
        ambiente_outbox.query(
            models.OutboxMensagemWhatsApp
        ).count()
        == 2
    )
