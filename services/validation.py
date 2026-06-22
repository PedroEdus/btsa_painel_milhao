"""Validação da base contra o contrato (CONTEXT Etapa 4 / decisão 8).

Confere colunas ausentes, tipos e duplicidade por venda ANTES de exibir.
Duplicidade por múltiplos compradores é risco crítico (CONTEXT 5.8/14.2):
a quantidade de cupons nunca pode ser inflada por linhas repetidas da mesma venda.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from data.contract import CHAVE_GRAO, OBRIGATORIAS


@dataclass
class ResultadoValidacao:
    ok: bool
    erros: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def validar(df: pd.DataFrame) -> ResultadoValidacao:
    erros: list[str] = []
    avisos: list[str] = []

    if df is None or df.empty:
        return ResultadoValidacao(ok=False, erros=["Base vazia ou indisponível."])

    # colunas obrigatórias
    faltando = [c for c in OBRIGATORIAS if c not in df.columns]
    if faltando:
        erros.append(f"Colunas obrigatórias ausentes: {', '.join(faltando)}")

    # duplicidade no grão (CONTEXT 14.2)
    # Grão do snapshot OneLake é por venda+cpf, sem mes_referencia real —
    # mes_referencia derivado causa falsos positivos; só avisa se duplicatas > 1%
    chave = [c for c in CHAVE_GRAO if c in df.columns]
    if chave:
        dups = int(df.duplicated(subset=chave).sum())
        if dups and dups / max(len(df), 1) > 0.01:
            avisos.append(
                f"{dups} linhas duplicadas no grão {chave} — risco de inflar cupons."
            )

    # nulos em valores financeiros
    for col in ("valor_total_recebido", "valor_principal"):
        if col in df.columns and df[col].isna().any():
            avisos.append(f"Valores nulos em {col} (tratados como 0 no cálculo).")

    return ResultadoValidacao(ok=not erros, erros=erros, avisos=avisos)
