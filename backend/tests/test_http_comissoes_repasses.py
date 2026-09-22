from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from main import app
from routers import comissao_router
from security import criar_token_acesso


@pytest.fixture()
def ambiente_http():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    models.Agendamento.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    models.ComissaoAtendimento.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    models.RepasseProfissional.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    TestSession = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    def override_get_db():
        db = TestSession()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[
        comissao_router.get_db
    ] = override_get_db

    cliente = TestClient(app)

    try:
        yield {
            "client": cliente,
            "Session": TestSession,
        }
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def cabecalho_tenant(
    tenant_slug: str = "tenant-teste",
) -> dict:
    token = criar_token_acesso(
        {
            "sub": tenant_slug,
            "tenant_slug": tenant_slug,
            "email": "gestor@teste.com",
            "role": "tenant_admin",
            "papel": "gestor",
            "perfil_operacional": "gestor",
            "papel_operacional": "gestor",
            "permissoes": ["*"],
            "nome": "Gestor Teste",
        }
    )

    return {
        "Authorization": f"Bearer {token}"
    }


def criar_comissao_pendente(Session):
    db = Session()

    try:
        agendamento = models.Agendamento(
            id=2001,
            barbearia_slug="tenant-teste",
            cliente_nome="Cliente HTTP",
            servico="Software",
            horario="10:00",
            data=date(2026, 9, 22),
            valor=1000.0,
            profissional="Ricardo",
            status="concluido",
        )

        comissao = models.ComissaoAtendimento(
            id=3001,
            barbearia_slug="tenant-teste",
            agendamento_id=2001,
            profissional_nome="Ricardo",
            servico="Software",
            valor_atendimento=1000.0,
            comissao_tipo="percentual",
            comissao_regra_valor=40.0,
            valor_comissao=400.0,
            status="pendente",
        )

        db.add(agendamento)
        db.add(comissao)
        db.commit()

    finally:
        db.close()


def test_rota_financeira_exige_autenticacao(
    ambiente_http,
):
    client = ambiente_http["client"]

    resposta = client.get(
        "/api/tenant-teste/comissoes/pendentes"
    )

    assert resposta.status_code in {401, 403}


def test_get_comissoes_pendentes_http(
    ambiente_http,
):
    client = ambiente_http["client"]
    Session = ambiente_http["Session"]

    criar_comissao_pendente(Session)

    resposta = client.get(
        "/api/tenant-teste/comissoes/pendentes",
        headers=cabecalho_tenant(),
    )

    assert resposta.status_code == 200

    dados = resposta.json()

    assert dados["tenant_slug"] == "tenant-teste"
    assert dados["quantidade"] == 1
    assert dados["total_pendente"] == 400.0

    assert dados["comissoes"][0]["id"] == 3001
    assert (
        dados["comissoes"][0]["agendamento_id"]
        == 2001
    )


def test_bloqueia_acesso_cross_tenant_http(
    ambiente_http,
):
    client = ambiente_http["client"]

    resposta = client.get(
        "/api/outro-tenant/comissoes/pendentes",
        headers=cabecalho_tenant(
            "tenant-teste"
        ),
    )

    assert resposta.status_code == 403


def test_fluxo_http_repasse_e_historico(
    ambiente_http,
):
    client = ambiente_http["client"]
    Session = ambiente_http["Session"]

    criar_comissao_pendente(Session)

    headers = cabecalho_tenant()

    resposta_repasse = client.post(
        "/api/tenant-teste/repasses",
        headers=headers,
        json={
            "comissoes_ids": [3001],
            "observacao": "Pagamento HTTP",
        },
    )

    assert resposta_repasse.status_code == 200

    repasse = resposta_repasse.json()

    assert repasse["valor"] == 400.0
    assert repasse["profissional_nome"] == "Ricardo"
    assert repasse["comissoes_ids"] == [3001]
    assert repasse["quantidade_comissoes"] == 1

    repasse_id = repasse["id"]

    resposta_pendentes = client.get(
        "/api/tenant-teste/comissoes/pendentes",
        headers=headers,
    )

    assert resposta_pendentes.status_code == 200
    assert resposta_pendentes.json()["quantidade"] == 0
    assert (
        resposta_pendentes.json()["total_pendente"]
        == 0
    )

    resposta_historico = client.get(
        "/api/tenant-teste/repasses",
        headers=headers,
    )

    assert resposta_historico.status_code == 200

    historico = resposta_historico.json()

    assert historico["quantidade"] == 1
    assert historico["total_pago"] == 400.0

    resposta_detalhe = client.get(
        f"/api/tenant-teste/repasses/{repasse_id}",
        headers=headers,
    )

    assert resposta_detalhe.status_code == 200

    detalhe = resposta_detalhe.json()

    assert detalhe["id"] == repasse_id
    assert detalhe["valor"] == 400.0
    assert detalhe["quantidade_comissoes"] == 1
    assert detalhe["comissoes"][0]["id"] == 3001
    assert detalhe["comissoes"][0]["status"] == "pago"


def test_http_bloqueia_pagamento_duplicado(
    ambiente_http,
):
    client = ambiente_http["client"]
    Session = ambiente_http["Session"]

    criar_comissao_pendente(Session)

    headers = cabecalho_tenant()

    payload = {
        "comissoes_ids": [3001],
    }

    primeira = client.post(
        "/api/tenant-teste/repasses",
        headers=headers,
        json=payload,
    )

    assert primeira.status_code == 200

    segunda = client.post(
        "/api/tenant-teste/repasses",
        headers=headers,
        json=payload,
    )

    assert segunda.status_code == 422

    detalhe = segunda.json()["detail"]

    assert (
        "ja foram pagas"
        in detalhe
        or "outro repasse"
        in detalhe
    )


def test_repasse_inexistente_retorna_404(
    ambiente_http,
):
    client = ambiente_http["client"]

    resposta = client.get(
        "/api/tenant-teste/repasses/999999",
        headers=cabecalho_tenant(),
    )

    assert resposta.status_code == 404
    assert (
        resposta.json()["detail"]
        == "Repasse nao encontrado."
    )
