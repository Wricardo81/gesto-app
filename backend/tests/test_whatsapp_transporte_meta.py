import pytest
import requests

from fastapi import HTTPException

from services import whatsapp_outbound_service


class RespostaFake:
    def __init__(
        self,
        *,
        status_code=200,
        dados=None,
        json_invalido=False,
    ):
        self.status_code = status_code
        self._dados = dados
        self._json_invalido = json_invalido

    def json(
        self,
    ):
        if self._json_invalido:
            raise ValueError(
                "json invalido"
            )

        return self._dados


def criar_transporte(
    **kwargs,
):
    parametros = {
        "access_token":
            "token-de-teste",

        "graph_api_version":
            "vTEST",

        "base_url":
            "https://graph.example.test",

        "timeout_seconds":
            20,
    }

    parametros.update(
        kwargs
    )

    return (
        whatsapp_outbound_service
        .TransporteMetaWhatsApp(
            **parametros
        )
    )


def test_meta_monta_request_correto(
    monkeypatch,
):
    captura = {}

    def post_fake(
        url,
        *,
        json,
        headers,
        timeout,
    ):
        captura["url"] = url
        captura["json"] = json
        captura["headers"] = headers
        captura["timeout"] = timeout

        return RespostaFake(
            dados={
                "messages": [
                    {
                        "id":
                            "wamid.saida.001"
                    }
                ]
            }
        )

    monkeypatch.setattr(
        whatsapp_outbound_service.requests,
        "post",
        post_fake,
    )

    transporte = criar_transporte()

    resultado = transporte.enviar_texto(
        phone_number_id=
            "123456789",

        telefone_destino=
            "+55 (81) 99999-9999",

        texto=
            "Agendamento confirmado.",
    )

    assert captura["url"] == (
        "https://graph.example.test/"
        "vTEST/"
        "123456789/"
        "messages"
    )

    assert captura[
        "headers"
    ][
        "Authorization"
    ] == "Bearer token-de-teste"

    assert captura[
        "headers"
    ][
        "Content-Type"
    ] == "application/json"

    assert captura["timeout"] == 20

    assert captura["json"] == {
        "messaging_product":
            "whatsapp",

        "recipient_type":
            "individual",

        "to":
            "5581999999999",

        "type":
            "text",

        "text": {
            "body":
                "Agendamento confirmado.",
        },
    }

    assert resultado == {
        "enviado":
            True,

        "provider":
            "meta",

        "provider_message_id":
            "wamid.saida.001",
    }


def test_meta_sem_access_token_retorna_503():
    with pytest.raises(
        HTTPException
    ) as erro:
        criar_transporte(
            access_token=None
        )

    assert erro.value.status_code == 503


def test_meta_sem_versao_retorna_503():
    with pytest.raises(
        HTTPException
    ) as erro:
        criar_transporte(
            graph_api_version=None
        )

    assert erro.value.status_code == 503


def test_meta_falha_de_rede_retorna_502(
    monkeypatch,
):
    def post_fake(
        *args,
        **kwargs,
    ):
        raise requests.RequestException(
            "falha simulada"
        )

    monkeypatch.setattr(
        whatsapp_outbound_service.requests,
        "post",
        post_fake,
    )

    transporte = criar_transporte()

    with pytest.raises(
        HTTPException
    ) as erro:
        transporte.enviar_texto(
            phone_number_id=
                "123456789",

            telefone_destino=
                "5581999999999",

            texto=
                "Teste",
        )

    assert erro.value.status_code == 502


def test_meta_erro_http_retorna_502(
    monkeypatch,
):
    def post_fake(
        *args,
        **kwargs,
    ):
        return RespostaFake(
            status_code=400,
            dados={
                "error": {
                    "message":
                        "erro simulado"
                }
            },
        )

    monkeypatch.setattr(
        whatsapp_outbound_service.requests,
        "post",
        post_fake,
    )

    transporte = criar_transporte()

    with pytest.raises(
        HTTPException
    ) as erro:
        transporte.enviar_texto(
            phone_number_id=
                "123456789",

            telefone_destino=
                "5581999999999",

            texto=
                "Teste",
        )

    assert erro.value.status_code == 502
    assert "HTTP 400" in erro.value.detail


def test_meta_resposta_sem_message_id_retorna_502(
    monkeypatch,
):
    def post_fake(
        *args,
        **kwargs,
    ):
        return RespostaFake(
            dados={
                "messages": [
                    {}
                ]
            }
        )

    monkeypatch.setattr(
        whatsapp_outbound_service.requests,
        "post",
        post_fake,
    )

    transporte = criar_transporte()

    with pytest.raises(
        HTTPException
    ) as erro:
        transporte.enviar_texto(
            phone_number_id=
                "123456789",

            telefone_destino=
                "5581999999999",

            texto=
                "Teste",
        )

    assert erro.value.status_code == 502


def test_meta_json_invalido_retorna_502(
    monkeypatch,
):
    def post_fake(
        *args,
        **kwargs,
    ):
        return RespostaFake(
            json_invalido=True
        )

    monkeypatch.setattr(
        whatsapp_outbound_service.requests,
        "post",
        post_fake,
    )

    transporte = criar_transporte()

    with pytest.raises(
        HTTPException
    ) as erro:
        transporte.enviar_texto(
            phone_number_id=
                "123456789",

            telefone_destino=
                "5581999999999",

            texto=
                "Teste",
        )

    assert erro.value.status_code == 502
