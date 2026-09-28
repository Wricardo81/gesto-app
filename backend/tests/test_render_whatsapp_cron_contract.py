from pathlib import Path


ROOT = (
    Path(__file__)
    .resolve()
    .parents[2]
)

RENDER_YAML = (
    ROOT
    / "render.yaml"
)


def carregar_render_yaml() -> str:
    assert (
        RENDER_YAML.exists()
    )

    return RENDER_YAML.read_text(
        encoding="utf-8"
    )


def test_cron_whatsapp_aponta_para_executor_correto():
    texto = carregar_render_yaml()

    assert (
        "type: cron"
        in texto
    )

    assert (
        "name: gesto-app-whatsapp-outbox"
        in texto
    )

    assert (
        "rootDir: backend"
        in texto
    )

    assert (
        "python scripts/executar_outbox_whatsapp.py --limite 50"
        in texto
    )


def test_cron_whatsapp_permanece_em_transporte_fake():
    texto = carregar_render_yaml()

    assert (
        "WHATSAPP_TRANSPORT_MODE"
        in texto
    )

    linhas = [
        linha.strip()
        for linha in texto.splitlines()
    ]

    indice = linhas.index(
        "- key: WHATSAPP_TRANSPORT_MODE"
    )

    assert (
        linhas[
            indice + 1
        ]
        == "value: fake"
    )


def test_cron_whatsapp_nao_possui_opt_in_ou_segredos_meta():
    texto = carregar_render_yaml()

    assert (
        "--permitir-meta"
        not in texto
    )

    assert (
        "WHATSAPP_ACCESS_TOKEN"
        not in texto
    )

    assert (
        "WHATSAPP_APP_SECRET"
        not in texto
    )

    assert (
        "WHATSAPP_VERIFY_TOKEN"
        not in texto
    )


def test_cron_whatsapp_mantem_database_url_externa():
    texto = carregar_render_yaml()

    linhas = [
        linha.strip()
        for linha in texto.splitlines()
    ]

    indice = linhas.index(
        "- key: DATABASE_URL"
    )

    assert (
        linhas[
            indice + 1
        ]
        == "sync: false"
    )

    assert (
        "schedule: \"* * * * *\""
        in texto
    )
