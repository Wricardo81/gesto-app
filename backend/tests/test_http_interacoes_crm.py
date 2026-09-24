from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from main import app
from routers import cliente_router
from security import criar_token_acesso


@pytest.fixture()
def ambiente_interacoes_crm():
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

    models.InteracaoClienteCRM.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    Session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    def override_get_db():
        db = Session()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[
        cliente_router.get_db
    ] = override_get_db

    client = TestClient(app)

    db = Session()

    try:
        db.add(
            models.Agendamento(
                barbearia_slug="tenant-a",
                cliente_nome="Cliente CRM",
                telefone_cliente="(81) 99999-9999",
                servico="Corte",
                profissional="Ana",
                data=date(2026, 1, 10),
                horario="10:00",
                valor=80,
                status="concluido",
            )
        )

        db.commit()

    finally:
        db.close()

    try:
        yield {
            "client": client,
            "Session": Session,
        }
    finally:
        app.dependency_overrides.pop(
            cliente_router.get_db,
            None,
        )


def token(
    tenant="tenant-a",
    papel="gestor",
    permissoes=None,
):
    if permissoes is None:
        permissoes = ["*"]

    return criar_token_acesso(
        {
            "sub": tenant,
            "tenant_slug": tenant,
            "role": "tenant_admin",
            "papel": papel,
            "permissoes": permissoes,
            "nome": "Usuario CRM",
            "email": "crm@teste.com",
        }
    )


def headers(**kwargs):
    return {
        "Authorization":
            f"Bearer {token(**kwargs)}"
    }


def test_registra_e_lista_interacao_crm(
    ambiente_interacoes_crm,
):
    client = ambiente_interacoes_crm[
        "client"
    ]

    resposta = client.post(
        (
            "/api/tenant-a/admin/clientes/"
            "81999999999/interacoes"
        ),
        headers=headers(),
        json={
            "tipo": "reativacao_risco",
            "cliente_nome": "Cliente CRM",
        },
    )

    assert resposta.status_code == 201

    dados = resposta.json()["interacao"]

    assert dados["telefone_cliente"] == (
        "81999999999"
    )
    assert dados["tipo"] == (
        "reativacao_risco"
    )
    assert dados["canal"] == "whatsapp"
    assert dados["usuario_papel"] == "gestor"
    assert dados["criado_em"]

    historico = client.get(
        (
            "/api/tenant-a/admin/clientes/"
            "81999999999/interacoes"
        ),
        headers=headers(),
    )

    assert historico.status_code == 200

    payload = historico.json()

    assert payload["quantidade"] == 1
    assert (
        payload["interacoes"][0]["tipo"]
        == "reativacao_risco"
    )


def test_recepcao_com_editar_cliente_pode_registrar(
    ambiente_interacoes_crm,
):
    client = ambiente_interacoes_crm[
        "client"
    ]

    resposta = client.post(
        (
            "/api/tenant-a/admin/clientes/"
            "81999999999/interacoes"
        ),
        headers=headers(
            papel="recepcao",
            permissoes=[
                "ver_clientes",
                "editar_cliente",
            ],
        ),
        json={
            "tipo":
                "reativacao_inativo",
            "cliente_nome":
                "Cliente CRM",
        },
    )

    assert resposta.status_code == 201


def test_prestador_sem_permissao_nao_registra(
    ambiente_interacoes_crm,
):
    client = ambiente_interacoes_crm[
        "client"
    ]

    resposta = client.post(
        (
            "/api/tenant-a/admin/clientes/"
            "81999999999/interacoes"
        ),
        headers=headers(
            papel="prestador",
            permissoes=[
                (
                    "ver_clientes_dos_"
                    "proprios_atendimentos"
                )
            ],
        ),
        json={
            "tipo":
                "reativacao_risco",
        },
    )

    assert resposta.status_code == 403


def test_nao_registra_tipo_invalido(
    ambiente_interacoes_crm,
):
    client = ambiente_interacoes_crm[
        "client"
    ]

    resposta = client.post(
        (
            "/api/tenant-a/admin/clientes/"
            "81999999999/interacoes"
        ),
        headers=headers(),
        json={
            "tipo": "qualquer_coisa",
        },
    )

    assert resposta.status_code == 422


def test_nao_registra_cliente_inexistente(
    ambiente_interacoes_crm,
):
    client = ambiente_interacoes_crm[
        "client"
    ]

    resposta = client.post(
        (
            "/api/tenant-a/admin/clientes/"
            "11911111111/interacoes"
        ),
        headers=headers(),
        json={
            "tipo":
                "reativacao_risco",
        },
    )

    assert resposta.status_code == 404


def test_tenant_nao_acessa_interacao_de_outro_tenant(
    ambiente_interacoes_crm,
):
    client = ambiente_interacoes_crm[
        "client"
    ]

    resposta = client.get(
        (
            "/api/tenant-a/admin/clientes/"
            "81999999999/interacoes"
        ),
        headers=headers(
            tenant="tenant-b"
        ),
    )

    assert resposta.status_code == 403



def test_listagem_clientes_expoe_ultima_interacao_crm(
    ambiente_interacoes_crm,
):
    client = ambiente_interacoes_crm[
        "client"
    ]

    primeira = client.post(
        (
            "/api/tenant-a/admin/clientes/"
            "81999999999/interacoes"
        ),
        headers=headers(),
        json={
            "tipo": "reativacao_risco",
            "cliente_nome": "Cliente CRM",
        },
    )

    assert primeira.status_code == 201

    segunda = client.post(
        (
            "/api/tenant-a/admin/clientes/"
            "81999999999/interacoes"
        ),
        headers=headers(),
        json={
            "tipo": "reativacao_inativo",
            "cliente_nome": "Cliente CRM",
        },
    )

    assert segunda.status_code == 201

    resposta = client.get(
        "/api/tenant-a/admin/clientes",
        headers=headers(),
    )

    assert resposta.status_code == 200

    clientes = resposta.json()["clientes"]

    assert len(clientes) == 1

    ultima = clientes[0][
        "ultima_interacao_crm"
    ]

    assert ultima is not None

    assert ultima["tipo"] == (
        "reativacao_inativo"
    )

    assert ultima["canal"] == "whatsapp"

    assert ultima["criado_em"]



def test_usuario_com_ver_clientes_pode_ler_interacoes(
    ambiente_interacoes_crm,
):
    client = ambiente_interacoes_crm[
        "client"
    ]

    resposta = client.get(
        (
            "/api/tenant-a/admin/clientes/"
            "81999999999/interacoes"
        ),
        headers=headers(
            papel="recepcao",
            permissoes=[
                "ver_clientes",
            ],
        ),
    )

    assert resposta.status_code == 200


def test_usuario_sem_permissao_clientes_nao_le_interacoes(
    ambiente_interacoes_crm,
):
    client = ambiente_interacoes_crm[
        "client"
    ]

    resposta = client.get(
        (
            "/api/tenant-a/admin/clientes/"
            "81999999999/interacoes"
        ),
        headers=headers(
            papel="prestador",
            permissoes=[
                (
                    "ver_clientes_dos_"
                    "proprios_atendimentos"
                ),
            ],
        ),
    )

    assert resposta.status_code == 403
