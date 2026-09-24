import hashlib
import hmac
import json

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from routers import whatsapp_webhook_router


VERIFY_TOKEN = "verify-token-teste"
APP_SECRET = "app-secret-teste"


@pytest.fixture()
def ambiente_seguranca_meta(
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

    monkeypatch.setattr(
        whatsapp_webhook_router.settings,
        "whatsapp_verify_token",
        VERIFY_TOKEN,
    )

    monkeypatch.setattr(
        whatsapp_webhook_router.settings,
        "whatsapp_app_secret",
        APP_SECRET,
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


def payload_meta():
    return {
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

                            "messages": [
                                {
                                    "from":
                                        "5581988888888",

                                    "id":
                                        "wamid.seg.001",

                                    "type":
                                        "text",

                                    "text": {
                                        "body":
                                            "Oi"
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def assinatura(
    corpo: bytes,
) -> str:
    digest = hmac.new(
        APP_SECRET.encode(
            "utf-8"
        ),
        corpo,
        hashlib.sha256,
    ).hexdigest()

    return (
        "sha256="
        + digest
    )


def test_get_challenge_valido(
    ambiente_seguranca_meta,
):
    client = ambiente_seguranca_meta[
        "client"
    ]

    resposta = client.get(
        "/api/webhooks/whatsapp/meta",
        params={
            "hub.mode":
                "subscribe",

            "hub.verify_token":
                VERIFY_TOKEN,

            "hub.challenge":
                "1234567890",
        },
    )

    assert resposta.status_code == 200

    assert (
        resposta.text
        == "1234567890"
    )


def test_get_verify_token_invalido_retorna_403(
    ambiente_seguranca_meta,
):
    client = ambiente_seguranca_meta[
        "client"
    ]

    resposta = client.get(
        "/api/webhooks/whatsapp/meta",
        params={
            "hub.mode":
                "subscribe",

            "hub.verify_token":
                "token-errado",

            "hub.challenge":
                "123",
        },
    )

    assert resposta.status_code == 403


def test_get_mode_invalido_retorna_403(
    ambiente_seguranca_meta,
):
    client = ambiente_seguranca_meta[
        "client"
    ]

    resposta = client.get(
        "/api/webhooks/whatsapp/meta",
        params={
            "hub.mode":
                "nao-subscribe",

            "hub.verify_token":
                VERIFY_TOKEN,

            "hub.challenge":
                "123",
        },
    )

    assert resposta.status_code == 403


def test_post_assinatura_valida_processa_evento(
    ambiente_seguranca_meta,
):
    client = ambiente_seguranca_meta[
        "client"
    ]

    corpo = json.dumps(
        payload_meta(),
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    resposta = client.post(
        "/api/webhooks/whatsapp/meta",
        content=corpo,
        headers={
            "Content-Type":
                "application/json",

            "X-Hub-Signature-256":
                assinatura(
                    corpo
                ),
        },
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados[
        "processados"
    ] == 1

    assert (
        dados["resultados"][0][
            "tenant_slug"
        ]
        == "clinica-a"
    )


def test_post_sem_assinatura_retorna_401(
    ambiente_seguranca_meta,
):
    client = ambiente_seguranca_meta[
        "client"
    ]

    corpo = json.dumps(
        payload_meta()
    ).encode(
        "utf-8"
    )

    resposta = client.post(
        "/api/webhooks/whatsapp/meta",
        content=corpo,
        headers={
            "Content-Type":
                "application/json",
        },
    )

    assert resposta.status_code == 401


def test_post_assinatura_invalida_retorna_401_e_nao_processa(
    ambiente_seguranca_meta,
):
    db = ambiente_seguranca_meta[
        "db"
    ]

    client = ambiente_seguranca_meta[
        "client"
    ]

    corpo = json.dumps(
        payload_meta()
    ).encode(
        "utf-8"
    )

    resposta = client.post(
        "/api/webhooks/whatsapp/meta",
        content=corpo,
        headers={
            "Content-Type":
                "application/json",

            "X-Hub-Signature-256":
                (
                    "sha256="
                    + ("0" * 64)
                ),
        },
    )

    assert resposta.status_code == 401

    assert (
        db.query(
            models.EventoWhatsAppRecebido
        )
        .count()
        == 0
    )

    assert (
        db.query(
            models.SessaoBookingWhatsApp
        )
        .count()
        == 0
    )
