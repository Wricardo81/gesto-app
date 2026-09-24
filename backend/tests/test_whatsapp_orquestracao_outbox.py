import pytest

from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import whatsapp_orquestracao_service
from services import whatsapp_outbound_service
from services import whatsapp_webhook_service


@pytest.fixture()
def ambiente_outbox_orquestracao():
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
        models.IntegracaoWhatsAppTenant.__table__,
        models.EventoWhatsAppRecebido.__table__,
        models.OutboxMensagemWhatsApp.__table__,
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

    servico = models.ServicoBarbearia(
        barbearia_slug="clinica-a",
        nome="Consulta",
        preco=150,
        duracao=30,
    )

    profissional = models.Profissional(
        barbearia_slug="clinica-a",
        nome="Dra Ana",
    )

    integracao = models.IntegracaoWhatsAppTenant(
        barbearia_slug="clinica-a",
        phone_number_id="phone-clinica-a",
        business_account_id="waba-a",
        numero_exibicao="5581111111111",
        ativo=True,
    )

    db.add_all([
        servico,
        profissional,
        integracao,
    ])

    db.flush()

    db.add(
        models.ServicoProfissional(
            barbearia_slug="clinica-a",
            servico_id=servico.id,
            profissional_id=
                profissional.id,
        )
    )

    db.commit()

    try:
        yield db

    finally:
        db.close()


def payload_meta(
    *,
    message_id="wamid.outbox.001",
    texto="Oi",
):
    return {
        "object":
            "whatsapp_business_account",

        "entry": [
            {
                "id":
                    "waba-a",

                "changes": [
                    {
                        "field":
                            "messages",

                        "value": {
                            "metadata": {
                                "phone_number_id":
                                    "phone-clinica-a",
                            },

                            "messages": [
                                {
                                    "from":
                                        "5581999999999",

                                    "id":
                                        message_id,

                                    "type":
                                        "text",

                                    "text": {
                                        "body":
                                            texto
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


class TransporteFalha:
    def __init__(
        self,
    ):
        self.tentativas = 0

    def enviar_texto(
        self,
        *,
        phone_number_id,
        telefone_destino,
        texto,
    ):
        self.tentativas += 1

        raise HTTPException(
            status_code=502,
            detail="falha temporaria",
        )


def test_falha_outbound_persiste_outbox(
    ambiente_outbox_orquestracao,
):
    db = ambiente_outbox_orquestracao

    transporte = TransporteFalha()

    with pytest.raises(
        HTTPException
    ) as erro:
        (
            whatsapp_orquestracao_service
            .processar_payload_meta_e_responder(
                db=db,
                payload=payload_meta(),
                transporte=transporte,
            )
        )

    assert erro.value.status_code == 502

    evento = (
        db.query(
            models.EventoWhatsAppRecebido
        )
        .one()
    )

    outbox = (
        db.query(
            models.OutboxMensagemWhatsApp
        )
        .one()
    )

    sessao = (
        db.query(
            models.SessaoBookingWhatsApp
        )
        .one()
    )

    assert evento.status == "processado"

    assert outbox.status == "erro"
    assert outbox.tentativas == 1

    assert (
        outbox.chave_idempotencia
        == "wamid.outbox.001"
    )

    assert sessao.etapa == "aguardando_servico"


def test_retry_reenvia_outbox_sem_reprocessar_booking(
    ambiente_outbox_orquestracao,
):
    db = ambiente_outbox_orquestracao

    payload = payload_meta(
        message_id=
            "wamid.retry.001"
    )

    with pytest.raises(
        HTTPException
    ):
        (
            whatsapp_orquestracao_service
            .processar_payload_meta_e_responder(
                db=db,
                payload=payload,
                transporte=TransporteFalha(),
            )
        )

    sessao_antes = (
        db.query(
            models.SessaoBookingWhatsApp
        )
        .one()
    )

    sessao_id = sessao_antes.id
    etapa_antes = sessao_antes.etapa

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        whatsapp_orquestracao_service
        .processar_payload_meta_e_responder(
            db=db,
            payload=payload,
            transporte=transporte,
        )
    )

    outbox = (
        db.query(
            models.OutboxMensagemWhatsApp
        )
        .one()
    )

    sessoes = (
        db.query(
            models.SessaoBookingWhatsApp
        )
        .all()
    )

    assert resultado["total_envios"] == 1

    assert len(
        transporte.envios
    ) == 1

    assert outbox.status == "enviada"
    assert outbox.tentativas == 2

    assert len(sessoes) == 1
    assert sessoes[0].id == sessao_id
    assert sessoes[0].etapa == etapa_antes


def test_retry_apos_sucesso_nao_duplica_envio(
    ambiente_outbox_orquestracao,
):
    db = ambiente_outbox_orquestracao

    payload = payload_meta(
        message_id=
            "wamid.sucesso.001"
    )

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    primeira = (
        whatsapp_orquestracao_service
        .processar_payload_meta_e_responder(
            db=db,
            payload=payload,
            transporte=transporte,
        )
    )

    segunda = (
        whatsapp_orquestracao_service
        .processar_payload_meta_e_responder(
            db=db,
            payload=payload,
            transporte=transporte,
        )
    )

    outbox = (
        db.query(
            models.OutboxMensagemWhatsApp
        )
        .one()
    )

    assert primeira["total_envios"] == 1
    assert segunda["total_envios"] == 0

    assert len(
        transporte.envios
    ) == 1

    assert outbox.status == "enviada"
    assert outbox.tentativas == 1


def test_retry_recupera_janela_entre_inbound_e_outbox(
    ambiente_outbox_orquestracao,
):
    db = ambiente_outbox_orquestracao

    payload = payload_meta(
        message_id=
            "wamid.crash.001"
    )

    resultado_inbound = (
        whatsapp_webhook_service
        .processar_payload_meta(
            db=db,
            payload=payload,
        )
    )

    assert (
        resultado_inbound[
            "processados"
        ]
        == 1
    )

    assert (
        db.query(
            models.OutboxMensagemWhatsApp
        ).count()
        == 0
    )

    sessoes_antes = (
        db.query(
            models.SessaoBookingWhatsApp
        )
        .all()
    )

    assert len(
        sessoes_antes
    ) == 1

    sessao_id = sessoes_antes[0].id
    etapa = sessoes_antes[0].etapa

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    retry = (
        whatsapp_orquestracao_service
        .processar_payload_meta_e_responder(
            db=db,
            payload=payload,
            transporte=transporte,
        )
    )

    sessoes_depois = (
        db.query(
            models.SessaoBookingWhatsApp
        )
        .all()
    )

    outbox = (
        db.query(
            models.OutboxMensagemWhatsApp
        )
        .one()
    )

    assert retry["total_envios"] == 1

    assert len(
        transporte.envios
    ) == 1

    assert outbox.status == "enviada"
    assert outbox.tentativas == 1

    assert len(
        sessoes_depois
    ) == 1

    assert (
        sessoes_depois[0].id
        == sessao_id
    )

    assert (
        sessoes_depois[0].etapa
        == etapa
    )
