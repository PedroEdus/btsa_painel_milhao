"""Adapter: mapeia colunas do snapshot OneLake para o schema interno do painel.

O snapshot bronze tem nomes e formatos diferentes do contrato (contract.py).
Este módulo é o único ponto de tradução — serviços e métricas nunca sabem
da origem real.
"""

from __future__ import annotations

import pandas as pd


def _parse_brl(series: pd.Series) -> pd.Series:
    """'R$1.234,56' → float. Valores inválidos/nulos viram 0.0."""
    return (
        series.astype(str)
        .str.replace(r"R\$\s*", "", regex=True)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0.0)
    )


def adaptar(df: pd.DataFrame) -> pd.DataFrame:
    """Transforma snapshot bronze → schema esperado pelos serviços do painel."""
    df = df.copy()

    # ── Nome da obra: codobra → primeiro produto não-nulo do código ────────────
    _nome_obra = (
        df[df["produto"].notna()][["codobra", "produto"]]
        .drop_duplicates("codobra")
        .set_index("codobra")["produto"]
    )
    df["obra_nome"] = df["codobra"].map(_nome_obra).fillna(df["codobra"].astype(str))

    # ── Renomear colunas diretas ─────────────────────────────────────────────
    df = df.rename(columns={
        "codobra":                 "obra_codigo",
        "venda":                   "num_venda",
        "nomecliente":             "nome_cliente",
        "cpf_pes":                 "cpf_titular",
        "emailcliente":            "email",
        "telefoneformatado":       "telefone",
        "data_ultimo_recebimento": "data_recebimento",
        "motivo":                  "motivo_bloqueio",
    })

    # ── Valores monetários ("R$1.234,56" → float) ────────────────────────────
    df["valor_total_recebido"] = _parse_brl(df["valor_recebido"])
    df["valor_vencido_antes"]  = _parse_brl(df["valor_inadimplencia"])

    # ── Cupons (Decimal do Spark → Int64) ────────────────────────────────────
    df["cupons_calculados"] = (
        pd.to_numeric(df["cupons_gerados"], errors="coerce")
        .fillna(0)
        .astype("Int64")
    )

    # ── Identificadores ──────────────────────────────────────────────────────
    df["obra"]      = df["obra_nome"]   # nome legível como coluna canônica
    df["num_venda"] = df["num_venda"].astype(str)
    df["empresa"]   = "Brasil Terrenos"

    # ── Datas ────────────────────────────────────────────────────────────────
    df["data_recebimento"]      = pd.to_datetime(df["data_recebimento"], dayfirst=True, errors="coerce")
    df["data_ultima_atualizacao"] = df["snapshot_gerado_em"]

    # Mês de referência derivado da data do último recebimento
    df["mes_referencia"] = (
        df["data_recebimento"].dt.strftime("%Y-%m").fillna("2026-06")
    )

    # ── Elegibilidade ────────────────────────────────────────────────────────
    _apto = df["status_sorteio"].astype(str).str.strip().str.upper() == "APTO"
    df["status_elegibilidade"] = _apto.map({True: "elegivel", False: "pendente"})
    df["status_cadastro"]      = _apto.map({True: "cadastrado", False: "nao_cadastrado"})

    # ── Financeiro derivado ──────────────────────────────────────────────────
    # Valor elegível = valor recebido (cupons já calculados pelo Fabric)
    df["valor_elegivel"]  = df["valor_total_recebido"]
    # Decomposição não disponível no bronze — usa total como principal
    df["valor_principal"] = df["valor_total_recebido"]
    df["valor_multa"]     = 0.0
    df["valor_juros"]     = 0.0
    df["valor_custas"]    = 0.0
    df["valor_recuperado"] = 0.0

    # ── Flags e defaults ─────────────────────────────────────────────────────
    df["classificacao_recebimento"]   = "normal"
    df["flag_vencido"]                = ~_apto
    df["participa_proximos_sorteios"] = _apto
    df["flag_antecipacao"]            = False
    df["flag_negociacao"]             = False
    df["titular_principal"]           = True
    df["qtd_compradores"]             = 1
    df["flag_contemplado_casa"]       = False
    df["participa_proximos_sorteios"] = _apto
    df["qtd_parcelas_pagas"]          = 0
    df["dias_atraso"]                 = 0
    df["qtd_parcelas_vencidas"]       = 0
    df["status_inadimplencia_antes"]  = "adimplente"
    df["status_apos_pagamento"]       = "adimplente"

    return df
