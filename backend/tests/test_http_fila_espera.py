from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from main import app
from routers import fila_espera_router
from security import criar_token_acesso


@pytest.fixture()
def ambiente_http_fila():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    models.FilaEspera.__table__.create(
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
        fila_espera_router.get_db
    ] = override_get_db

    client = TestClient(app)

    try:
        yield {
            "client": client,
            "Session": TestSession,
        }
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def cabecalho(
    *,
    tenant_slug="tenant-a",
    papel="recepcao",
    permissoes=None,
):
    token = criar_token_acesso(
        {
            "sub": tenant_slug,
            "tenant_slug": tenant_slug,
            "email": f"{papel}@teste.com",
            "role": "tenant_admin",
            "papel": papel,
            "perfil_operacional": papel,
            "papel_operacional": papel,
            "permissoes": permissoes or [],
            "nome": f"{papel.title()} Teste",
        }
    )

    return {
        "Authorization": f"Bearer {token}"
    }


def criar_item(
    Session,
    *,
    tenant_slug="tenant-a",
    status="aguardando",
):
    db = Session()

    try:
        item = models.FilaEspera(
            barbearia_slug=tenant_slug,
            cliente_nome="Cliente HTTP",
            telefone_cliente="81999999999",
            servico="Corte",
            data_desejada=date(2026, 9, 22),
            periodo_preferido="qualquer",
            prioridade="normal",
            status=status,
            origem="teste",
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        return item.id

    finally:
        db.close()


def test_leitura_permitida_com_ver_fila(
    ambiente_http_fila,
):
    client = ambiente_http_fila["client"]

    resposta = client.get(
        "/api/tenant-a/admin/fila-espera",
        headers=cabecalho(
            permissoes=["ver_fila_espera"],
        ),
    )

    assert resposta.status_code == 200


def test_leitura_permitida_com_gerenciar_fila(
    ambiente_http_fila,
):
    client = ambiente_http_fila["client"]

    resposta = client.get(
        "/api/tenant-a/admin/fila-espera",
        headers=cabecalho(
            permissoes=["gerenciar_fila_espera"],
        ),
    )

    assert resposta.status_code == 200


def test_somente_leitura_nao_pode_atualizar_status(
    ambiente_http_fila,
):
    client = ambiente_http_fila["client"]
    Session = ambiente_http_fila["Session"]

    item_id = criar_item(Session)

    resposta = client.put(
        f"/api/tenant-a/admin/fila-espera/{item_id}/status",
        headers=cabecalho(
            permissoes=["ver_fila_espera"],
        ),
        json={
            "status": "chamado",
        },
    )

    assert resposta.status_code == 403


def test_gerenciar_pode_atualizar_status(
    ambiente_http_fila,
):
    client = ambiente_http_fila["client"]
    Session = ambiente_http_fila["Session"]

    item_id = criar_item(Session)

    resposta = client.put(
        f"/api/tenant-a/admin/fila-espera/{item_id}/status",
        headers=cabecalho(
            permissoes=["gerenciar_fila_espera"],
        ),
        json={
            "status": "chamado",
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["item"]["status"] == "chamado"


def test_somente_leitura_nao_pode_excluir(
    ambiente_http_fila,
):
    client = ambiente_http_fila["client"]
    Session = ambiente_http_fila["Session"]

    item_id = criar_item(
        Session,
        status="arquivado",
    )

    resposta = client.delete(
        f"/api/tenant-a/admin/fila-espera/{item_id}",
        headers=cabecalho(
            permissoes=["ver_fila_espera"],
        ),
    )

    assert resposta.status_code == 403


def test_gerenciar_pode_excluir_item_arquivado(
    ambiente_http_fila,
):
    client = ambiente_http_fila["client"]
    Session = ambiente_http_fila["Session"]

    item_id = criar_item(
        Session,
        status="arquivado",
    )

    resposta = client.delete(
        f"/api/tenant-a/admin/fila-espera/{item_id}",
        headers=cabecalho(
            permissoes=["gerenciar_fila_espera"],
        ),
    )

    assert resposta.status_code == 200
    assert resposta.json()["item"]["excluido"] is True


def test_bloqueia_cross_tenant(
    ambiente_http_fila,
):
    client = ambiente_http_fila["client"]

    resposta = client.get(
        "/api/tenant-b/admin/fila-espera",
        headers=cabecalho(
            tenant_slug="tenant-a",
            permissoes=["gerenciar_fila_espera"],
        ),
    )

    assert resposta.status_code == 403


def test_sem_permissao_nao_pode_ver_fila(
    ambiente_http_fila,
):
    client = ambiente_http_fila["client"]

    resposta = client.get(
        "/api/tenant-a/admin/fila-espera",
        headers=cabecalho(
            permissoes=[],
        ),
    )

    assert resposta.status_code == 403


def test_somente_leitura_nao_pode_converter_fila(
    ambiente_http_fila,
    monkeypatch,
):
    client = ambiente_http_fila["client"]
    Session = ambiente_http_fila["Session"]

    item_id = criar_item(Session)

    chamado = {
        "executado": False,
    }

    def criar_agendamento_fake(
        db,
        tenant_slug,
        dados,
    ):
        chamado["executado"] = True

        return {
            "id": 9001,
        }

    monkeypatch.setattr(
        fila_espera_router
        .agendamento_service,
        "criar_novo_agendamento",
        criar_agendamento_fake,
    )

    resposta = client.post(
        (
            f"/api/tenant-a/admin/"
            f"fila-espera/{item_id}/agendar"
        ),
        headers=cabecalho(
            permissoes=["ver_fila_espera"],
        ),
        json={
            "data": "2026-09-23",
            "horario": "10:30",
            "profissional": "Ana",
        },
    )

    assert resposta.status_code == 403
    assert chamado["executado"] is False


def test_gerenciar_converte_fila_em_agendamento(
    ambiente_http_fila,
    monkeypatch,
):
    client = ambiente_http_fila["client"]
    Session = ambiente_http_fila["Session"]

    item_id = criar_item(Session)

    recebido = {}

    def criar_agendamento_fake(
        db,
        tenant_slug,
        dados,
    ):
        recebido["tenant_slug"] = tenant_slug
        recebido["cliente_nome"] = (
            dados.cliente_nome
        )
        recebido["telefone_cliente"] = (
            dados.telefone_cliente
        )
        recebido["servico"] = dados.servico
        recebido["profissional"] = (
            dados.profissional
        )
        recebido["data"] = dados.data
        recebido["horario"] = dados.horario
        recebido["valor"] = dados.valor
        recebido["lembrete"] = (
            dados.aceita_lembrete_whatsapp
        )
        recebido["promocoes"] = (
            dados.aceita_promocoes_whatsapp
        )

        return {
            "id": 9001,
            "status": "confirmado",
        }

    monkeypatch.setattr(
        fila_espera_router
        .agendamento_service,
        "criar_novo_agendamento",
        criar_agendamento_fake,
    )

    resposta = client.post(
        (
            f"/api/tenant-a/admin/"
            f"fila-espera/{item_id}/agendar"
        ),
        headers=cabecalho(
            permissoes=[
                "gerenciar_fila_espera"
            ],
        ),
        json={
            "data": "2026-09-23",
            "horario": "10:30",
            "profissional": "Ana",
        },
    )

    assert resposta.status_code == 201

    corpo = resposta.json()

    assert (
        corpo["item_fila"]["status"]
        == "agendado"
    )

    assert (
        corpo["item_fila"]["agendado_em"]
        is not None
    )

    assert corpo["agendamento"]["id"] == 9001

    assert recebido == {
        "tenant_slug": "tenant-a",
        "cliente_nome": "Cliente HTTP",
        "telefone_cliente": "81999999999",
        "servico": "Corte",
        "profissional": "Ana",
        "data": "2026-09-23",
        "horario": "10:30",
        "valor": 0,
        "lembrete": True,
        "promocoes": False,
    }

    db = Session()

    try:
        item = (
            db.query(models.FilaEspera)
            .filter(
                models.FilaEspera.id
                == item_id
            )
            .first()
        )

        assert item is not None
        assert item.status == "agendado"
        assert item.agendado_em is not None

    finally:
        db.close()


def test_nao_converte_item_duas_vezes(
    ambiente_http_fila,
    monkeypatch,
):
    client = ambiente_http_fila["client"]
    Session = ambiente_http_fila["Session"]

    item_id = criar_item(
        Session,
        status="agendado",
    )

    chamado = {
        "executado": False,
    }

    def criar_agendamento_fake(
        db,
        tenant_slug,
        dados,
    ):
        chamado["executado"] = True

        return {
            "id": 9002,
        }

    monkeypatch.setattr(
        fila_espera_router
        .agendamento_service,
        "criar_novo_agendamento",
        criar_agendamento_fake,
    )

    resposta = client.post(
        (
            f"/api/tenant-a/admin/"
            f"fila-espera/{item_id}/agendar"
        ),
        headers=cabecalho(
            permissoes=[
                "gerenciar_fila_espera"
            ],
        ),
        json={
            "data": "2026-09-23",
            "horario": "10:30",
            "profissional": "Ana",
        },
    )

    assert resposta.status_code == 409
    assert chamado["executado"] is False


@pytest.mark.parametrize(
    "status",
    [
        "cancelado",
        "expirado",
        "arquivado",
    ],
)
def test_nao_converte_item_inativo(
    ambiente_http_fila,
    monkeypatch,
    status,
):
    client = ambiente_http_fila["client"]
    Session = ambiente_http_fila["Session"]

    item_id = criar_item(
        Session,
        status=status,
    )

    chamado = {
        "executado": False,
    }

    def criar_agendamento_fake(
        db,
        tenant_slug,
        dados,
    ):
        chamado["executado"] = True

        return {
            "id": 9003,
        }

    monkeypatch.setattr(
        fila_espera_router
        .agendamento_service,
        "criar_novo_agendamento",
        criar_agendamento_fake,
    )

    resposta = client.post(
        (
            f"/api/tenant-a/admin/"
            f"fila-espera/{item_id}/agendar"
        ),
        headers=cabecalho(
            permissoes=[
                "gerenciar_fila_espera"
            ],
        ),
        json={
            "data": "2026-09-23",
            "horario": "10:30",
            "profissional": "Ana",
        },
    )

    assert resposta.status_code == 409
    assert chamado["executado"] is False

