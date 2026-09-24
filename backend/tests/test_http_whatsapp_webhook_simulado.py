import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from routers import whatsapp_webhook_simulado_router


@pytest.fixture()
def ambiente_webhook_whatsapp():
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

    servico_a = models.ServicoBarbearia(
        barbearia_slug="clinica-a",
        nome="Consulta",
        preco=150,
        duracao=30,
    )

    profissional_a = models.Profissional(
        barbearia_slug="clinica-a",
        nome="Dra Ana",
    )

    servico_b = models.ServicoBarbearia(
        barbearia_slug="clinica-b",
        nome="Avaliacao",
        preco=100,
        duracao=30,
    )

    profissional_b = models.Profissional(
        barbearia_slug="clinica-b",
        nome="Dr Bruno",
    )

    integracao_a = models.IntegracaoWhatsAppTenant(
        barbearia_slug="clinica-a",
        phone_number_id="phone-clinica-a",
        business_account_id="waba-a",
        numero_exibicao="5581111111111",
        ativo=True,
    )

    integracao_b = models.IntegracaoWhatsAppTenant(
        barbearia_slug="clinica-b",
        phone_number_id="phone-clinica-b",
        business_account_id="waba-b",
        numero_exibicao="5581222222222",
        ativo=True,
    )

    db.add_all([
        servico_a,
        profissional_a,
        servico_b,
        profissional_b,
        integracao_a,
        integracao_b,
    ])

    db.flush()

    db.add_all([
        models.ServicoProfissional(
            barbearia_slug="clinica-a",
            servico_id=servico_a.id,
            profissional_id=profissional_a.id,
        ),

        models.ServicoProfissional(
            barbearia_slug="clinica-b",
            servico_id=servico_b.id,
            profissional_id=profissional_b.id,
        ),
    ])

    db.commit()

    app = FastAPI()

    app.include_router(
        whatsapp_webhook_simulado_router.router
    )

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[
        whatsapp_webhook_simulado_router.get_db
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


def test_webhook_resolve_tenant_e_inicia_booking(
    ambiente_webhook_whatsapp,
):
    client = ambiente_webhook_whatsapp[
        "client"
    ]

    resposta = client.post(
        "/api/webhooks/whatsapp/simulado",
        json={
            "message_id": "msg-001",
            "phone_number_id": "phone-clinica-a",
            "telefone_cliente": "(81) 99999-9999",
            "texto": "Oi",
        },
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["recebido"] is True
    assert dados["message_id"] == "msg-001"

    assert (
        dados["tenant_slug"]
        == "clinica-a"
    )

    assert (
        dados["telefone_cliente"]
        == "81999999999"
    )

    assert (
        dados["resposta"]["etapa"]
        == "aguardando_servico"
    )

    assert dados["resposta"]["opcoes"] == [
        "1. Consulta",
    ]


def test_webhook_mantem_isolamento_entre_tenants(
    ambiente_webhook_whatsapp,
):
    client = ambiente_webhook_whatsapp[
        "client"
    ]

    resposta_a = client.post(
        "/api/webhooks/whatsapp/simulado",
        json={
            "message_id": "msg-a",
            "phone_number_id": "phone-clinica-a",
            "telefone_cliente": "81999999999",
            "texto": "oi",
        },
    )

    resposta_b = client.post(
        "/api/webhooks/whatsapp/simulado",
        json={
            "message_id": "msg-b",
            "phone_number_id": "phone-clinica-b",
            "telefone_cliente": "81999999999",
            "texto": "oi",
        },
    )

    assert resposta_a.status_code == 200
    assert resposta_b.status_code == 200

    dados_a = resposta_a.json()
    dados_b = resposta_b.json()

    assert (
        dados_a["tenant_slug"]
        == "clinica-a"
    )

    assert (
        dados_b["tenant_slug"]
        == "clinica-b"
    )

    assert dados_a["resposta"][
        "opcoes"
    ] == [
        "1. Consulta",
    ]

    assert dados_b["resposta"][
        "opcoes"
    ] == [
        "1. Avaliacao",
    ]

    assert (
        dados_a["resposta"]["sessao"]["id"]
        != dados_b["resposta"]["sessao"]["id"]
    )


def test_webhook_phone_number_id_desconhecido_retorna_404(
    ambiente_webhook_whatsapp,
):
    client = ambiente_webhook_whatsapp[
        "client"
    ]

    resposta = client.post(
        "/api/webhooks/whatsapp/simulado",
        json={
            "message_id": "msg-404",
            "phone_number_id": "phone-desconhecido",
            "telefone_cliente": "81999999999",
            "texto": "oi",
        },
    )

    assert resposta.status_code == 404


def test_webhook_integracao_inativa_retorna_409(
    ambiente_webhook_whatsapp,
):
    db = ambiente_webhook_whatsapp[
        "db"
    ]

    client = ambiente_webhook_whatsapp[
        "client"
    ]

    integracao = (
        db.query(
            models.IntegracaoWhatsAppTenant
        )
        .filter(
            models.IntegracaoWhatsAppTenant.phone_number_id
            == "phone-clinica-a"
        )
        .first()
    )

    integracao.ativo = False

    db.commit()

    resposta = client.post(
        "/api/webhooks/whatsapp/simulado",
        json={
            "message_id": "msg-inativa",
            "phone_number_id": "phone-clinica-a",
            "telefone_cliente": "81999999999",
            "texto": "oi",
        },
    )

    assert resposta.status_code == 409


def test_webhook_payload_invalido_retorna_422(
    ambiente_webhook_whatsapp,
):
    client = ambiente_webhook_whatsapp[
        "client"
    ]

    resposta = client.post(
        "/api/webhooks/whatsapp/simulado",
        json={
            "message_id": "",
            "phone_number_id": "",
            "telefone_cliente": "1",
            "texto": "",
        },
    )

    assert resposta.status_code == 422


def test_webhook_segunda_mensagem_continua_mesma_sessao(
    ambiente_webhook_whatsapp,
):
    client = ambiente_webhook_whatsapp[
        "client"
    ]

    primeira = client.post(
        "/api/webhooks/whatsapp/simulado",
        json={
            "message_id": "msg-001",
            "phone_number_id": "phone-clinica-a",
            "telefone_cliente": "81999999999",
            "texto": "oi",
        },
    )

    segunda = client.post(
        "/api/webhooks/whatsapp/simulado",
        json={
            "message_id": "msg-002",
            "phone_number_id": "phone-clinica-a",
            "telefone_cliente": "81999999999",
            "texto": "Consulta",
        },
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 200

    dados_primeira = primeira.json()
    dados_segunda = segunda.json()

    assert (
        dados_primeira["resposta"]["sessao"]["id"]
        == dados_segunda["resposta"]["sessao"]["id"]
    )

    assert (
        dados_segunda["resposta"]["etapa"]
        == "aguardando_profissional"
    )

    assert (
        dados_segunda["resposta"]["sessao"]["servico"]
        == "Consulta"
    )

    assert dados_segunda[
        "resposta"
    ]["opcoes"] == [
        "1. Dra Ana",
    ]
