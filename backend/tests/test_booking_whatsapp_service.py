from datetime import UTC, date, datetime, timedelta

import pytest

from fastapi import HTTPException

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models

from services import booking_whatsapp_service


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    models.SessaoBookingWhatsApp.__table__.create(
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


def test_cria_sessao_booking_normalizando_telefone(
    db_session,
):
    sessao = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente="(81) 99999-9999",
        )
    )

    assert sessao.id is not None
    assert sessao.barbearia_slug == "tenant-a"
    assert sessao.telefone_cliente == "81999999999"
    assert sessao.status == "ativa"
    assert sessao.etapa == "inicio"
    assert sessao.canal == "whatsapp"
    assert sessao.expira_em is not None


def test_reutiliza_mesma_sessao_enquanto_ativa(
    db_session,
):
    primeira = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
        )
    )

    segunda = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente="81 99999-9999",
        )
    )

    assert primeira.id == segunda.id

    total = (
        db_session.query(
            models.SessaoBookingWhatsApp
        )
        .count()
    )

    assert total == 1


def test_criacao_sem_sessao_adquire_lock_e_reconsulta(
    db_session,
    monkeypatch,
):
    eventos = []

    lock_original = (
        booking_whatsapp_service
        .bloquear_sessao_booking_cliente
    )

    busca_original = (
        booking_whatsapp_service
        .buscar_sessao_ativa_sem_expirar
    )

    def lock_spy(
        db,
        *,
        tenant_slug,
        telefone_cliente,
    ):
        eventos.append(
            "lock"
        )

        return lock_original(
            db=db,
            tenant_slug=tenant_slug,
            telefone_cliente=
                telefone_cliente,
        )

    def busca_spy(
        db,
        *,
        tenant_slug,
        telefone_cliente,
    ):
        eventos.append(
            "reconsulta"
        )

        return busca_original(
            db=db,
            tenant_slug=tenant_slug,
            telefone_cliente=
                telefone_cliente,
        )

    monkeypatch.setattr(
        booking_whatsapp_service,
        "bloquear_sessao_booking_cliente",
        lock_spy,
    )

    monkeypatch.setattr(
        booking_whatsapp_service,
        "buscar_sessao_ativa_sem_expirar",
        busca_spy,
    )

    sessao = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente=
                "81999999999",
        )
    )

    assert (
        sessao.status
        == "ativa"
    )

    assert eventos == [
        "lock",
        "reconsulta",
    ]


def test_reconsulta_apos_lock_reutiliza_sessao_concorrente(
    db_session,
    monkeypatch,
):
    agora = (
        booking_whatsapp_service
        .agora_utc_naive()
    )

    concorrente = (
        models.SessaoBookingWhatsApp(
            barbearia_slug=
                "tenant-a",
            telefone_cliente=
                "81999999999",
            status=
                "ativa",
            etapa=
                "aguardando_servico",
            canal=
                "whatsapp",
            criado_em=
                agora,
            atualizado_em=
                agora,
            expira_em=(
                agora
                + timedelta(
                    minutes=30
                )
            ),
        )
    )

    chamadas = {
        "obter":
            0,
    }

    def obter_primeira_vez_none(
        *args,
        **kwargs,
    ):
        chamadas["obter"] += 1

        return None

    def lock_simulado(
        db,
        *,
        tenant_slug,
        telefone_cliente,
    ):
        db.add(
            concorrente
        )

        db.commit()

    monkeypatch.setattr(
        booking_whatsapp_service,
        "obter_sessao_ativa",
        obter_primeira_vez_none,
    )

    monkeypatch.setattr(
        booking_whatsapp_service,
        "bloquear_sessao_booking_cliente",
        lock_simulado,
    )

    sessao = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente=
                "81999999999",
        )
    )

    assert (
        sessao.id
        == concorrente.id
    )

    assert (
        sessao.etapa
        == "aguardando_servico"
    )

    assert (
        db_session.query(
            models.SessaoBookingWhatsApp
        )
        .filter(
            models.SessaoBookingWhatsApp
            .barbearia_slug
            == "tenant-a",

            models.SessaoBookingWhatsApp
            .telefone_cliente
            == "81999999999",

            models.SessaoBookingWhatsApp
            .status
            == "ativa",
        )
        .count()
        == 1
    )


def test_sessao_expirada_e_substituida_por_nova(
    db_session,
):
    antiga = models.SessaoBookingWhatsApp(
        barbearia_slug="tenant-a",
        telefone_cliente="81999999999",
        status="ativa",
        etapa="aguardando_servico",
        canal="whatsapp",
        expira_em=(
            datetime.now(
                UTC
            ).replace(
                tzinfo=None
            )
            - timedelta(minutes=1)
        ),
    )

    db_session.add(antiga)
    db_session.commit()
    db_session.refresh(antiga)

    id_antigo = antiga.id

    nova = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
        )
    )

    db_session.refresh(antiga)

    assert antiga.id == id_antigo
    assert antiga.status == "expirada"

    assert nova.id != id_antigo
    assert nova.status == "ativa"
    assert nova.etapa == "inicio"


def test_sessoes_sao_isoladas_por_tenant(
    db_session,
):
    tenant_a = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
        )
    )

    tenant_b = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-b",
            telefone_cliente="81999999999",
        )
    )

    assert tenant_a.id != tenant_b.id

    assert (
        tenant_a.barbearia_slug
        == "tenant-a"
    )

    assert (
        tenant_b.barbearia_slug
        == "tenant-b"
    )


def test_atualiza_estado_parcial_e_renova_expiracao(
    db_session,
):
    sessao = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
        )
    )

    expiracao_anterior = sessao.expira_em

    atualizada = (
        booking_whatsapp_service
        .atualizar_sessao(
            db=db_session,
            sessao=sessao,
            etapa="aguardando_horario",
            cliente_nome="Ricardo",
            servico="Corte",
            profissional="Ana",
            data_agendamento=date(
                2026,
                10,
                10,
            ),
            horario="10:30",
        )
    )

    assert (
        atualizada.etapa
        == "aguardando_horario"
    )

    assert atualizada.cliente_nome == "Ricardo"
    assert atualizada.servico == "Corte"
    assert atualizada.profissional == "Ana"
    assert atualizada.data == date(2026, 10, 10)
    assert atualizada.horario == "10:30"

    assert (
        atualizada.expira_em
        >= expiracao_anterior
    )


def test_concluir_sessao_impede_reuso_da_anterior(
    db_session,
):
    sessao = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
        )
    )

    concluida = (
        booking_whatsapp_service
        .concluir_sessao(
            db=db_session,
            sessao=sessao,
        )
    )

    assert concluida.status == "concluida"
    assert concluida.etapa == "concluido"

    nova = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
        )
    )

    assert nova.id != concluida.id
    assert nova.status == "ativa"
    assert nova.etapa == "inicio"


def test_rejeita_etapa_invalida(
    db_session,
):
    sessao = (
        booking_whatsapp_service
        .criar_ou_obter_sessao(
            db=db_session,
            tenant_slug="tenant-a",
            telefone_cliente="81999999999",
        )
    )

    with pytest.raises(
        HTTPException
    ) as erro:
        (
            booking_whatsapp_service
            .atualizar_sessao(
                db=db_session,
                sessao=sessao,
                etapa="qualquer_coisa",
            )
        )

    assert erro.value.status_code == 422
