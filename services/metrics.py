"""Métricas derivadas e regra de cupom (CONTEXT 5 / 15.4).

Regra de cupom = único ponto onde o valor elegível e a contagem de cupons são
calculados em Python. Tudo parametrizado por config.REGRA_CUPOM, com a versão
da regra registrada (CONTEXT decisão 12). Cupons calculados ≠ cupons oficiais
(CONTEXT 14.3): a coluna oficial nunca é preenchida aqui.

IMPORTANTE (CONTEXT 14.2): o valor elegível e os cupons são calculados ANTES de
qualquer junção que possa duplicar recebimentos. A base de consumo já vem no
grão certo; aqui só agregamos.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import CAMPANHA, REGRA_CUPOM


def adicionar_valor_elegivel(df: pd.DataFrame, regra=REGRA_CUPOM) -> pd.DataFrame:
    """Soma os componentes habilitados pela regra → coluna valor_elegivel."""
    df = df.copy()
    comps = [c for c in regra.componentes_elegiveis if c in df.columns]
    df["valor_elegivel"] = df[comps].fillna(0).sum(axis=1)
    return df


def adicionar_cupons(df: pd.DataFrame, regra=REGRA_CUPOM) -> pd.DataFrame:
    """Calcula cupons por linha a partir do valor elegível.

    apenas_blocos_completos=True → floor(valor / 100), descarta saldo residual.
    Marca regra_versao para rastreabilidade.
    """
    if "valor_elegivel" not in df.columns:
        df = adicionar_valor_elegivel(df, regra)
    df = df.copy()
    razao = df["valor_elegivel"] / regra.valor_por_cupom
    df["cupons_calculados"] = (
        np.floor(razao) if regra.apenas_blocos_completos else np.round(razao)
    ).astype("Int64")
    df["regra_versao"] = regra.versao
    return df


def preparar(df: pd.DataFrame, regra=REGRA_CUPOM) -> pd.DataFrame:
    """Pipeline padrão: valor elegível + cupons.

    Se cupons_calculados já existir (snapshot OneLake pré-calculado pelo Fabric),
    pula o recálculo Python — preserva os valores oficiais do Fabric.
    """
    if "cupons_calculados" in df.columns:
        if "valor_elegivel" not in df.columns:
            df = df.copy()
            df["valor_elegivel"] = df["valor_total_recebido"].fillna(0)
        return df
    return adicionar_cupons(adicionar_valor_elegivel(df, regra), regra)


def kpis_executivos(df: pd.DataFrame) -> dict[str, float]:
    """Indicadores da visão executiva (CONTEXT 10.2)."""
    elegivel = df["valor_elegivel"] if "valor_elegivel" in df else pd.Series(dtype=float)
    return {
        "valor_total_recebido": float(df["valor_total_recebido"].sum()),
        "valor_elegivel": float(elegivel.sum()),
        "cupons_calculados": int(df.get("cupons_calculados", pd.Series(dtype="Int64")).sum()),
        "clientes_participantes": int(df["cpf_titular"].nunique()),
        "clientes_cadastrados": int(
            df.loc[df["status_cadastro"] == "cadastrado", "cpf_titular"].nunique()
        ),
        "clientes_elegiveis": int(
            df.loc[df["status_elegibilidade"] == "elegivel", "cpf_titular"].nunique()
        ),
        "valor_recuperado": float(df.get("valor_recuperado", pd.Series(dtype=float)).sum()),
    }


def cupons_por_mes(df: pd.DataFrame) -> pd.DataFrame:
    """Cupons mensais — cada sorteio usa só o mês correspondente (CONTEXT 5.4)."""
    return (
        df.groupby("mes_referencia", as_index=False)["cupons_calculados"]
        .sum()
        .sort_values("mes_referencia")
    )


def recebimento_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Recebimento mensal + acumulado."""
    valid = df[df["data_recebimento"].notna() & (df["valor_total_recebido"] > 0)]
    if valid.empty:
        return pd.DataFrame({"data": [], "valor_total_recebido": [], "acumulado": []})
    mensal = (
        valid.groupby(valid["data_recebimento"].dt.to_period("M"), as_index=False)["valor_total_recebido"]
        .sum()
        .rename(columns={"data_recebimento": "data"})
        .sort_values("data")
    )
    mensal["data"] = mensal["data"].dt.to_timestamp()
    mensal["acumulado"] = mensal["valor_total_recebido"].cumsum()
    return mensal


def recebimento_diario(df: pd.DataFrame) -> pd.DataFrame:
    """Recebimento diário + acumulado (CONTEXT 10.3)."""
    valid = df[df["data_recebimento"].notna() & (df["valor_total_recebido"] > 0)]
    if valid.empty:
        return pd.DataFrame({"data": [], "valor_total_recebido": [], "acumulado": []})
    diario = (
        valid.groupby(valid["data_recebimento"].dt.date, as_index=False)["valor_total_recebido"]
        .sum()
        .rename(columns={"data_recebimento": "data"})
        .sort_values("data")
    )
    diario["acumulado"] = diario["valor_total_recebido"].cumsum()
    return diario


def recebimento_por_classificacao(df: pd.DataFrame) -> pd.DataFrame:
    """Normal vs recuperação (CONTEXT 10.3)."""
    return (
        df.groupby("classificacao_recebimento", as_index=False)["valor_total_recebido"]
        .sum()
    )


def funil_participacao(df: pd.DataFrame) -> pd.DataFrame:
    """Funil real da campanha (CONTEXT 7 — não inventar etapa de cadastro).

    Fluxo: Base total → Elegíveis → Geraram cupons. A etapa 'Cadastrados' do
    contrato é incluída SOMENTE se trouxer sinal próprio (diferente de elegíveis);
    no mock/dado atual cadastro==elegibilidade, então é omitida para não induzir
    leitura falsa. Cupons gerados = clientes com cupons_calculados > 0.
    """
    base = df["cpf_titular"].nunique()
    elegivel_mask = df["status_elegibilidade"] == "elegivel"
    ele = df.loc[elegivel_mask, "cpf_titular"].nunique()

    # Geraram cupons = elegíveis que efetivamente têm cupom (subconjunto dos
    # elegíveis → funil monotônico). Cupom é calculado sobre o recebimento, mas
    # só o elegível concorre, então a etapa final filtra por elegibilidade.
    if "cupons_calculados" in df.columns:
        com_cupom = df.loc[
            elegivel_mask & (df["cupons_calculados"].fillna(0) > 0), "cpf_titular"
        ].nunique()
    else:
        com_cupom = ele

    etapas = ["Base total", "Elegíveis", "Geraram cupons"]
    valores = [base, ele, com_cupom]

    # Inclui 'Cadastrados' só se for sinal independente (≠ elegíveis).
    if "status_cadastro" in df.columns:
        cad = df.loc[df["status_cadastro"] == "cadastrado", "cpf_titular"].nunique()
        if cad != ele:
            etapas.insert(1, "Cadastrados")
            valores.insert(1, cad)

    return pd.DataFrame({"etapa": etapas, "clientes": valores})


# ── Mês de referência atual (CONTEXT 6 — destaque dinâmico, nunca hardcoded) ──
def mes_referencia_atual() -> str:
    """Competência atual no formato YYYY-MM, a partir da data do sistema."""
    from datetime import date
    return date.today().strftime("%Y-%m")


# ── Recuperação vs. novos negócios (CONTEXT 12) ──────────────────────────────
# A campanha inicia em 01/07. Classificação por data de venda só é possível se
# a coluna existir. O contrato atual NÃO traz data_venda — função preparada com
# fallback para não quebrar o painel.
_COLS_DATA_VENDA = ("data_venda", "data_contrato", "data_negocio")


def classificar_origem_venda(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona coluna 'origem_negocio': 'Nova venda pós-campanha' | 'Base existente'.

    Usa a 1ª coluna de data de venda disponível (_COLS_DATA_VENDA) comparando com
    CAMPANHA.inicio. Se nenhuma existir, cai no fallback: usa
    'classificacao_recebimento' (recuperacao→'Base existente') quando presente,
    senão marca 'Indeterminado'. NUNCA levanta exceção (CONTEXT critério 2/3).
    """
    df = df.copy()
    col_data = next((c for c in _COLS_DATA_VENDA if c in df.columns), None)
    if col_data is not None:
        inicio = pd.Timestamp(CAMPANHA.inicio)
        datas = pd.to_datetime(df[col_data], errors="coerce")
        df["origem_negocio"] = datas.apply(
            lambda d: "Nova venda pós-campanha"
            if pd.notna(d) and d >= inicio else "Base existente"
        )
    elif "classificacao_recebimento" in df.columns:
        # Fallback aproximado: recuperação = base existente inadimplente.
        df["origem_negocio"] = df["classificacao_recebimento"].map(
            {"recuperacao": "Base existente", "normal": "Base existente"}
        ).fillna("Indeterminado")
    else:
        df["origem_negocio"] = "Indeterminado"
    return df


def tem_classificacao_origem(df: pd.DataFrame) -> bool:
    """True se há coluna real de data de venda p/ separar novos negócios."""
    return any(c in df.columns for c in _COLS_DATA_VENDA)


def top_obras(df: pd.DataFrame, n: int | None = 6) -> pd.DataFrame:
    """Obras por valor recebido (+ cupons + média diária). n=None → todas."""
    dias = (
        df[df["data_recebimento"].notna()]
        .groupby("obra")["data_recebimento"]
        .apply(lambda s: s.dt.date.nunique())
        .rename("dias_pagantes")
    )
    g = (
        df.groupby("obra", as_index=False)
        .agg(valor=("valor_total_recebido", "sum"), cupons=("cupons_calculados", "sum"))
        .sort_values("valor", ascending=False)
    )
    if n is not None and n < len(g):
        g = g.head(n)
    g = g.join(dias, on="obra")
    g["media_diaria"] = (g["valor"] / g["dias_pagantes"].clip(lower=1)).round(2)
    return g


def kpis_carteira(df: pd.DataFrame) -> dict[str, float | int]:
    """Extend kpis_executivos com adimplência, inadimplência e ticket médio."""
    base = kpis_executivos(df)
    total = base["clientes_participantes"]
    elegiveis = base["clientes_elegiveis"]
    n_vendas = df["num_venda"].nunique()
    valor_vencido = (
        float(df["valor_vencido_antes"].fillna(0).sum())
        if "valor_vencido_antes" in df.columns else 0.0
    )
    return {
        **base,
        "inadimplentes": total - elegiveis,
        "pct_adimplencia": round(100 * elegiveis / total, 1) if total else 0.0,
        "valor_vencido": valor_vencido,
        "ticket_medio": float(df["valor_total_recebido"].sum()) / n_vendas if n_vendas else 0.0,
        "cupons_por_cliente_apto": round(base["cupons_calculados"] / elegiveis, 1) if elegiveis else 0.0,
    }


def inadimplencia_por_cidade(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """Top N cidades por valor inadimplente (valor_vencido_antes)."""
    col = "valor_vencido_antes"
    if col not in df.columns:
        return pd.DataFrame({"cidade": [], col: []})
    return (
        df.groupby("cidade", as_index=False)[col]
        .sum()
        .sort_values(col, ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def cupons_por_cidade(df: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    """Top N cidades por cupons calculados."""
    if "cupons_calculados" not in df.columns:
        return pd.DataFrame({"cidade": [], "cupons_calculados": []})
    return (
        df.groupby("cidade", as_index=False)["cupons_calculados"]
        .sum()
        .sort_values("cupons_calculados", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )


def calendario_sorteios() -> pd.DataFrame:
    """Calendário: mês pagamento → mês sorteio → prêmio → status."""
    from datetime import date
    hoje = date.today()
    meses = pd.period_range(CAMPANHA.inicio, CAMPANHA.fim, freq="M")
    rows = []
    for i, mes_pag in enumerate(meses):
        mes_sor = mes_pag + 1
        is_final = i == len(meses) - 1
        premio = "R$ 1.000.000" if is_final else "Casa + Carro"
        ano_sor, mes_num_sor = mes_sor.year, mes_sor.month
        ano_pag, mes_num_pag = mes_pag.year, mes_pag.month
        if (ano_sor, mes_num_sor) < (hoje.year, hoje.month):
            status = "Realizado"
        elif (ano_pag, mes_num_pag) == (hoje.year, hoje.month):
            status = "Em breve"
        elif is_final:
            status = "Final"
        else:
            status = "Futuro"
        rows.append({
            "Pagamento": mes_pag.strftime("%b/%Y"),
            "Sorteio": mes_sor.strftime("%b/%Y"),
            "Prêmio": premio,
            "Status": status,
            "_final": is_final,
        })
    return pd.DataFrame(rows)


def progresso_campanha(hoje=None) -> dict:
    """Progresso temporal da campanha (CONTEXT 2.1: 01/jul → 31/dez)."""
    from datetime import date

    hoje = hoje or date.today()
    total = (CAMPANHA.fim - CAMPANHA.inicio).days or 1
    decorrido = max(0, min(total, (hoje - CAMPANHA.inicio).days))
    return {
        "dias_decorridos": decorrido,
        "dias_totais": total,
        "dias_restantes": total - decorrido,
        "pct": round(100 * decorrido / total, 1),
    }
