from datetime import UTC, datetime

import pytest
import importlib.util
import json
from pathlib import Path

from fastapi import HTTPException


SCRIPT_PATH = (
    Path(__file__)
    .resolve()
    .parents[1]
    / "scripts"
    / "executar_outbox_whatsapp.py"
)


def carregar_executor():
    spec = (
        importlib.util
        .spec_from_file_location(
            "executor_outbox_contrato",
            SCRIPT_PATH,
        )
    )

    modulo = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        modulo
    )

    return modulo


def test_status_healthy_sem_falhas():
    executor = carregar_executor()

    status = (
        executor
        .classificar_status_operacional(
            {
                "falhas": 0,
            }
        )
    )

    assert (
        status
        == "healthy"
    )


def test_status_partial_com_falhas():
    executor = carregar_executor()

    status = (
        executor
        .classificar_status_operacional(
            {
                "falhas": 2,
            }
        )
    )

    assert (
        status
        == "partial"
    )


def test_main_healthy_retorna_exit_zero(
    monkeypatch,
    capsys,
):
    executor = carregar_executor()

    monkeypatch.setattr(
        executor,
        "executar_outbox_whatsapp",
        lambda **kwargs: {
            "executor":
                "whatsapp_outbox",

            "status_operacional":
                "healthy",

            "modo_transporte":
                "fake",

            "limite":
                kwargs["limite"],

            "selecionadas":
                0,

            "enviadas":
                0,

            "falhas":
                0,

            "envios":
                [],

            "erros":
                [],
        },
    )

    codigo = executor.main(
        [
            "--limite",
            "10",
        ]
    )

    saida = capsys.readouterr()

    dados = json.loads(
        saida.out
    )

    assert codigo == 0

    assert (
        dados[
            "status_operacional"
        ]
        == "healthy"
    )


def test_main_partial_tambem_retorna_exit_zero(
    monkeypatch,
    capsys,
):
    executor = carregar_executor()

    monkeypatch.setattr(
        executor,
        "executar_outbox_whatsapp",
        lambda **kwargs: {
            "executor":
                "whatsapp_outbox",

            "status_operacional":
                "partial",

            "modo_transporte":
                "fake",

            "limite":
                kwargs["limite"],

            "selecionadas":
                1,

            "enviadas":
                0,

            "falhas":
                1,

            "envios":
                [],

            "erros":
                [
                    {
                        "status_code":
                            502,

                        "erro":
                            "falha temporaria",
                    }
                ],
        },
    )

    codigo = executor.main(
        [
            "--limite",
            "10",
        ]
    )

    saida = capsys.readouterr()

    dados = json.loads(
        saida.out
    )

    assert codigo == 0

    assert (
        dados[
            "status_operacional"
        ]
        == "partial"
    )


def test_main_http_exception_retorna_fatal_exit_2(
    monkeypatch,
    capsys,
):
    executor = carregar_executor()

    def falhar(
        **kwargs,
    ):
        raise HTTPException(
            status_code=503,
            detail=(
                "configuracao invalida"
            ),
        )

    monkeypatch.setattr(
        executor,
        "executar_outbox_whatsapp",
        falhar,
    )

    codigo = executor.main(
        [
            "--limite",
            "10",
        ]
    )

    saida = capsys.readouterr()

    dados = json.loads(
        saida.err
    )

    assert codigo == 2

    assert (
        dados[
            "status_operacional"
        ]
        == "fatal"
    )

    assert (
        dados[
            "status_code"
        ]
        == 503
    )


def test_executor_fake_nao_exige_opt_in(
    monkeypatch,
):
    executor = carregar_executor()

    monkeypatch.setattr(
        executor.settings,
        "whatsapp_transport_mode",
        "fake",
    )

    modo = (
        executor
        .validar_modo_transporte_executor(
            permitir_meta=False,
        )
    )

    assert modo == "fake"


def test_executor_meta_sem_opt_in_e_bloqueado(
    monkeypatch,
):
    executor = carregar_executor()

    monkeypatch.setattr(
        executor.settings,
        "whatsapp_transport_mode",
        "meta",
    )

    with pytest.raises(
        executor.HTTPException
    ) as erro:
        (
            executor
            .validar_modo_transporte_executor(
                permitir_meta=False,
            )
        )

    assert (
        erro.value.status_code
        == 503
    )

    assert (
        "Meta bloqueado"
        in str(
            erro.value.detail
        )
    )


def test_executor_meta_com_opt_in_expresso_e_permitido(
    monkeypatch,
):
    executor = carregar_executor()

    monkeypatch.setattr(
        executor.settings,
        "whatsapp_transport_mode",
        "meta",
    )

    modo = (
        executor
        .validar_modo_transporte_executor(
            permitir_meta=True,
        )
    )

    assert modo == "meta"


def test_metadados_operacionais_preservam_resultado(
    monkeypatch,
):
    executor = carregar_executor()

    monkeypatch.setattr(
        executor,
        "perf_counter",
        lambda: 10.125,
    )

    momento = datetime(
        2026,
        9,
        28,
        12,
        30,
        0,
        tzinfo=UTC,
    )

    resultado = (
        executor
        .adicionar_metadados_operacionais(
            {
                "executor":
                    "whatsapp_outbox",

                "status_operacional":
                    "healthy",

                "selecionadas":
                    2,
            },
            inicio_monotonic=10.0,
            execucao_id=
                "execucao-teste-001",
            executado_em=momento,
        )
    )

    assert (
        resultado["executor"]
        == "whatsapp_outbox"
    )

    assert (
        resultado["status_operacional"]
        == "healthy"
    )

    assert (
        resultado["selecionadas"]
        == 2
    )

    assert (
        resultado["execucao_id"]
        == "execucao-teste-001"
    )

    assert (
        resultado["executado_em_utc"]
        == "2026-09-28T12:30:00+00:00"
    )

    assert (
        resultado["duracao_ms"]
        == 125.0
    )


def test_metadados_operacionais_nao_aceitam_duracao_negativa(
    monkeypatch,
):
    executor = carregar_executor()

    monkeypatch.setattr(
        executor,
        "perf_counter",
        lambda: 9.0,
    )

    resultado = (
        executor
        .adicionar_metadados_operacionais(
            {
                "status_operacional":
                    "fatal",
            },
            inicio_monotonic=10.0,
            execucao_id=
                "execucao-teste-002",
            executado_em=datetime(
                2026,
                9,
                28,
                tzinfo=UTC,
            ),
        )
    )

    assert (
        resultado["duracao_ms"]
        == 0.0
    )

    assert (
        resultado["execucao_id"]
        == "execucao-teste-002"
    )


def test_main_exception_generica_retorna_fatal_exit_2(
    monkeypatch,
    capsys,
):
    executor = carregar_executor()

    def falhar(
        **kwargs,
    ):
        raise RuntimeError(
            "banco indisponivel"
        )

    monkeypatch.setattr(
        executor,
        "executar_outbox_whatsapp",
        falhar,
    )

    codigo = executor.main(
        [
            "--limite",
            "10",
        ]
    )

    saida = capsys.readouterr()

    dados = json.loads(
        saida.err
    )

    assert codigo == 2

    assert (
        dados[
            "status_operacional"
        ]
        == "fatal"
    )

    assert (
        dados[
            "erro_tipo"
        ]
        == "RuntimeError"
    )

    assert (
        dados[
            "erro"
        ]
        == (
            "Falha interna no executor "
            "da outbox."
        )
    )

    assert (
        dados[
            "status_code"
        ]
        == 500
    )

    serializado = str(
        dados
    )

    assert (
        "banco indisponivel"
        not in serializado
    )
