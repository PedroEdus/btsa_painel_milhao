"""Adapter: mapeia colunas do snapshot OneLake para o schema interno do painel.

O snapshot bronze tem nomes e formatos diferentes do contrato (contract.py).
Este módulo é o único ponto de tradução — serviços e métricas nunca sabem
da origem real.

Formato 07/2026 (query nova): nomes com espaço/acento normalizados pelo
pipeline p/ snake_case sem acento; valores monetários numéricos (antes
"R$1.234,56" string); datas datetime; cupons pré-calculados em cupons_milhao
sobre valor_gera_cupom (floor(valor/100), conferido 100% na carga 06/07).
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd


def _norm_col(col: str) -> str:
    """'Cupons Milhão' → 'cupons_milhao' (mesma normalização do pipeline)."""
    sem_acento = (
        unicodedata.normalize("NFKD", str(col)).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^0-9a-zA-Z]+", "_", sem_acento).strip("_").lower()


def _parse_brl(series: pd.Series) -> pd.Series:
    """'R$1.234,56' → float. Já numérico passa direto. Nulos viram 0.0."""
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0.0).astype(float)
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
    df.columns = [_norm_col(c) for c in df.columns]

    # ── Nome da obra ─────────────────────────────────────────────────────────
    if "nomeobra" in df.columns:
        df["obra_nome"] = df["nomeobra"]
    else:
        # Formato antigo: codobra → primeiro produto não-nulo do código.
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

    # ── Valores monetários (string BRL ou numérico → float) ──────────────────
    df["valor_total_recebido"] = _parse_brl(df["valor_recebido"])
    df["valor_vencido_antes"]  = _parse_brl(df["valor_inadimplencia"])
    # Valor que efetivamente gera cupom (base do cálculo do Fabric).
    if "valor_gera_cupom" in df.columns:
        df["valor_elegivel"] = _parse_brl(df["valor_gera_cupom"])
    else:
        df["valor_elegivel"] = df["valor_total_recebido"]

    # ── Cupons (pré-calculados pelo Fabric → Int64) ──────────────────────────
    _col_cupons = "cupons_milhao" if "cupons_milhao" in df.columns else "cupons_gerados"
    df["cupons_calculados"] = (
        pd.to_numeric(df[_col_cupons], errors="coerce")
        .fillna(0)
        .astype("Int64")
    )

    # ── Identificadores ──────────────────────────────────────────────────────
    df["obra"]      = df["obra_nome"]   # nome legível como coluna canônica
    df["num_venda"] = df["num_venda"].astype(str)
    df["empresa"] = (
        df["nomeempresa"] if "nomeempresa" in df.columns else "Brasil Terrenos"
    )
    # Código da empresa como coluna separada.
    if "codempresa" in df.columns:
        df["empresa_codigo"] = df["codempresa"].astype(str)
    # Regional vem com espaço à esquerda no bronze (" NORTE"); normaliza.
    if "regional" in df.columns:
        df["regional"] = df["regional"].astype(str).str.strip()
    # Telefone numérico na query nova (6.19e10) → string legível.
    if pd.api.types.is_numeric_dtype(df["telefone"]):
        df["telefone"] = (
            df["telefone"].astype("Int64").astype(str).replace("<NA>", "")
        )

    # ── Datas ────────────────────────────────────────────────────────────────
    df["data_recebimento"] = pd.to_datetime(
        df["data_recebimento"], dayfirst=True, errors="coerce"
    )
    if "dt_venda" in df.columns:
        # Habilita classificar_origem_venda (novos negócios vs base existente).
        df["data_venda"] = pd.to_datetime(df["dt_venda"], dayfirst=True, errors="coerce")
    df["data_ultima_atualizacao"] = (
        df["snapshot_gerado_em"] if "snapshot_gerado_em" in df.columns else pd.NaT
    )

    # Mês de referência derivado da data do último recebimento; sem recebimento
    # cai na competência corrente.
    df["mes_referencia"] = (
        df["data_recebimento"].dt.strftime("%Y-%m")
        .fillna(pd.Timestamp.now().strftime("%Y-%m"))
    )

    # ── Elegibilidade ────────────────────────────────────────────────────────
    _apto = df["status_sorteio"].astype(str).str.strip().str.upper() == "APTO"
    df["status_elegibilidade"] = _apto.map({True: "elegivel", False: "pendente"})
    df["status_cadastro"]      = _apto.map({True: "cadastrado", False: "nao_cadastrado"})

    # ── Financeiro derivado ──────────────────────────────────────────────────
    # Decomposição não disponível no bronze — usa total como principal
    df["valor_principal"] = df["valor_total_recebido"]
    df["valor_multa"]     = 0.0
    df["valor_juros"]     = 0.0
    df["valor_custas"]    = 0.0

    # ── Flags e defaults ─────────────────────────────────────────────────────
    # Recuperação = estava inadimplente e regularizou no mês.
    if "recuperacao" in df.columns:
        # Query atual: flag explícita calculada pelo Fabric (estava inadimplente
        # no fechamento e pagou). Fonte de verdade — nada de proxy.
        _recup = pd.to_numeric(df["recuperacao"], errors="coerce").fillna(0) > 0
    elif "inadimplente_no_mes_pago" in df.columns:
        _recup = df["inadimplente_no_mes_pago"].astype(str).str.strip().str.upper().str.startswith("S")
    elif "pagou_parcela_mes_anterior" in df.columns:
        # Proxy fraco: não pagou a parcela do mês anterior mas está APTO agora.
        _recup = (
            df["pagou_parcela_mes_anterior"].astype(str).str.strip().str.upper().str.startswith("N")
            & _apto
        )
    else:
        _recup = pd.Series(False, index=df.index)
    df["classificacao_recebimento"] = _recup.map({True: "recuperacao", False: "normal"})
    # Valor recuperado = o que os recuperados pagaram no período.
    df["valor_recuperado"] = df["valor_total_recebido"].where(_recup, 0.0)
    # Foto da inadimplência no fechamento de junho (início da campanha).
    if "inad_junho" in df.columns:
        _inad_jun = pd.to_numeric(df["inad_junho"], errors="coerce").fillna(0) > 0
        df["status_inadimplencia_antes"] = _inad_jun.map(
            {True: "inadimplente", False: "adimplente"}
        )
    df["flag_vencido"]                = ~_apto
    df["participa_proximos_sorteios"] = _apto
    df["flag_antecipacao"]            = False
    df["flag_negociacao"]             = False
    df["titular_principal"]           = True
    df["qtd_compradores"]             = 1
    df["flag_contemplado_casa"]       = False
    df["qtd_parcelas_pagas"]          = 0
    # Dias de atraso real (bronze: diasatraso, nulo p/ adimplente → 0).
    if "diasatraso" in df.columns:
        df["dias_atraso"] = pd.to_numeric(df["diasatraso"], errors="coerce").fillna(0).astype(int)
    else:
        df["dias_atraso"] = 0
    df["qtd_parcelas_vencidas"]       = 0
    if "status_inadimplencia_antes" not in df.columns:  # setado acima via inad_junho
        df["status_inadimplencia_antes"] = "adimplente"
    df["status_apos_pagamento"]       = "adimplente"

    return df
