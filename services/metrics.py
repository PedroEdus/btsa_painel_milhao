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

from components.format import mes_ano_pt
from config.settings import CAMPANHA, REGRA_CUPOM
from data.contract import CHAVE_VENDA


def id_contrato(df: pd.DataFrame) -> pd.Series:
    """ID único de contrato (venda) — CHAVE_VENDA: empresa+obra+num_venda.

    Paradigma do painel (CONTEXT decisão): elegibilidade/inadimplência/funil
    contam por CONTRATO, não por cliente — uma venda pode ter vários
    compradores (qtd_compradores) que não devem inflar a contagem.
    """
    # Concatenação vetorizada: agg("|".join, axis=1) faz apply linha a linha
    # (Python puro) e domina o tempo de cada rerun em bases grandes.
    cols = list(CHAVE_VENDA)
    serie = df[cols[0]].astype(str)
    for col in cols[1:]:
        serie = serie + "|" + df[col].astype(str)
    return serie


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
    """Indicadores da visão executiva (CONTEXT 10.2).

    clientes_participantes é a ÚNICA métrica por cliente (cpf_titular) — fica
    reservada pro card inicial "quantidade de clientes únicos". Cadastro,
    elegibilidade e recuperação contam por CONTRATO (id_contrato).
    """
    elegivel = df["valor_elegivel"] if "valor_elegivel" in df else pd.Series(dtype=float)
    contrato = id_contrato(df)
    return {
        "valor_total_recebido": float(df["valor_total_recebido"].sum()),
        "valor_elegivel": float(elegivel.sum()),
        "cupons_calculados": int(df.get("cupons_calculados", pd.Series(dtype="Int64")).sum()),
        "clientes_participantes": int(df["cpf_titular"].nunique()),
        "contratos_participantes": int(contrato.nunique()),
        "contratos_cadastrados": int(
            contrato[df["status_cadastro"] == "cadastrado"].nunique()
        ),
        "contratos_elegiveis": int(
            contrato[df["status_elegibilidade"] == "elegivel"].nunique()
        ),
        # Cupons de contratos APTO — só esses concorrem de fato ao sorteio.
        "cupons_elegiveis": int(
            df.loc[df["status_elegibilidade"] == "elegivel", "cupons_calculados"]
            .fillna(0).sum()
            if "cupons_calculados" in df.columns else 0
        ),
        "valor_recuperado": float(df.get("valor_recuperado", pd.Series(dtype=float)).sum()),
        "contratos_recuperados": (
            int(contrato[df["classificacao_recebimento"] == "recuperacao"].nunique())
            if "classificacao_recebimento" in df.columns else 0
        ),
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


def recebimento_por_origem(df: pd.DataFrame) -> pd.DataFrame:
    """Recebimento no padrão da empresa (reunião 09/07 — Robson):

    Em dia      = parcela do mês vigente paga dentro do mês
    Recuperado  = parcela de meses anteriores (paga após o vencimento)
    Antecipado  = parcela de mês futuro

    Valores reais da query 10/07 (Valor Recuperado / Valor Antecipado);
    Em dia = total − recuperado − antecipado. Origens zeradas são omitidas.
    """
    total = float(df["valor_total_recebido"].sum())
    recuperado = float(df.get("valor_recuperado", pd.Series(dtype=float)).sum())
    antecipado = float(df.get("valor_antecipado", pd.Series(dtype=float)).sum())
    em_dia = max(0.0, total - recuperado - antecipado)
    linhas = pd.DataFrame({
        "origem": ["Em dia", "Recuperado", "Antecipado"],
        "valor": [em_dia, recuperado, antecipado],
    })
    return linhas[linhas["valor"] > 0].reset_index(drop=True)


def inadimplencia_por_faixa(df: pd.DataFrame) -> pd.DataFrame:
    """Contratos inadimplentes segmentados por faixa de dias em atraso.

    Mesma base de "contratos_inadimplentes" do kpis_carteira (total -
    elegíveis): um contrato com QUALQUER venda elegível conta como elegível
    ali, então aqui também é excluído. Dedupe por contrato (maior atraso
    entre as ocorrências pendentes) p/ cada contrato cair em 1 faixa só —
    soma das faixas bate exatamente com o total de inadimplentes do KPI.

    Retorna "contratos" (quantidade) e "valor" (VGV — soma de
    valor_vencido_antes dos contratos da faixa) pra alternar a visualização.
    """
    df = df.copy()
    df["_contrato"] = id_contrato(df)
    _contrato_elegivel = set(df.loc[df["status_elegibilidade"] == "elegivel", "_contrato"])
    _mask = (
        (df["status_elegibilidade"] == "pendente")
        & ~df["_contrato"].isin(_contrato_elegivel)
    )
    _inad = (
        df.loc[_mask, ["_contrato", "dias_atraso"]]
        .groupby("_contrato", as_index=False)["dias_atraso"].max()
    )
    if "valor_vencido_antes" in df.columns:
        _valor = (
            df.loc[_mask, ["_contrato", "valor_vencido_antes"]]
            .groupby("_contrato", as_index=False)["valor_vencido_antes"].sum()
        )
        _inad = _inad.merge(_valor, on="_contrato", how="left")
    else:
        _inad["valor_vencido_antes"] = 0.0
    # dias_atraso==0 num contrato já marcado pendente é gap de dado do bronze
    # (diasatraso nulo), não "sem atraso real" — bucket próprio em vez de
    # descartar silenciosamente (senão a soma das faixas não bate com o KPI).
    bins   = [-1, 0, 30, 60, 90, 180, float("inf")]
    labels = ["Sem atraso informado", "1-30 dias", "31-60 dias", "61-90 dias",
              "91-180 dias", "180+ dias"]
    _inad["faixa"] = pd.cut(_inad["dias_atraso"], bins=bins, labels=labels, right=True)
    return (
        _inad.groupby("faixa", as_index=False, observed=True)
        .agg(contratos=("_contrato", "nunique"), valor=("valor_vencido_antes", "sum"))
    )


def funil_participacao(df: pd.DataFrame) -> pd.DataFrame:
    """Funil real da campanha (CONTEXT 7 — não inventar etapa de cadastro).

    Fluxo: Base total → Elegíveis → Geraram cupons, contado por CONTRATO
    (paradigma do painel — uma venda com vários compradores não deve inflar
    a contagem). A etapa 'Cadastrados' é incluída SOMENTE se trouxer sinal
    próprio (diferente de elegíveis); no mock/dado atual cadastro==elegibilidade,
    então é omitida para não induzir leitura falsa. Geraram cupons = contratos
    elegíveis com cupons_calculados > 0.
    """
    contrato = id_contrato(df)
    base = contrato.nunique()
    elegivel_mask = df["status_elegibilidade"] == "elegivel"
    ele = contrato[elegivel_mask].nunique()

    # Geraram cupons = elegíveis que efetivamente têm cupom (subconjunto dos
    # elegíveis → funil monotônico). Cupom é calculado sobre o recebimento, mas
    # só o elegível concorre, então a etapa final filtra por elegibilidade.
    if "cupons_calculados" in df.columns:
        com_cupom = contrato[
            elegivel_mask & (df["cupons_calculados"].fillna(0) > 0)
        ].nunique()
    else:
        com_cupom = ele

    etapas = ["Base total", "Elegíveis", "Geraram cupons"]
    valores = [base, ele, com_cupom]

    # Inclui 'Cadastrados' só se for sinal independente (≠ elegíveis).
    if "status_cadastro" in df.columns:
        cad = contrato[df["status_cadastro"] == "cadastrado"].nunique()
        if cad != ele:
            etapas.insert(1, "Cadastrados")
            valores.insert(1, cad)

    return pd.DataFrame({"etapa": etapas, "contratos": valores})


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


def novos_clientes(df: pd.DataFrame) -> int:
    """Clientes novos: CPFs cuja PRIMEIRA venda ocorreu após o início da campanha.

    Cliente antigo que comprou de novo pós-campanha não conta — só quem entrou
    na base a partir de CAMPANHA.inicio. Sem data_venda no snapshot → 0.
    """
    if "data_venda" not in df.columns:
        return 0
    primeira = df.groupby("cpf_titular")["data_venda"].min()
    return int((primeira >= pd.Timestamp(CAMPANHA.inicio)).sum())


def novas_vendas_por_dia(df: pd.DataFrame) -> pd.DataFrame:
    """Vendas fechadas a partir do início da campanha, contadas por dia."""
    if "data_venda" not in df.columns:
        return pd.DataFrame({"data": [], "vendas": []})
    novas = df[df["data_venda"] >= pd.Timestamp(CAMPANHA.inicio)]
    if novas.empty:
        return pd.DataFrame({"data": [], "vendas": []})
    return (
        novas.groupby(novas["data_venda"].dt.date)["num_venda"]
        .nunique()
        .rename("vendas")
        .reset_index()
        .rename(columns={"data_venda": "data"})
        .sort_values("data")
    )


def cupons_media_dia_semana(df: pd.DataFrame) -> pd.DataFrame:
    """Média de cupons gerados por dia da semana.

    Soma cupons por data de recebimento e tira a média entre as ocorrências
    de cada dia da semana (2 segundas → média das 2).
    """
    valid = df[df["data_recebimento"].notna()]
    por_dia = valid.groupby(valid["data_recebimento"].dt.date)["cupons_calculados"].sum()
    if por_dia.empty:
        return pd.DataFrame({"dia": [], "cupons": []})
    _nomes = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    media = por_dia.groupby([d.weekday() for d in por_dia.index]).mean()
    return pd.DataFrame({
        "dia": [_nomes[i] for i in media.index],
        "cupons": media.round(0).astype(int).values,
    })


def clientes_por_dia_semana(df: pd.DataFrame) -> pd.DataFrame:
    """Novos clientes × clientes recuperados por dia da semana.

    Novos: CPFs cuja PRIMEIRA venda ocorreu na campanha, no dia da semana da
    venda. Recuperados: CPFs com flag de recuperação, no dia da semana do
    último recebimento (data que regularizou).
    """
    _nomes = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    novos = pd.Series(0, index=range(7))
    if "data_venda" in df.columns:
        primeira = df.groupby("cpf_titular")["data_venda"].min().dropna()
        primeira = primeira[primeira >= pd.Timestamp(CAMPANHA.inicio)]
        novos = primeira.dt.weekday.value_counts().reindex(range(7), fill_value=0)
    rec = pd.Series(0, index=range(7))
    if "classificacao_recebimento" in df.columns and "data_recebimento" in df.columns:
        r = (
            df.loc[df["classificacao_recebimento"] == "recuperacao"]
            .dropna(subset=["data_recebimento"])
            .groupby("cpf_titular")["data_recebimento"].max()
        )
        rec = r.dt.weekday.value_counts().reindex(range(7), fill_value=0)
    return pd.DataFrame({
        "dia": _nomes,
        "novos": novos.values.astype(int),
        "recuperados": rec.values.astype(int),
    })


def clientes_serie_diaria(df: pd.DataFrame, tipo: str = "novos") -> pd.DataFrame:
    """Série diária de clientes (data, quantidade, acumulado).

    tipo="novos": CPFs pela data da 1ª venda na campanha.
    tipo="recuperados": CPFs recuperados pela data do último recebimento
    (dia em que o inadimplente regularizou).
    """
    if tipo == "novos":
        if "data_venda" not in df.columns:
            return pd.DataFrame({"data": [], "quantidade": [], "acumulado": []})
        s = df.groupby("cpf_titular")["data_venda"].min().dropna()
        s = s[s >= pd.Timestamp(CAMPANHA.inicio)]
    else:
        if "classificacao_recebimento" not in df.columns:
            return pd.DataFrame({"data": [], "quantidade": [], "acumulado": []})
        s = (
            df.loc[df["classificacao_recebimento"] == "recuperacao"]
            .dropna(subset=["data_recebimento"])
            .groupby("cpf_titular")["data_recebimento"].max()
        )
    por_dia = s.dt.date.value_counts().sort_index()
    out = pd.DataFrame({"data": por_dia.index, "quantidade": por_dia.values})
    out["acumulado"] = out["quantidade"].cumsum()
    return out


def cupons_por_tipo(df: pd.DataFrame) -> pd.DataFrame:
    """Cupons por tipo de sorteio: Milhão (acumulado) × Casas.

    Query atual traz coluna única cupons_casas; formatos anteriores traziam
    atual/próximo separados. Colunas ausentes são omitidas do resultado.
    """
    if "cupons_casas" in df.columns:
        tipos = [
            ("Milhão (final)", "cupons_calculados"),
            ("Casas (mês)", "cupons_casas"),
        ]
    else:
        tipos = [
            ("Milhão (final)", "cupons_calculados"),
            ("Casas — sorteio atual", "cupons_casas_sorteio_atual"),
            ("Casas — próximo sorteio", "cupons_casas_proximo_sorteio"),
        ]
    rows = [
        {"tipo": nome, "cupons": int(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())}
        for nome, col in tipos
        if col in df.columns
    ]
    return pd.DataFrame(rows)


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
    """Extend kpis_executivos com adimplência, inadimplência e ticket médio.

    total/elegiveis/inadimplentes são por CONTRATO (paradigma do painel);
    clientes_participantes fica reservado pro card inicial de clientes únicos.
    """
    base = kpis_executivos(df)
    total = base["contratos_participantes"]
    elegiveis = base["contratos_elegiveis"]
    valor_vencido = (
        float(df["valor_vencido_antes"].fillna(0).sum())
        if "valor_vencido_antes" in df.columns else 0.0
    )
    return {
        **base,
        "contratos_inadimplentes": total - elegiveis,
        "pct_adimplencia": round(100 * elegiveis / total, 1) if total else 0.0,
        "valor_vencido": valor_vencido,
        "ticket_medio": float(df["valor_total_recebido"].sum()) / total if total else 0.0,
        "cupons_por_contrato_apto": round(base["cupons_calculados"] / elegiveis, 1) if elegiveis else 0.0,
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
            "Pagamento": mes_ano_pt(mes_pag),
            "Sorteio": mes_ano_pt(mes_sor),
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
