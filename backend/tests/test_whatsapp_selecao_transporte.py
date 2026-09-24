import pytest

from fastapi import HTTPException

from routers import whatsapp_webhook_router

from services import whatsapp_outbound_service


def test_factory_fake_retorna_transporte_fake():
    transporte = (
        whatsapp_outbound_service
        .criar_transporte_whatsapp(
            modo="fake"
        )
    )

    assert isinstance(
        transporte,
        whatsapp_outbound_service
        .TransporteFakeWhatsApp,
    )


def test_factory_normaliza_modo_meta():
    transporte = (
        whatsapp_outbound_service
        .criar_transporte_whatsapp(
            modo=" META ",
            access_token="token-teste",
            graph_api_version="vTEST",
            base_url=
                "https://graph.example.test",
            timeout_seconds=20,
        )
    )

    assert isinstance(
        transporte,
        whatsapp_outbound_service
        .TransporteMetaWhatsApp,
    )

    assert (
        transporte.access_token
        == "token-teste"
    )

    assert (
        transporte.graph_api_version
        == "vTEST"
    )


def test_factory_modo_invalido_retorna_503():
    with pytest.raises(
        HTTPException
    ) as erro:
        (
            whatsapp_outbound_service
            .criar_transporte_whatsapp(
                modo="desconhecido"
            )
        )

    assert (
        erro.value.status_code
        == 503
    )


def test_factory_meta_sem_token_retorna_503():
    with pytest.raises(
        HTTPException
    ) as erro:
        (
            whatsapp_outbound_service
            .criar_transporte_whatsapp(
                modo="meta",
                access_token=None,
                graph_api_version="vTEST",
            )
        )

    assert (
        erro.value.status_code
        == 503
    )


def test_dependencia_router_default_continua_fake(
    monkeypatch,
):
    monkeypatch.setattr(
        whatsapp_webhook_router.settings,
        "whatsapp_transport_mode",
        "fake",
    )

    transporte = (
        whatsapp_webhook_router
        .get_transporte_whatsapp()
    )

    assert isinstance(
        transporte,
        whatsapp_outbound_service
        .TransporteFakeWhatsApp,
    )


def test_dependencia_router_meta_cria_transporte_sem_enviar(
    monkeypatch,
):
    monkeypatch.setattr(
        whatsapp_webhook_router.settings,
        "whatsapp_transport_mode",
        "meta",
    )

    monkeypatch.setattr(
        whatsapp_webhook_router.settings,
        "whatsapp_access_token",
        "token-ficticio",
    )

    monkeypatch.setattr(
        whatsapp_webhook_router.settings,
        "whatsapp_graph_api_version",
        "vTEST",
    )

    monkeypatch.setattr(
        whatsapp_webhook_router.settings,
        "whatsapp_graph_api_base_url",
        "https://graph.example.test",
    )

    monkeypatch.setattr(
        whatsapp_webhook_router.settings,
        "whatsapp_http_timeout_seconds",
        20,
    )

    transporte = (
        whatsapp_webhook_router
        .get_transporte_whatsapp()
    )

    assert isinstance(
        transporte,
        whatsapp_outbound_service
        .TransporteMetaWhatsApp,
    )

    assert (
        transporte.access_token
        == "token-ficticio"
    )
