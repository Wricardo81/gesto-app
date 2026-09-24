import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from routers import whatsapp_webhook_simulado_router


@pytest.fixture()
def ambiente_idempotencia():
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
        phone_number_id="phone-a",
        business_account_id="waba-a",
        numero_exibicao="5581111111111",
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


def enviar(
    client,
    *,
    message_id,
    texto,
):
    return client.post(
        "/api/webhooks/whatsapp/simulado",
        json={
            "message_id": message_id,
            "phone_number_id": "phone-a",
            "telefone_cliente": "81999999999",
            "texto": texto,
        },
    )


def test_primeiro_evento_nao_e_idempotente(
    ambiente_idempotencia,
):
    client = ambiente_idempotencia[
        "client"
    ]

    resposta = enviar(
        client,
        message_id="msg-001",
        texto="oi",
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["idempotente"] is False

    assert (
        dados["resposta"]["etapa"]
        == "aguardando_servico"
    )


def test_evento_repetido_devolve_resposta_sem_avancar_sessao(
    ambiente_idempotencia,
):
    db = ambiente_idempotencia["db"]
    client = ambiente_idempotencia[
        "client"
    ]

    primeira = enviar(
        client,
        message_id="msg-001",
        texto="oi",
    )

    segunda = enviar(
        client,
        message_id="msg-001",
        texto="oi",
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 200

    dados_primeira = primeira.json()
    dados_segunda = segunda.json()

    assert (
        dados_primeira["idempotente"]
        is False
    )

    assert (
        dados_segunda["idempotente"]
        is True
    )

    assert (
        dados_primeira["resposta"]["sessao"]["id"]
        == dados_segunda["resposta"]["sessao"]["id"]
    )

    sessoes = (
        db.query(
            models.SessaoBookingWhatsApp
        )
        .count()
    )

    assert sessoes == 1


def test_mesmo_message_id_com_texto_diferente_nao_reprocessa(
    ambiente_idempotencia,
):
    client = ambiente_idempotencia[
        "client"
    ]

    primeira = enviar(
        client,
        message_id="msg-001",
        texto="oi",
    )

    repetida = enviar(
        client,
        message_id="msg-001",
        texto="Consulta",
    )

    assert primeira.status_code == 200
    assert repetida.status_code == 200

    dados = repetida.json()

    assert dados["idempotente"] is True

    assert (
        dados["resposta"]["etapa"]
        == "aguardando_servico"
    )


def test_message_ids_diferentes_avancam_conversa(
    ambiente_idempotencia,
):
    client = ambiente_idempotencia[
        "client"
    ]

    primeira = enviar(
        client,
        message_id="msg-001",
        texto="oi",
    )

    segunda = enviar(
        client,
        message_id="msg-002",
        texto="Consulta",
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 200

    dados = segunda.json()

    assert dados["idempotente"] is False

    assert (
        dados["resposta"]["etapa"]
        == "aguardando_profissional"
    )


def test_evento_processado_fica_registrado_uma_unica_vez(
    ambiente_idempotencia,
):
    db = ambiente_idempotencia["db"]
    client = ambiente_idempotencia[
        "client"
    ]

    enviar(
        client,
        message_id="msg-001",
        texto="oi",
    )

    enviar(
        client,
        message_id="msg-001",
        texto="oi",
    )

    eventos = (
        db.query(
            models.EventoWhatsAppRecebido
        )
        .all()
    )

    assert len(eventos) == 1

    evento = eventos[0]

    assert evento.provedor == "simulado"
    assert evento.message_id == "msg-001"
    assert evento.status == "processado"
    assert evento.resposta_json
    assert evento.processado_em is not None
