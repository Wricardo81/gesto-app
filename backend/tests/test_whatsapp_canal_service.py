import pytest

from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import whatsapp_canal_service


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    models.IntegracaoWhatsAppTenant.__table__.create(
        bind=engine,
        checkfirst=True,
    )

    Session = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    db = Session()

    try:
        yield db
    finally:
        db.close()


def test_salva_identidade_tecnica_do_tenant(
    db_session,
):
    integracao = (
        whatsapp_canal_service
        .salvar_integracao_whatsapp(
            db=db_session,
            tenant_slug="clinica-a",
            phone_number_id="100001",
            business_account_id="200001",
            numero_exibicao="5581999999999",
        )
    )

    assert integracao.id is not None
    assert integracao.barbearia_slug == "clinica-a"
    assert integracao.phone_number_id == "100001"
    assert integracao.business_account_id == "200001"
    assert integracao.numero_exibicao == "5581999999999"
    assert integracao.ativo is True


def test_resolve_tenant_pelo_phone_number_id(
    db_session,
):
    (
        whatsapp_canal_service
        .salvar_integracao_whatsapp(
            db=db_session,
            tenant_slug="clinica-a",
            phone_number_id="100001",
        )
    )

    tenant = (
        whatsapp_canal_service
        .resolver_tenant_por_phone_number_id(
            db=db_session,
            phone_number_id="100001",
        )
    )

    assert tenant == "clinica-a"


def test_phone_number_id_desconhecido_nao_resolve_tenant(
    db_session,
):
    with pytest.raises(
        HTTPException
    ) as erro:
        (
            whatsapp_canal_service
            .resolver_tenant_por_phone_number_id(
                db=db_session,
                phone_number_id="nao-existe",
            )
        )

    assert erro.value.status_code == 404


def test_integracao_inativa_nao_recebe_mensagens(
    db_session,
):
    (
        whatsapp_canal_service
        .salvar_integracao_whatsapp(
            db=db_session,
            tenant_slug="clinica-a",
            phone_number_id="100001",
            ativo=False,
        )
    )

    with pytest.raises(
        HTTPException
    ) as erro:
        (
            whatsapp_canal_service
            .resolver_tenant_por_phone_number_id(
                db=db_session,
                phone_number_id="100001",
            )
        )

    assert erro.value.status_code == 409


def test_phone_number_id_nao_pode_pertencer_a_dois_tenants(
    db_session,
):
    (
        whatsapp_canal_service
        .salvar_integracao_whatsapp(
            db=db_session,
            tenant_slug="clinica-a",
            phone_number_id="100001",
        )
    )

    with pytest.raises(
        HTTPException
    ) as erro:
        (
            whatsapp_canal_service
            .salvar_integracao_whatsapp(
                db=db_session,
                tenant_slug="clinica-b",
                phone_number_id="100001",
            )
        )

    assert erro.value.status_code == 409


def test_atualiza_integracao_do_mesmo_tenant(
    db_session,
):
    primeira = (
        whatsapp_canal_service
        .salvar_integracao_whatsapp(
            db=db_session,
            tenant_slug="clinica-a",
            phone_number_id="100001",
            business_account_id="200001",
        )
    )

    primeira_id = primeira.id

    atualizada = (
        whatsapp_canal_service
        .salvar_integracao_whatsapp(
            db=db_session,
            tenant_slug="clinica-a",
            phone_number_id="100002",
            business_account_id="200002",
            numero_exibicao="5581888888888",
        )
    )

    assert atualizada.id == primeira_id
    assert atualizada.phone_number_id == "100002"
    assert atualizada.business_account_id == "200002"

    assert (
        db_session.query(
            models.IntegracaoWhatsAppTenant
        )
        .count()
        == 1
    )
