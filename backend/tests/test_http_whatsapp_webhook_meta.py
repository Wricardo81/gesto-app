import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from routers import whatsapp_webhook_router


@pytest.fixture()
def ambiente_meta(monkeypatch):
    monkeypatch.setattr(
        whatsapp_webhook_router
        .whatsapp_webhook_service,
        "validar_assinatura_meta",
        lambda **kwargs: None,
    )

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

    app = FastAPI()

    app.include_router(
        whatsapp_webhook_router.router
    )

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[
        whatsapp_webhook_router.get_db
    ] = override_get_db

    client = TestClient(app)

    try:
        yield {
            "db": db,
            "client": client,
        }

    finally:
        client.close()
        db.close()


def payload_texto(
    *,
    message_id="wamid.001",
    texto="Oi",
):
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "waba-001",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product":
                                "whatsapp",

                            "metadata": {
                                "display_phone_number":
                                    "5581999999999",

                                "phone_number_id":
                                    "123456789",
                            },

                            "contacts": [
                                {
                                    "wa_id":
                                        "5581988888888",

                                    "profile": {
                                        "name":
                                            "Ricardo"
                                    },
                                }
                            ],

                            "messages": [
                                {
                                    "from":
                                        "5581988888888",

                                    "id":
                                        message_id,

                                    "timestamp":
                                        "1720000000",

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


def test_meta_texto_inicia_booking(
    ambiente_meta,
):
    client = ambiente_meta[
        "client"
    ]

    resposta = client.post(
        "/api/webhooks/whatsapp/meta",
        json=payload_texto(),
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["recebido"] is True
    assert dados["processados"] == 1

    resultado = dados[
        "resultados"
    ][0]

    assert (
        resultado["tenant_slug"]
        == "clinica-a"
    )

    assert (
        resultado["telefone_cliente"]
        == "5581988888888"
    )

    assert (
        resultado["resposta"]["etapa"]
        == "aguardando_servico"
    )

    assert resultado[
        "resposta"
    ]["opcoes"] == [
        "1. Consulta",
    ]


def test_meta_usa_phone_number_id_e_nao_display_phone_number(
    ambiente_meta,
):
    client = ambiente_meta[
        "client"
    ]

    payload = payload_texto()

    payload[
        "entry"
    ][0][
        "changes"
    ][0][
        "value"
    ][
        "metadata"
    ][
        "display_phone_number"
    ] = "0000000000000"

    resposta = client.post(
        "/api/webhooks/whatsapp/meta",
        json=payload,
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert (
        dados["resultados"][0][
            "tenant_slug"
        ]
        == "clinica-a"
    )


def test_meta_evento_repetido_e_idempotente(
    ambiente_meta,
):
    client = ambiente_meta[
        "client"
    ]

    primeira = client.post(
        "/api/webhooks/whatsapp/meta",
        json=payload_texto(
            message_id="wamid.dup",
        ),
    )

    segunda = client.post(
        "/api/webhooks/whatsapp/meta",
        json=payload_texto(
            message_id="wamid.dup",
        ),
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 200

    dados_primeira = primeira.json()
    dados_segunda = segunda.json()

    assert (
        dados_primeira["resultados"][0][
            "idempotente"
        ]
        is False
    )

    assert (
        dados_segunda["resultados"][0][
            "idempotente"
        ]
        is True
    )


def test_meta_status_sem_messages_e_ignorado(
    ambiente_meta,
):
    client = ambiente_meta[
        "client"
    ]

    payload = {
        "object":
            "whatsapp_business_account",

        "entry": [
            {
                "id": "waba-001",
                "changes": [
                    {
                        "field": "messages",
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

    assert dados["processados"] == 0
    assert dados["ignorados"] == 1
    assert dados["resultados"] == []


def test_meta_tipo_nao_texto_e_ignorado(
    ambiente_meta,
):
    client = ambiente_meta[
        "client"
    ]

    payload = payload_texto()

    mensagem = payload[
        "entry"
    ][0][
        "changes"
    ][0][
        "value"
    ][
        "messages"
    ][0]

    mensagem["type"] = "image"

    mensagem.pop(
        "text"
    )

    resposta = client.post(
        "/api/webhooks/whatsapp/meta",
        json=payload,
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["processados"] == 0
    assert dados["ignorados"] == 1


def test_meta_duas_mensagens_sao_processadas_na_ordem(
    ambiente_meta,
):
    client = ambiente_meta[
        "client"
    ]

    payload = payload_texto(
        message_id="wamid.001",
        texto="Oi",
    )

    value = payload[
        "entry"
    ][0][
        "changes"
    ][0][
        "value"
    ]

    value[
        "messages"
    ].append(
        {
            "from":
                "5581988888888",

            "id":
                "wamid.002",

            "timestamp":
                "1720000001",

            "type":
                "text",

            "text": {
                "body":
                    "Consulta"
            },
        }
    )

    resposta = client.post(
        "/api/webhooks/whatsapp/meta",
        json=payload,
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["processados"] == 2

    primeira = dados[
        "resultados"
    ][0]

    segunda = dados[
        "resultados"
    ][1]

    assert (
        primeira["resposta"]["etapa"]
        == "aguardando_servico"
    )

    assert (
        segunda["resposta"]["etapa"]
        == "aguardando_profissional"
    )

    assert (
        primeira["resposta"]["sessao"]["id"]
        == segunda["resposta"]["sessao"]["id"]
    )
