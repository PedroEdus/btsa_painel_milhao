"""Testes de validação do contrato (CONTEXT 14.2)."""

from __future__ import annotations

import pandas as pd

from data.contract import OBRIGATORIAS
from services.validation import validar


def _base(n: int = 20) -> pd.DataFrame:
    """Base sintética mínima conforme o contrato (colunas obrigatórias)."""
    return pd.DataFrame({
        "empresa": ["Brasil Terrenos"] * n,
        "obra": ["Obra A"] * n,
        "num_venda": [f"V{i}" for i in range(n)],
        "cpf_titular": [f"{i:011d}" for i in range(n)],
        "mes_referencia": ["2026-07"] * n,
        "valor_principal": [100.0] * n,
        "valor_multa": [0.0] * n,
        "valor_juros": [0.0] * n,
        "valor_custas": [0.0] * n,
        "valor_total_recebido": [100.0] * n,
        "status_cadastro": ["cadastrado"] * n,
        "status_elegibilidade": ["elegivel"] * n,
    })


def test_base_sintetica_cobre_obrigatorias():
    assert set(OBRIGATORIAS) <= set(_base().columns)


def test_base_vazia_falha():
    r = validar(pd.DataFrame())
    assert not r.ok


def test_base_valida_passa():
    r = validar(_base(50))
    assert r.ok


def test_coluna_obrigatoria_ausente_falha():
    df = _base(20).drop(columns=["valor_principal"])
    r = validar(df)
    assert not r.ok


def test_duplicidade_no_grao_gera_aviso():
    df = _base(20)
    dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    r = validar(dup)
    assert any("duplicadas" in a for a in r.avisos)


def test_cor_celula_status():
    from components.ui import _estilo_celula
    assert "background-color:#d8f3de" in _estilo_celula("elegivel")   # verde
    assert "background-color:#fffbeb" in _estilo_celula("pendente")   # amber
    assert "background-color:#fef2f2" in _estilo_celula("inadimplente")  # vermelho
    assert _estilo_celula("qualquer_outro") == ""
