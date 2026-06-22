"""Testes da regra de cupom e métricas (CONTEXT 5 / Etapa 6)."""

from __future__ import annotations

import pandas as pd

from config.settings import RegraCupom
from services.metrics import adicionar_cupons, adicionar_valor_elegivel, kpis_executivos


def _df(principal, multa=0.0, juros=0.0, custas=0.0):
    return pd.DataFrame([{
        "valor_principal": principal, "valor_multa": multa,
        "valor_juros": juros, "valor_custas": custas,
        "valor_total_recebido": principal + multa + juros + custas,
        "cpf_titular": "1", "status_cadastro": "cadastrado",
        "status_elegibilidade": "elegivel", "valor_recuperado": 0.0,
    }])


def test_cupom_blocos_completos_descarta_residual():
    # R$244 -> 2 cupons, descarta R$44 (CONTEXT 5.1)
    regra = RegraCupom(incluir_multa=False, incluir_juros=False, incluir_custas=False)
    out = adicionar_cupons(_df(244), regra)
    assert int(out["cupons_calculados"].iloc[0]) == 2


def test_cupom_1000_gera_10():
    regra = RegraCupom(incluir_multa=False, incluir_juros=False, incluir_custas=False)
    out = adicionar_cupons(_df(1000), regra)
    assert int(out["cupons_calculados"].iloc[0]) == 10


def test_valor_elegivel_soma_todos_componentes_por_default():
    # decisão Pedro: todo valor que entra no caixa
    regra = RegraCupom()  # principal+multa+juros+custas
    out = adicionar_valor_elegivel(_df(100, multa=50, juros=30, custas=20), regra)
    assert float(out["valor_elegivel"].iloc[0]) == 200.0


def test_excluir_custas_quando_flag_off():
    regra = RegraCupom(incluir_custas=False)
    out = adicionar_valor_elegivel(_df(100, custas=80), regra)
    assert float(out["valor_elegivel"].iloc[0]) == 100.0


def test_versao_regra_registrada():
    out = adicionar_cupons(_df(100), RegraCupom())
    assert out["regra_versao"].iloc[0] == RegraCupom().versao


def test_kpis_contam_clientes_unicos():
    df = adicionar_cupons(adicionar_valor_elegivel(_df(500)))
    m = kpis_executivos(df)
    assert m["clientes_participantes"] == 1
    assert m["cupons_calculados"] == 5
