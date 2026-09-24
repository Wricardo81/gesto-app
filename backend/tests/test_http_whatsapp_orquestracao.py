import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from routers import whatsapp_webhook_router

from services import whatsapp_outbound_service


@pytest.fixture()
def ambiente_http_orquestracao(
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
        phone_number_id="123456789",
        business_account_id="waba-001",
        numero_exibicao="5581999999999",
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
            profissional_id=profissional.id,
        )
    )

    db.commit()

    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    monkeypatch.setattr(
        whatsapp_webhook_router
        .whatsapp_webhook_service,
        "validar_assinatura_meta",
        lambda **kwargs: None,
    )

    app = FastAPI()

    app.include_router(
        whatsapp_webhook_router.router
    )

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_transporte():
        return transporte

    app.dependency_overrides[
        whatsapp_webhook_router.get_db
    ] = override_get_db

    app.dependency_overrides[
        whatsapp_webhook_router
        .get_transporte_whatsapp
    ] = override_transporte

    client = TestClient(
        app
    )

    try:
        yield {
            "db":
                db,

            "client":
                client,

            "transporte":
                transporte,
        }

    finally:
        client.close()
        db.close()


def payload_meta(
    *,
    message_id="wamid.http.001",
    texto="Oi",
):
    return {
        "object":
            "whatsapp_business_account",

        "entry": [
            {
                "id":
                    "waba-001",

                "changes": [
                    {
                        "field":
                            "messages",

                        "value": {
                            "metadata": {
                                "phone_number_id":
                                    "123456789",
                            },

                            "messages": [
                                {
                                    "from":
                                        "5581988888888",

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


def enviar(
    client,
    *,
    message_id,
    texto,
):
    return client.post(
        "/api/webhooks/whatsapp/meta",
        json=payload_meta(
            message_id=message_id,
            texto=texto,
        ),
    )


def test_http_primeira_mensagem_gera_outbound(
    ambiente_http_orquestracao,
):
    client = ambiente_http_orquestracao[
        "client"
    ]

    transporte = ambiente_http_orquestracao[
        "transporte"
    ]

    resposta = enviar(
        client,
        message_id="wamid.http.001",
        texto="Oi",
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados[
        "processados"
    ] == 1

    assert dados[
        "total_envios"
    ] == 1

    assert len(
        transporte.envios
    ) == 1

    assert (
        "Escolha um servico"
        in transporte.envios[0][
            "texto"
        ]
    )

    assert (
        "1. Consulta"
        in transporte.envios[0][
            "texto"
        ]
    )


def test_http_retry_nao_duplica_outbound(
    ambiente_http_orquestracao,
):
    client = ambiente_http_orquestracao[
        "client"
    ]

    transporte = ambiente_http_orquestracao[
        "transporte"
    ]

    primeira = enviar(
        client,
        message_id="wamid.http.dup",
        texto="Oi",
    )

    segunda = enviar(
        client,
        message_id="wamid.http.dup",
        texto="Oi",
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 200

    assert (
        primeira.json()[
            "total_envios"
        ]
        == 1
    )

    assert (
        segunda.json()[
            "total_envios"
        ]
        == 0
    )

    assert len(
        transporte.envios
    ) == 1


def test_http_segunda_mensagem_avanca_conversa(
    ambiente_http_orquestracao,
):
    client = ambiente_http_orquestracao[
        "client"
    ]

    transporte = ambiente_http_orquestracao[
        "transporte"
    ]

    enviar(
        client,
        message_id="wamid.http.001",
        texto="Oi",
    )

    resposta = enviar(
        client,
        message_id="wamid.http.002",
        texto="Consulta",
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados[
        "total_envios"
    ] == 1

    assert len(
        transporte.envios
    ) == 2

    ultimo = transporte.envios[-1]

    assert (
        "profissional"
        in ultimo[
            "texto"
        ].lower()
    )

    assert (
        "1. Dra Ana"
        in ultimo[
            "texto"
        ]
    )


def test_http_status_meta_nao_gera_outbound(
    ambiente_http_orquestracao,
):
    client = ambiente_http_orquestracao[
        "client"
    ]

    transporte = ambiente_http_orquestracao[
        "transporte"
    ]

    payload = {
        "object":
            "whatsapp_business_account",

        "entry": [
            {
                "id":
                    "waba-001",

                "changes": [
                    {
                        "field":
                            "messages",

                        "value": {
                            "metadata": {
                                "phone_number_id":
                                    "123456789",
                            },

                            "statuses": [
                                {
                                    "id":
                                        "wamid.status",

                                    "status":
                                        "delivered",
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }

    resposta = client.post(
        "/api/webhooks/whatsapp/meta",
        json=payload,
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados[
        "processados"
    ] == 0

    assert dados[
        "total_envios"
    ] == 0

    assert transporte.envios == []
