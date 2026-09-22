from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from services import comissao_service


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    models.Profissional.__table__.create(
        bind=engine,
        checkfirst=True,
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
        autoflush=True,
        autocommit=False,
    )

    session = TestSession()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def criar_cenario_basico(db):
    profissional = models.Profissional(
        barbearia_slug="tenant-teste",
        nome="Ricardo",
        comissao_tipo="percentual",
        comissao_valor=40.0,
    )

    agendamento = models.Agendamento(
        id=1001,
        barbearia_slug="tenant-teste",
        cliente_nome="Cliente Teste",
        servico="Desenvolvimento de software",
        horario="10:00",
        data=date(2026, 9, 22),
        valor=1000.0,
        profissional="Ricardo",
        status="concluido",
    )

    db.add(profissional)
    db.add(agendamento)
    db.commit()

    return profissional, agendamento


def test_gera_snapshot_de_comissao(db):
    _, agendamento = criar_cenario_basico(db)

    comissao = (
        comissao_service
        .gerar_comissao_atendimento_se_necessario(
            db,
            agendamento,
        )
    )

    db.commit()
    db.refresh(comissao)

    assert comissao.barbearia_slug == "tenant-teste"
    assert comissao.agendamento_id == 1001
    assert comissao.profissional_nome == "Ricardo"
    assert comissao.valor_atendimento == 1000.0
    assert comissao.comissao_tipo == "percentual"
    assert comissao.comissao_regra_valor == 40.0
    assert comissao.valor_comissao == 400.0
    assert comissao.status == "pendente"
    assert comissao.repasse_id is None


def test_nao_duplica_comissao_do_mesmo_atendimento(db):
    _, agendamento = criar_cenario_basico(db)

    primeira = (
        comissao_service
        .gerar_comissao_atendimento_se_necessario(
            db,
            agendamento,
        )
    )

    db.commit()

    segunda = (
        comissao_service
        .gerar_comissao_atendimento_se_necessario(
            db,
            agendamento,
        )
    )

    db.commit()

    quantidade = (
        db.query(models.ComissaoAtendimento)
        .filter(
            models.ComissaoAtendimento.barbearia_slug
            == "tenant-teste",
            models.ComissaoAtendimento.agendamento_id
            == 1001,
        )
        .count()
    )

    assert primeira.id == segunda.id
    assert quantidade == 1


def test_lista_comissao_pendente_e_total(db):
    _, agendamento = criar_cenario_basico(db)

    comissao_service.gerar_comissao_atendimento_se_necessario(
        db,
        agendamento,
    )

    db.commit()

    resultado = (
        comissao_service
        .listar_comissoes_pendentes(
            db,
            "tenant-teste",
        )
    )

    assert resultado["quantidade"] == 1
    assert resultado["total_pendente"] == 400.0

    item = resultado["comissoes"][0]

    assert item["agendamento_id"] == 1001
    assert item["profissional_nome"] == "Ricardo"
    assert item["valor_comissao"] == 400.0
    assert item["status"] == "pendente"


def test_registra_repasse_e_marca_comissao_como_paga(db):
    _, agendamento = criar_cenario_basico(db)

    comissao = (
        comissao_service
        .gerar_comissao_atendimento_se_necessario(
            db,
            agendamento,
        )
    )

    db.commit()
    db.refresh(comissao)

    dados = comissao_service.NovoRepasseProfissional(
        comissoes_ids=[comissao.id],
        observacao="Pagamento teste",
    )

    resultado = (
        comissao_service
        .registrar_repasse_profissional(
            db=db,
            tenant_slug="tenant-teste",
            dados=dados,
            registrado_por="pytest",
        )
    )

    db.refresh(comissao)

    assert resultado["valor"] == 400.0
    assert resultado["profissional_nome"] == "Ricardo"
    assert resultado["quantidade_comissoes"] == 1
    assert resultado["comissoes_ids"] == [comissao.id]

    assert comissao.status == "pago"
    assert comissao.repasse_id == resultado["id"]
    assert comissao.pago_em is not None


def test_bloqueia_pagamento_duplicado(db):
    _, agendamento = criar_cenario_basico(db)

    comissao = (
        comissao_service
        .gerar_comissao_atendimento_se_necessario(
            db,
            agendamento,
        )
    )

    db.commit()
    db.refresh(comissao)

    dados = comissao_service.NovoRepasseProfissional(
        comissoes_ids=[comissao.id]
    )

    comissao_service.registrar_repasse_profissional(
        db=db,
        tenant_slug="tenant-teste",
        dados=dados,
        registrado_por="pytest",
    )

    with pytest.raises(
        ValueError,
        match="ja foram pagas",
    ):
        comissao_service.registrar_repasse_profissional(
            db=db,
            tenant_slug="tenant-teste",
            dados=dados,
            registrado_por="pytest",
        )


def test_historico_de_repasse_mantem_rastreabilidade(db):
    _, agendamento = criar_cenario_basico(db)

    comissao = (
        comissao_service
        .gerar_comissao_atendimento_se_necessario(
            db,
            agendamento,
        )
    )

    db.commit()
    db.refresh(comissao)

    dados = comissao_service.NovoRepasseProfissional(
        comissoes_ids=[comissao.id],
        observacao="Fechamento financeiro",
    )

    repasse_criado = (
        comissao_service
        .registrar_repasse_profissional(
            db=db,
            tenant_slug="tenant-teste",
            dados=dados,
            registrado_por="pytest",
        )
    )

    historico = (
        comissao_service
        .listar_repasses_profissionais(
            db,
            "tenant-teste",
        )
    )

    detalhe = (
        comissao_service
        .obter_repasse_profissional(
            db,
            "tenant-teste",
            repasse_criado["id"],
        )
    )

    assert historico["quantidade"] == 1
    assert historico["total_pago"] == 400.0

    assert detalhe is not None
    assert detalhe["valor"] == 400.0
    assert detalhe["profissional_nome"] == "Ricardo"
    assert detalhe["quantidade_comissoes"] == 1

    comissao_detalhe = detalhe["comissoes"][0]

    assert comissao_detalhe["agendamento_id"] == 1001
    assert comissao_detalhe["valor_comissao"] == 400.0
    assert comissao_detalhe["status"] == "pago"


def test_tenant_nao_enxerga_dados_de_outro_tenant(db):
    _, agendamento = criar_cenario_basico(db)

    comissao_service.gerar_comissao_atendimento_se_necessario(
        db,
        agendamento,
    )

    db.commit()

    outro_tenant = (
        comissao_service
        .listar_comissoes_pendentes(
            db,
            "outro-tenant",
        )
    )

    assert outro_tenant["quantidade"] == 0
    assert outro_tenant["total_pendente"] == 0
    assert outro_tenant["comissoes"] == []
