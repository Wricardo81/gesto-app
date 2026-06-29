from dataclasses import dataclass


@dataclass(frozen=True)
class PlanoAssinatura:
    codigo: str
    nome: str
    periodicidade: str
    valor_mensal_equivalente: float
    valor_total: float
    meses: int
    desconto_percentual: int
    stripe_price_env: str


PLANOS_ASSINATURA = {
    "mensal": PlanoAssinatura(
        codigo="mensal",
        nome="Plano Mensal",
        periodicidade="mensal",
        valor_mensal_equivalente=99.00,
        valor_total=99.00,
        meses=1,
        desconto_percentual=0,
        stripe_price_env="stripe_price_mensal",
    ),
    "trimestral": PlanoAssinatura(
        codigo="trimestral",
        nome="Plano Trimestral",
        periodicidade="trimestral",
        valor_mensal_equivalente=89.00,
        valor_total=267.00,
        meses=3,
        desconto_percentual=10,
        stripe_price_env="stripe_price_trimestral",
    ),
    "anual": PlanoAssinatura(
        codigo="anual",
        nome="Plano Anual",
        periodicidade="anual",
        valor_mensal_equivalente=79.00,
        valor_total=948.00,
        meses=12,
        desconto_percentual=20,
        stripe_price_env="stripe_price_anual",
    ),
    "teste_mp": PlanoAssinatura(
        codigo="teste_mp",
        nome="Teste Mercado Pago",
        periodicidade="teste",
        meses=1,
        desconto_percentual=0,
        valor_total=1.00,
        valor_mensal_equivalente=1.00,
        stripe_price_env="stripe_price_teste_mp",
    ),
}


def listar_planos_assinatura() -> list[dict]:
    return [
        plano.__dict__
        for plano in PLANOS_ASSINATURA.values()
    ]


def obter_plano_assinatura(
    codigo: str,
) -> PlanoAssinatura:
    codigo_normalizado = str(
        codigo or ""
    ).strip().lower()

    plano = PLANOS_ASSINATURA.get(
        codigo_normalizado
    )

    if not plano:
        raise ValueError(
            "Plano de assinatura inválido."
        )

    return plano