from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
from services import fila_espera_service


@pytest.fixture()
def sessao_fila():
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

    db = TestSession()

    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def criar_item(
    session,
    tenant_slug,
    status="aguardando",
):
    item = models.FilaEspera(
        barbearia_slug=tenant_slug,
        cliente_nome="Cliente Teste",
        telefone_cliente="81999999999",
        servico="Corte",
        profissional_preferido=None,
        data_desejada=date.today(),
        periodo_preferido="qualquer",
        prioridade="normal",
        status=status,
        observacao=None,
        origem="teste",
    )

    session.add(item)
    session.commit()
    session.refresh(item)

    return item


@pytest.mark.parametrize(
    "status_inicial",
    [
        "aguardando",
        "chamado",
        "agendado",
        "cancelado",
        "expirado",
    ],
)
def test_permitem_arquivar_status_validos(
    sessao_fila,
    status_inicial,
):
    item = criar_item(
        sessao_fila,
        "tenant-a",
        status=status_inicial,
    )

    dados = (
        fila_espera_service
        .AtualizacaoStatusFilaEspera(
            status="arquivado"
        )
    )

    resultado = (
        fila_espera_service
        .atualizar_status_fila_espera(
            db=sessao_fila,
            tenant_slug="tenant-a",
            item_id=item.id,
            dados=dados,
        )
    )

    assert resultado["status"] == "arquivado"


def test_arquivado_nao_pode_voltar_para_aguardando(
    sessao_fila,
):
    item = criar_item(
        sessao_fila,
        "tenant-a",
        status="arquivado",
    )

    dados = (
        fila_espera_service
        .AtualizacaoStatusFilaEspera(
            status="aguardando"
        )
    )

    with pytest.raises(Exception):
        fila_espera_service.atualizar_status_fila_espera(
            db=sessao_fila,
            tenant_slug="tenant-a",
            item_id=item.id,
            dados=dados,
        )


def test_nao_arquiva_item_de_outro_tenant(
    sessao_fila,
):
    item = criar_item(
        sessao_fila,
        "tenant-b",
        status="aguardando",
    )

    dados = (
        fila_espera_service
        .AtualizacaoStatusFilaEspera(
            status="arquivado"
        )
    )

    with pytest.raises(Exception):
        fila_espera_service.atualizar_status_fila_espera(
            db=sessao_fila,
            tenant_slug="tenant-a",
            item_id=item.id,
            dados=dados,
        )



def test_exclui_item_arquivado_definitivamente(
    sessao_fila,
):
    item = criar_item(
        sessao_fila,
        "tenant-a",
        status="arquivado",
    )

    item_id = item.id

    resultado = (
        fila_espera_service
        .excluir_item_fila_espera(
            db=sessao_fila,
            tenant_slug="tenant-a",
            item_id=item_id,
        )
    )

    assert resultado["id"] == item_id
    assert resultado["excluido"] is True

    existente = (
        sessao_fila
        .query(models.FilaEspera)
        .filter(
            models.FilaEspera.id == item_id
        )
        .first()
    )

    assert existente is None


def test_nao_exclui_item_nao_arquivado(
    sessao_fila,
):
    item = criar_item(
        sessao_fila,
        "tenant-a",
        status="aguardando",
    )

    with pytest.raises(Exception) as erro:
        fila_espera_service.excluir_item_fila_espera(
            db=sessao_fila,
            tenant_slug="tenant-a",
            item_id=item.id,
        )

    assert (
        getattr(erro.value, "status_code", None)
        == 409
    )

    existente = (
        sessao_fila
        .query(models.FilaEspera)
        .filter(
            models.FilaEspera.id == item.id
        )
        .first()
    )

    assert existente is not None


def test_nao_exclui_item_de_outro_tenant(
    sessao_fila,
):
    item = criar_item(
        sessao_fila,
        "tenant-b",
        status="arquivado",
    )

    with pytest.raises(Exception) as erro:
        fila_espera_service.excluir_item_fila_espera(
            db=sessao_fila,
            tenant_slug="tenant-a",
            item_id=item.id,
        )

    assert (
        getattr(erro.value, "status_code", None)
        == 404
    )

    existente = (
        sessao_fila
        .query(models.FilaEspera)
        .filter(
            models.FilaEspera.id == item.id
        )
        .first()
    )

    assert existente is not None
