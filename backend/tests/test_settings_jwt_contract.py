import importlib.util
from pathlib import Path

import pytest


BACKEND_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)


SETTINGS_PATH = (
    BACKEND_DIR
    / "settings.py"
)


SECURITY_PATH = (
    BACKEND_DIR
    / "security.py"
)


def carregar_settings():
    spec = (
        importlib.util
        .spec_from_file_location(
            "settings_contract_test",
            SETTINGS_PATH,
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


def test_settings_sem_jwt_pode_iniciar():
    modulo = carregar_settings()

    configuracao = modulo.Settings(
        _env_file=None,
        database_url=
            "sqlite:///:memory:",
        app_env=
            "production",
        whatsapp_transport_mode=
            "fake",
    )

    assert (
        configuracao.jwt_secret_key
        is None
    )

    assert (
        configuracao.whatsapp_transport_mode
        == "fake"
    )


def test_settings_possui_um_unico_app_env():
    texto = SETTINGS_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        texto.count(
            'app_env: str = "development"'
        )
        == 1
    )


def test_security_declara_validador_jwt():
    texto = SECURITY_PATH.read_text(
        encoding="utf-8"
    )

    assert (
        "def validar_jwt_secret_key("
        in texto
    )

    assert (
        "JWT_SECRET_KEY nao configurado."
        in texto
    )

    assert (
        "SECRET_KEY = validar_jwt_secret_key("
        in texto
    )


def carregar_security_com_jwt(
    monkeypatch,
):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "segredo-teste-importacao-0123456789abcdef",
    )

    spec = (
        importlib.util
        .spec_from_file_location(
            "security_contract_test",
            SECURITY_PATH,
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


def test_validador_rejeita_none(
    monkeypatch,
):
    security = carregar_security_com_jwt(
        monkeypatch
    )

    with pytest.raises(
        RuntimeError,
        match="JWT_SECRET_KEY nao configurado",
    ):
        security.validar_jwt_secret_key(
            None
        )


def test_validador_rejeita_vazio(
    monkeypatch,
):
    security = carregar_security_com_jwt(
        monkeypatch
    )

    with pytest.raises(
        RuntimeError,
        match="JWT_SECRET_KEY nao configurado",
    ):
        security.validar_jwt_secret_key(
            "   "
        )


def test_validador_aceita_segredo(
    monkeypatch,
):
    security = carregar_security_com_jwt(
        monkeypatch
    )

    assert (
        security.validar_jwt_secret_key(
            "segredo-teste"
        )
        == "segredo-teste"
    )
