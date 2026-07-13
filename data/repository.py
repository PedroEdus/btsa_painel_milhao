"""Repositório de dados — ponto único de acesso para o painel.

A base do Fabric é atualizada às 8h e 15h (horário de Brasília). O cache é
keyado pela janela vigente: só refaz a query do OneLake quando uma nova
janela começa (fronteira + margem p/ o pipeline gravar o snapshot).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from config.settings import (
    ATUALIZACAO_MARGEM_MINUTOS,
    HORARIOS_ATUALIZACAO,
    TZ_BR,
)

_TZ = ZoneInfo(TZ_BR)
_MARGEM = timedelta(minutes=ATUALIZACAO_MARGEM_MINUTOS)


def agora_br() -> datetime:
    return datetime.now(_TZ)


def _fronteiras(agora: datetime) -> list[datetime]:
    """Fronteiras de atualização (8h/15h BR) de ontem, hoje e amanhã."""
    return [
        (agora + timedelta(days=d)).replace(hour=h, minute=0, second=0, microsecond=0)
        for d in (-1, 0, 1)
        for h in sorted(HORARIOS_ATUALIZACAO)
    ]


def janela_atual(agora: datetime | None = None) -> datetime:
    """Última fronteira cujo snapshot já deve estar gravado (fronteira+margem)."""
    agora = agora or agora_br()
    return max(f for f in _fronteiras(agora) if f + _MARGEM <= agora)


def proxima_atualizacao(agora: datetime | None = None) -> datetime:
    """Próximo instante em que o painel deve buscar dados novos."""
    agora = agora or agora_br()
    return min(f + _MARGEM for f in _fronteiras(agora) if f + _MARGEM > agora)


def segundos_ate_proxima_atualizacao() -> int:
    return max(60, int((proxima_atualizacao() - agora_br()).total_seconds()))


@st.cache_data(ttl=12 * 3600, show_spinner="Carregando dados da campanha…")
def _carregar(janela: str) -> pd.DataFrame:
    # `janela` existe só p/ keyar o cache: muda às 8h/15h BR → nova query.
    # SNAPSHOT_LOCAL (.env): parquet local no formato bronze — usado enquanto
    # a query nova (10/07, 50 cols) ainda não está no Fabric. Remover a var
    # volta ao OneLake.
    _local = os.getenv("SNAPSHOT_LOCAL", "")
    if _local:
        from data.adapter import adaptar
        return adaptar(pd.read_parquet(_local))
    from data.onelake import load_painel_milhao_data
    return load_painel_milhao_data()


def carregar_dados() -> pd.DataFrame:
    """Retorna a base de consumo do OneLake, cacheada por janela de atualização."""
    return _carregar(janela_atual().isoformat())


def ultima_atualizacao() -> datetime:
    """Horário nominal (BR) da base vigente — fronteira 8h/15h da janela atual."""
    return janela_atual()


def limpar_cache() -> None:
    _carregar.clear()
