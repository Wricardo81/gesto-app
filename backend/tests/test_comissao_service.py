from services.comissao_service import calcular_valor_comissao


def test_calcular_comissao_percentual():
    resultado = calcular_valor_comissao(
        valor_atendimento=100,
        comissao_tipo="percentual",
        comissao_valor=20,
    )

    assert resultado == 20.0


def test_calcular_comissao_valor_fixo():
    resultado = calcular_valor_comissao(
        valor_atendimento=100,
        comissao_tipo="valor_fixo",
        comissao_valor=15,
    )

    assert resultado == 15.0


def test_calcular_comissao_sem_comissao():
    resultado = calcular_valor_comissao(
        valor_atendimento=100,
        comissao_tipo="nenhuma",
        comissao_valor=0,
    )

    assert resultado == 0.0


def test_calcular_comissao_percentual_com_arredondamento():
    resultado = calcular_valor_comissao(
        valor_atendimento=99.99,
        comissao_tipo="percentual",
        comissao_valor=33,
    )

    assert resultado == 33.0


def test_calcular_comissao_tipo_desconhecido_retorna_zero():
    resultado = calcular_valor_comissao(
        valor_atendimento=100,
        comissao_tipo="invalido",
        comissao_valor=50,
    )

    assert resultado == 0.0
