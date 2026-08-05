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


PLANO_ESSENCIAL = PlanoAssinatura(
    codigo="essencial",
    nome="Plano Essencial",
    periodicidade="mensal",
    valor_mensal_equivalente=59.00,
    valor_total=59.00,
    meses=1,
    desconto_percentual=0,
    stripe_price_env="stripe_price_essencial",
)

PLANO_PROFISSIONAL = PlanoAssinatura(
    codigo="profissional",
    nome="Plano Profissional",
    periodicidade="mensal",
    valor_mensal_equivalente=129.00,
    valor_total=129.00,
    meses=1,
    desconto_percentual=0,
    stripe_price_env="stripe_price_profissional",
)

PLANO_EMPRESA = PlanoAssinatura(
    codigo="empresa",
    nome="Plano Empresa",
    periodicidade="mensal",
    valor_mensal_equivalente=299.00,
    valor_total=299.00,
    meses=1,
    desconto_percentual=0,
    stripe_price_env="stripe_price_empresa",
)

PLANO_TESTE_MP = PlanoAssinatura(
    codigo="teste_mp",
    nome="Teste Mercado Pago",
    periodicidade="teste",
    meses=1,
    desconto_percentual=0,
    valor_total=1.00,
    valor_mensal_equivalente=1.00,
    stripe_price_env="stripe_price_teste_mp",
)


PLANOS_ASSINATURA = {
    "essencial": PLANO_ESSENCIAL,
    "profissional": PLANO_PROFISSIONAL,
    "empresa": PLANO_EMPRESA,

    # Compatibilidade temporária com links antigos.
    "mensal": PLANO_ESSENCIAL,
    "trimestral": PLANO_PROFISSIONAL,
    "anual": PLANO_EMPRESA,

    # Plano técnico de teste.
    "teste_mp": PLANO_TESTE_MP,
}


def listar_planos_assinatura() -> list[dict]:
    planos_unicos = [
        PLANO_ESSENCIAL,
        PLANO_PROFISSIONAL,
        PLANO_EMPRESA,
    ]

    return [
        plano.__dict__
        for plano in planos_unicos
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
