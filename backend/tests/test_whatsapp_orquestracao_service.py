import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import whatsapp_orquestracao_service
from services import whatsapp_outbound_service


@pytest.fixture()
def ambiente_orquestracao():
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

    try:
        yield {
            "db":
                db,

            "transporte":
                transporte,
        }

    finally:
        db.close()


def payload_meta(
    *,
    message_id="wamid.001",
    texto="Oi",
):
    return {
        "object":
            "whatsapp_business_account",

        "entry": [
            {
                "id": "waba-001",

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


def processar(
    ambiente,
    *,
    message_id,
    texto,
):
    return (
        whatsapp_orquestracao_service
        .processar_payload_meta_e_responder(
            db=ambiente[
                "db"
            ],

            payload=payload_meta(
                message_id=message_id,
                texto=texto,
            ),

            transporte=ambiente[
                "transporte"
            ],
        )
    )


def test_formatador_une_mensagem_e_opcoes():
    texto = (
        whatsapp_outbound_service
        .formatar_resposta_booking_para_texto(
            {
                "mensagem":
                    "Escolha um servico.",

                "opcoes": [
                    "1. Corte",
                    "2. Barba",
                ],
            }
        )
    )

    assert texto == (
        "Escolha um servico."
        "\n\n"
        "1. Corte"
        "\n"
        "2. Barba"
    )


def test_formatador_sem_opcoes_retorna_so_mensagem():
    texto = (
        whatsapp_outbound_service
        .formatar_resposta_booking_para_texto(
            {
                "mensagem":
                    "Agendamento confirmado com sucesso.",

                "opcoes": [],
            }
        )
    )

    assert texto == (
        "Agendamento confirmado com sucesso."
    )


def test_primeira_mensagem_gera_um_outbound(
    ambiente_orquestracao,
):
    resultado = processar(
        ambiente_orquestracao,
        message_id="wamid.001",
        texto="Oi",
    )

    transporte = ambiente_orquestracao[
        "transporte"
    ]

    assert resultado[
        "processados"
    ] == 1

    assert resultado[
        "total_envios"
    ] == 1

    assert len(
        transporte.envios
    ) == 1

    envio = transporte.envios[0]

    assert (
        envio[
            "phone_number_id"
        ]
        == "123456789"
    )

    assert (
        envio[
            "telefone_destino"
        ]
        == "5581988888888"
    )

    assert (
        "Escolha um servico"
        in envio[
            "texto"
        ]
    )

    assert (
        "1. Consulta"
        in envio[
            "texto"
        ]
    )


def test_segunda_mensagem_avanca_e_gera_novo_outbound(
    ambiente_orquestracao,
):
    processar(
        ambiente_orquestracao,
        message_id="wamid.001",
        texto="Oi",
    )

    resultado = processar(
        ambiente_orquestracao,
        message_id="wamid.002",
        texto="Consulta",
    )

    transporte = ambiente_orquestracao[
        "transporte"
    ]

    assert resultado[
        "total_envios"
    ] == 1

    assert len(
        transporte.envios
    ) == 2

    segundo = transporte.envios[1]

    assert (
        "profissional"
        in segundo[
            "texto"
        ].lower()
    )

    assert (
        "1. Dra Ana"
        in segundo[
            "texto"
        ]
    )


def test_retry_mesma_message_id_nao_gera_segundo_outbound(
    ambiente_orquestracao,
):
    primeira = processar(
        ambiente_orquestracao,
        message_id="wamid.dup",
        texto="Oi",
    )

    segunda = processar(
        ambiente_orquestracao,
        message_id="wamid.dup",
        texto="Oi",
    )

    transporte = ambiente_orquestracao[
        "transporte"
    ]

    assert primeira[
        "total_envios"
    ] == 1

    assert segunda[
        "total_envios"
    ] == 0

    assert len(
        transporte.envios
    ) == 1

    assert (
        segunda[
            "resultados"
        ][0][
            "idempotente"
        ]
        is True
    )


def test_evento_sem_mensagem_nao_gera_outbound(
    ambiente_orquestracao,
):
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

    resultado = (
        whatsapp_orquestracao_service
        .processar_payload_meta_e_responder(
            db=ambiente_orquestracao[
                "db"
            ],

            payload=payload,

            transporte=ambiente_orquestracao[
                "transporte"
            ],
        )
    )

    assert resultado[
        "processados"
    ] == 0

    assert resultado[
        "total_envios"
    ] == 0

    assert (
        ambiente_orquestracao[
            "transporte"
        ].envios
        == []
    )
