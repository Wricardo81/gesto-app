from __future__ import annotations

import requests

from typing import Protocol

from fastapi import HTTPException


def normalizar_telefone_destino(
    telefone: str,
) -> str:
    digitos = "".join(
        caractere
        for caractere in str(
            telefone or ""
        )
        if caractere.isdigit()
    )

    if len(digitos) < 8:
        raise HTTPException(
            status_code=422,
            detail=(
                "Telefone de destino "
                "invalido."
            ),
        )

    if len(digitos) > 20:
        raise HTTPException(
            status_code=422,
            detail=(
                "Telefone de destino "
                "invalido."
            ),
        )

    return digitos


def validar_texto_saida(
    texto: str,
) -> str:
    texto_normalizado = str(
        texto or ""
    ).strip()

    if not texto_normalizado:
        raise HTTPException(
            status_code=422,
            detail=(
                "Mensagem WhatsApp "
                "nao pode ser vazia."
            ),
        )

    if len(texto_normalizado) > 4096:
        raise HTTPException(
            status_code=422,
            detail=(
                "Mensagem WhatsApp "
                "excede o limite suportado."
            ),
        )

    return texto_normalizado


def formatar_resposta_booking_para_texto(
    resposta_booking: dict,
) -> str:
    if not isinstance(
        resposta_booking,
        dict,
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "Resposta do Booking Assistant "
                "possui formato invalido."
            ),
        )

    mensagem = validar_texto_saida(
        resposta_booking.get(
            "mensagem",
            ""
        )
    )

    opcoes = resposta_booking.get(
        "opcoes",
        []
    )

    if opcoes is None:
        opcoes = []

    if not isinstance(
        opcoes,
        list,
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "Opcoes do Booking Assistant "
                "possuem formato invalido."
            ),
        )

    opcoes_validas = [
        str(opcao).strip()
        for opcao in opcoes
        if str(opcao).strip()
    ]

    if not opcoes_validas:
        return mensagem

    texto = (
        mensagem
        + "\n\n"
        + "\n".join(
            opcoes_validas
        )
    )

    return validar_texto_saida(
        texto
    )


def montar_payload_texto_meta(
    *,
    telefone_destino: str,
    texto: str,
) -> dict:
    telefone = normalizar_telefone_destino(
        telefone_destino
    )

    mensagem = validar_texto_saida(
        texto
    )

    return {
        "messaging_product":
            "whatsapp",

        "recipient_type":
            "individual",

        "to":
            telefone,

        "type":
            "text",

        "text": {
            "body":
                mensagem,
        },
    }


class TransporteWhatsApp(Protocol):
    def enviar_texto(
        self,
        *,
        phone_number_id: str,
        telefone_destino: str,
        texto: str,
    ) -> dict:
        ...


class TransporteMetaWhatsApp:
    def __init__(
        self,
        *,
        access_token: str | None,
        graph_api_version: str | None,
        base_url: str = "https://graph.facebook.com",
        timeout_seconds: int = 20,
    ):
        self.access_token = str(
            access_token or ""
        ).strip()

        self.graph_api_version = str(
            graph_api_version or ""
        ).strip().strip("/")

        self.base_url = str(
            base_url or ""
        ).strip().rstrip("/")

        self.timeout_seconds = timeout_seconds

        if not self.access_token:
            raise HTTPException(
                status_code=503,
                detail=(
                    "WhatsApp access token nao configurado."
                ),
            )

        if not self.graph_api_version:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Versao da Graph API nao configurada."
                ),
            )

        if not self.base_url:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Base URL da Graph API nao configurada."
                ),
            )

        if (
            not isinstance(
                self.timeout_seconds,
                int,
            )
            or self.timeout_seconds <= 0
        ):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Timeout HTTP do WhatsApp invalido."
                ),
            )

    def enviar_texto(
        self,
        *,
        phone_number_id: str,
        telefone_destino: str,
        texto: str,
    ) -> dict:
        origem = str(
            phone_number_id or ""
        ).strip()

        if not origem:
            raise HTTPException(
                status_code=422,
                detail=(
                    "phone_number_id nao informado."
                ),
            )

        payload = montar_payload_texto_meta(
            telefone_destino=telefone_destino,
            texto=texto,
        )

        url = (
            f"{self.base_url}/"
            f"{self.graph_api_version}/"
            f"{origem}/messages"
        )

        headers = {
            "Authorization":
                f"Bearer {self.access_token}",

            "Content-Type":
                "application/json",
        }

        try:
            resposta = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout_seconds,
            )

        except requests.RequestException:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Falha de comunicacao com a API do WhatsApp."
                ),
            )

        if not (
            200 <= resposta.status_code < 300
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "API do WhatsApp retornou "
                    f"HTTP {resposta.status_code}."
                ),
            )

        try:
            dados = resposta.json()

        except ValueError:
            raise HTTPException(
                status_code=502,
                detail=(
                    "API do WhatsApp retornou JSON invalido."
                ),
            )

        mensagens = dados.get(
            "messages",
            []
        )

        if (
            not isinstance(
                mensagens,
                list,
            )
            or not mensagens
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "API do WhatsApp nao retornou identificador da mensagem."
                ),
            )

        primeira = mensagens[0]

        if not isinstance(
            primeira,
            dict,
        ):
            raise HTTPException(
                status_code=502,
                detail=(
                    "Resposta da API do WhatsApp possui formato invalido."
                ),
            )

        provider_message_id = str(
            primeira.get(
                "id",
                ""
            )
            or ""
        ).strip()

        if not provider_message_id:
            raise HTTPException(
                status_code=502,
                detail=(
                    "API do WhatsApp nao retornou identificador da mensagem."
                ),
            )

        return {
            "enviado": True,
            "provider": "meta",
            "provider_message_id":
                provider_message_id,
        }


class TransporteFakeWhatsApp:
    def __init__(
        self,
    ):
        self.envios = []

    def enviar_texto(
        self,
        *,
        phone_number_id: str,
        telefone_destino: str,
        texto: str,
    ) -> dict:
        envio = {
            "phone_number_id":
                phone_number_id,

            "telefone_destino":
                telefone_destino,

            "texto":
                texto,
        }

        self.envios.append(
            envio
        )

        numero = len(
            self.envios
        )

        return {
            "enviado": True,
            "provider":
                "fake",

            "provider_message_id":
                f"fake-{numero}",
        }


def enviar_texto_whatsapp(
    *,
    transporte: TransporteWhatsApp,
    phone_number_id: str,
    telefone_destino: str,
    texto: str,
) -> dict:
    origem = str(
        phone_number_id or ""
    ).strip()

    if not origem:
        raise HTTPException(
            status_code=422,
            detail=(
                "phone_number_id "
                "nao informado."
            ),
        )

    telefone = normalizar_telefone_destino(
        telefone_destino
    )

    mensagem = validar_texto_saida(
        texto
    )

    resultado = transporte.enviar_texto(
        phone_number_id=origem,
        telefone_destino=telefone,
        texto=mensagem,
    )

    if not isinstance(
        resultado,
        dict,
    ):
        raise HTTPException(
            status_code=502,
            detail=(
                "Transporte WhatsApp "
                "retornou resposta invalida."
            ),
        )

    return {
        "enviado":
            bool(
                resultado.get(
                    "enviado",
                    False,
                )
            ),

        "provider":
            resultado.get(
                "provider"
            ),

        "provider_message_id":
            resultado.get(
                "provider_message_id"
            ),

        "phone_number_id":
            origem,

        "telefone_destino":
            telefone,
    }


def criar_transporte_whatsapp(
    *,
    modo: str,
    access_token: str | None = None,
    graph_api_version: str | None = None,
    base_url: str = "https://graph.facebook.com",
    timeout_seconds: int = 20,
) -> TransporteWhatsApp:
    modo_normalizado = str(
        modo or ""
    ).strip().lower()

    if modo_normalizado == "fake":
        return TransporteFakeWhatsApp()

    if modo_normalizado == "meta":
        return TransporteMetaWhatsApp(
            access_token=access_token,
            graph_api_version=graph_api_version,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )

    raise HTTPException(
        status_code=503,
        detail=(
            "Modo de transporte WhatsApp "
            "invalido."
        ),
    )
