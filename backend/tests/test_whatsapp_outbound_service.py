import pytest

from fastapi import HTTPException

from services import whatsapp_outbound_service


def test_normaliza_telefone_destino():
    telefone = (
        whatsapp_outbound_service
        .normalizar_telefone_destino(
            "+55 (81) 99999-9999"
        )
    )

    assert telefone == "5581999999999"


def test_rejeita_telefone_invalido():
    with pytest.raises(
        HTTPException
    ) as erro:
        (
            whatsapp_outbound_service
            .normalizar_telefone_destino(
                "123"
            )
        )

    assert (
        erro.value.status_code
        == 422
    )


def test_rejeita_texto_vazio():
    with pytest.raises(
        HTTPException
    ) as erro:
        (
            whatsapp_outbound_service
            .validar_texto_saida(
                "   "
            )
        )

    assert (
        erro.value.status_code
        == 422
    )


def test_monta_payload_meta_de_texto():
    payload = (
        whatsapp_outbound_service
        .montar_payload_texto_meta(
            telefone_destino=
                "+55 81 99999-9999",

            texto=
                "Seu agendamento foi confirmado.",
        )
    )

    assert payload == {
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
                "Seu agendamento foi confirmado.",
        },
    }


def test_transporte_fake_registra_envio():
    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    resultado = (
        whatsapp_outbound_service
        .enviar_texto_whatsapp(
            transporte=transporte,
            phone_number_id=
                "phone-clinica-a",

            telefone_destino=
                "(81) 99999-9999",

            texto=
                "Escolha um servico.",
        )
    )

    assert resultado[
        "enviado"
    ] is True

    assert (
        resultado[
            "provider"
        ]
        == "fake"
    )

    assert (
        resultado[
            "provider_message_id"
        ]
        == "fake-1"
    )

    assert len(
        transporte.envios
    ) == 1

    envio = transporte.envios[0]

    assert (
        envio[
            "phone_number_id"
        ]
        == "phone-clinica-a"
    )

    assert (
        envio[
            "telefone_destino"
        ]
        == "81999999999"
    )

    assert (
        envio[
            "texto"
        ]
        == "Escolha um servico."
    )


def test_dois_envios_geram_ids_distintos():
    transporte = (
        whatsapp_outbound_service
        .TransporteFakeWhatsApp()
    )

    primeiro = (
        whatsapp_outbound_service
        .enviar_texto_whatsapp(
            transporte=transporte,
            phone_number_id=
                "phone-clinica-a",

            telefone_destino=
                "81999999999",

            texto=
                "Mensagem 1",
        )
    )

    segundo = (
        whatsapp_outbound_service
        .enviar_texto_whatsapp(
            transporte=transporte,
            phone_number_id=
                "phone-clinica-a",

            telefone_destino=
                "81999999999",

            texto=
                "Mensagem 2",
        )
    )

    assert (
        primeiro[
            "provider_message_id"
        ]
        == "fake-1"
    )

    assert (
        segundo[
            "provider_message_id"
        ]
        == "fake-2"
    )

    assert len(
        transporte.envios
    ) == 2
