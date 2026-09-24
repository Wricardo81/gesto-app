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
        == "banco indisponivel"
    )
