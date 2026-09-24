from datetime import timedelta

import pytest

from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import whatsapp_outbox_service
from services import whatsapp_outbound_service


@pytest.fixture()
def ambiente_claim():
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
            texto="Teste",
        )
    )

    mensagem.status = status

    db.commit()
    db.refresh(
        mensagem
    )

    return mensagem


def test_claim_marca_processando(
    ambiente_claim,
):
    db = ambiente_claim

    mensagem = criar(
        db,
        chave="claim-1",
    )

    claimed = (
        whatsapp_outbox_service
        .claim_mensagens_outbox(
            db,
            limite=10,
        )
    )

    db.refresh(
        mensagem
    )

    assert len(
        claimed
    ) == 1

    assert (
        mensagem.status
        == "processando"
    )

    assert (
        mensagem.processando_desde
        is not None
    )


def test_claim_nao_pega_processando_recente(
    ambiente_claim,
):
    db = ambiente_claim

    mensagem = criar(
        db,
        chave="claim-recente",
        status="processando",
    )

    mensagem.processando_desde = (
        whatsapp_outbox_service
        .agora_utc_naive()
    )

    db.commit()

    claimed = (
        whatsapp_outbox_service
        .claim_mensagens_outbox(
            db,
            limite=10,
        )
    )

    assert claimed == []


def test_claim_recupera_processando_abandonado(
    ambiente_claim,
):
    db = ambiente_claim

    mensagem = criar(
        db,
        chave="claim-antigo",
        status="processando",
    )

    mensagem.processando_desde = (
        whatsapp_outbox_service
        .agora_utc_naive()
        - timedelta(
            seconds=(
                whatsapp_outbox_service
                .CLAIM_EXPIRA_SEGUNDOS
                + 1
            )
        )
    )

    db.commit()

    claimed = (
        whatsapp_outbox_service
        .claim_mensagens_outbox(
            db,
            limite=10,
        )
    )

    assert len(
        claimed
    ) == 1

    assert claimed[0].id == mensagem.id


def test_backoff_impede_retry_imediato(
    ambiente_claim,
):
    db = ambiente_claim

    mensagem = criar(
        db,
        chave="backoff-1",
    )

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    class Falha:
        def enviar_texto(
            self,
            *,
            phone_number_id,
            telefone_destino,
            texto,
        ):
            raise HTTPException(
                status_code=502,
                detail="falha",
            )

    claimed = (
        whatsapp_outbox_service
        .claim_mensagens_outbox(
            db,
            limite=1,
        )
    )

    with pytest.raises(
        HTTPException
    ):
        (
            whatsapp_outbox_service
            .tentar_entregar_mensagem_outbox(
                db=db,
                mensagem=claimed[0],
                transporte=Falha(),
            )
        )

    db.refresh(
        mensagem
    )

    assert mensagem.status == "erro"

    assert (
        mensagem.proxima_tentativa_em
        is not None
    )

    novo_claim = (
        whatsapp_outbox_service
        .claim_mensagens_outbox(
            db,
            limite=1,
        )
    )

    assert novo_claim == []

    assert transporte.envios == []


def test_backoff_vencido_permite_retry(
    ambiente_claim,
):
    db = ambiente_claim

    mensagem = criar(
        db,
        chave="backoff-vencido",
        status="erro",
    )

    mensagem.tentativas = 1

    mensagem.proxima_tentativa_em = (
        whatsapp_outbox_service
        .agora_utc_naive()
        - timedelta(
            seconds=1
        )
    )

    db.commit()

    claimed = (
        whatsapp_outbox_service
        .claim_mensagens_outbox(
            db,
            limite=1,
        )
    )

    assert len(
        claimed
    ) == 1

    assert claimed[0].id == mensagem.id


def test_maximo_tentativas_vira_esgotada(
    ambiente_claim,
):
    db = ambiente_claim

    mensagem = criar(
        db,
        chave="max-tentativas",
    )

    mensagem.tentativas = (
        whatsapp_outbox_service
        .MAX_TENTATIVAS_OUTBOX
        - 1
    )

    mensagem.status = "processando"

    db.commit()

    class Falha:
        def enviar_texto(
            self,
            *,
            phone_number_id,
            telefone_destino,
            texto,
        ):
            raise HTTPException(
                status_code=502,
                detail="falha final",
            )

    with pytest.raises(
        HTTPException
    ):
        (
            whatsapp_outbox_service
            .tentar_entregar_mensagem_outbox(
                db=db,
                mensagem=mensagem,
                transporte=Falha(),
            )
        )

    db.refresh(
        mensagem
    )

    assert (
        mensagem.tentativas
        == whatsapp_outbox_service
        .MAX_TENTATIVAS_OUTBOX
    )

    assert (
        mensagem.status
        == "esgotada"
    )

    assert (
        mensagem.proxima_tentativa_em
        is None
    )


def test_mensagem_esgotada_nao_entra_no_claim(
    ambiente_claim,
):
    db = ambiente_claim

    mensagem = criar(
        db,
        chave="esgotada",
        status="esgotada",
    )

    mensagem.tentativas = (
        whatsapp_outbox_service
        .MAX_TENTATIVAS_OUTBOX
    )

    db.commit()

    claimed = (
        whatsapp_outbox_service
        .claim_mensagens_outbox(
            db,
            limite=10,
        )
    )

    assert claimed == []


def test_sucesso_limpa_campos_de_retry(
    ambiente_claim,
):
    db = ambiente_claim

    mensagem = criar(
        db,
        chave="sucesso",
        status="erro",
    )

    mensagem.proxima_tentativa_em = (
        whatsapp_outbox_service
        .agora_utc_naive()
        - timedelta(
            seconds=1
        )
    )

    db.commit()

    claimed = (
        whatsapp_outbox_service
        .claim_mensagens_outbox(
            db,
            limite=1,
        )
    )

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    (
        whatsapp_outbox_service
        .tentar_entregar_mensagem_outbox(
            db=db,
            mensagem=claimed[0],
            transporte=transporte,
        )
    )

    db.refresh(
        mensagem
    )

    assert mensagem.status == "enviada"

    assert (
        mensagem.processando_desde
        is None
    )

    assert (
        mensagem.proxima_tentativa_em
        is None
    )
