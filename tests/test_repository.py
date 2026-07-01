"""Testes da janela de atualização (base Fabric: 8h e 15h, Brasília)."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from data.repository import janela_atual, proxima_atualizacao

_TZ = ZoneInfo("America/Sao_Paulo")


def _dt(dia: int, hora: int, minuto: int = 0) -> datetime:
    return datetime(2026, 7, dia, hora, minuto, tzinfo=_TZ)


def test_meio_dia_usa_janela_das_8():
    j = janela_atual(_dt(10, 12))
    assert (j.day, j.hour) == (10, 8)


def test_noite_usa_janela_das_15():
    j = janela_atual(_dt(10, 20))
    assert (j.day, j.hour) == (10, 15)


def test_madrugada_usa_15h_de_ontem():
    j = janela_atual(_dt(10, 2))
    assert (j.day, j.hour) == (9, 15)


def test_dentro_da_margem_ainda_usa_janela_anterior():
    # 8h15 com margem de 20min: snapshot das 8h ainda pode estar sendo gravado.
    j = janela_atual(_dt(10, 8, 15))
    assert (j.day, j.hour) == (9, 15)


def test_proxima_atualizacao_apos_agora():
    agora = _dt(10, 12)
    prox = proxima_atualizacao(agora)
    assert prox > agora
    assert prox.hour == 15  # margem em minutos não muda a hora
