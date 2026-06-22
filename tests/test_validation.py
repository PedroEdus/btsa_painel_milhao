"""Testes de validação do contrato (CONTEXT 14.2)."""

from __future__ import annotations

import pandas as pd

from data.mock import gerar
from services.validation import validar


def test_base_vazia_falha():
    r = validar(pd.DataFrame())
    assert not r.ok


def test_mock_passa_validacao():
    r = validar(gerar(50))
    assert r.ok


def test_coluna_obrigatoria_ausente_falha():
    df = gerar(20).drop(columns=["valor_principal"])
    r = validar(df)
    assert not r.ok


def test_duplicidade_no_grao_gera_aviso():
    df = gerar(20)
    dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    r = validar(dup)
    assert any("duplicadas" in a for a in r.avisos)


def test_cor_celula_status():
    from components.ui import _estilo_celula
    assert "background-color:#d8f3de" in _estilo_celula("elegivel")   # verde
    assert "background-color:#fffbeb" in _estilo_celula("pendente")   # amber
    assert "background-color:#fef2f2" in _estilo_celula("inadimplente")  # vermelho
    assert _estilo_celula("qualquer_outro") == ""
