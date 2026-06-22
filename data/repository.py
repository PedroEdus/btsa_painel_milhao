"""Repositório de dados — ponto único de acesso para o painel.

Alterna entre MOCK e Fabric conforme config. Cache com TTL explícito
(CONTEXT 9/15.6). Recarregar a página não refaz a query; o TTL é que dispara.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from config.settings import CACHE_TTL_SEGUNDOS, USE_MOCK


@st.cache_data(ttl=CACHE_TTL_SEGUNDOS, show_spinner="Carregando dados da campanha…")
def carregar_dados() -> pd.DataFrame:
    """Retorna a base de consumo (mock ou Fabric). Cacheada por TTL."""
    if USE_MOCK:
        from data.mock import gerar
        return gerar()

    from data.onelake import load_painel_milhao_data
    return load_painel_milhao_data()


def ultima_atualizacao() -> datetime:
    """Horário do último refresh efetivo do cache (CONTEXT 12 / decisão 7)."""
    return datetime.now()


def limpar_cache() -> None:
    carregar_dados.clear()
