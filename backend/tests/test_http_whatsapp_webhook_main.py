import hashlib
import hmac
import json

import pytest

from fastapi.testclient import TestClient

import main

from routers import whatsapp_webhook_router


VERIFY_TOKEN = "verify-main-teste"
APP_SECRET = "secret-main-teste"


@pytest.fixture()
def client_main(
    monkeypatch,
):
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

    client = TestClient(
        main.app
    )

    try:
        yield client
    finally:
        client.close()


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


def test_main_registra_get_meta(
    client_main,
):
    resposta = client_main.get(
        "/api/webhooks/whatsapp/meta",
        params={
            "hub.mode":
                "subscribe",

            "hub.verify_token":
                VERIFY_TOKEN,

            "hub.challenge":
                "abc123",
        },
    )

    assert resposta.status_code == 200
    assert resposta.text == "abc123"


def test_main_rejeita_get_token_invalido(
    client_main,
):
    resposta = client_main.get(
        "/api/webhooks/whatsapp/meta",
        params={
            "hub.mode":
                "subscribe",

            "hub.verify_token":
                "errado",

            "hub.challenge":
                "abc123",
        },
    )

    assert resposta.status_code == 403


def test_main_post_meta_sem_assinatura_retorna_401(
    client_main,
):
    resposta = client_main.post(
        "/api/webhooks/whatsapp/meta",
        json={
            "object":
                "whatsapp_business_account",

            "entry": [],
        },
    )

    assert resposta.status_code == 401


def test_main_post_meta_assinatura_valida_payload_vazio(
    client_main,
):
    corpo = json.dumps(
        {
            "object":
                "whatsapp_business_account",

            "entry": [],
        },
        separators=(
            ",",
            ":",
        ),
    ).encode(
        "utf-8"
    )

    resposta = client_main.post(
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

    assert dados["recebido"] is True
    assert dados["processados"] == 0
    assert dados["resultados"] == []


def test_main_nao_expoe_webhook_simulado(
    client_main,
):
    resposta = client_main.post(
        "/api/webhooks/whatsapp/simulado",
        json={
            "message_id":
                "msg-nao-deveria-existir",

            "phone_number_id":
                "phone-a",

            "telefone_cliente":
                "81999999999",

            "texto":
                "Oi",
        },
    )

    assert resposta.status_code == 404
