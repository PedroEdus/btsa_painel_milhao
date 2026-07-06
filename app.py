"""Painel da Campanha do Milhão — Visão Executiva (CONTEXT 10.2).

Single-page com st.tabs() estilizado. Auto-rotação 10 s entre abas.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from components import (
    banner_premiacao,
    barras,
    card,
    barras_cidades,
    comparativo_carteira,
    donut,
    funil,
    hero,
    linha_temporal,
    medidor,
    mes_ano_pt,
    mes_extenso_pt,
    moeda,
    moeda_compacta,
    nota_regra,
    is_mobile,
    numero,
    page_header,
    percentual,
    progress_adimplencia,
    ranking_cidades_tabela,
    stat_cards,
    tabela,
    tabela_html,
)
from components.ui import autoplay_tabs
from config.settings import CAMPANHA, CUPONS_DISPONIVEIS, REGRA_CUPOM
from data import carregar_dados, ultima_atualizacao
from services import (
    calendario_sorteios,
    cupons_por_cidade,
    cupons_media_dia_semana,
    cupons_por_mes,
    cupons_por_tipo,
    exigir_login_btsa,
    funil_participacao,
    inadimplencia_por_cidade,
    inadimplencia_por_faixa,
    kpis_carteira,
    mes_referencia_atual,
    novos_clientes,
    preparar,
    progresso_campanha,
    recebimento_diario,
    recebimento_mensal,
    recebimento_por_classificacao,
    validar,
)

st.set_page_config(
    page_title="Campanha do Milhão",
    page_icon="assets/logo-sidebar-icon.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Oculta o chrome do Streamlit o mais cedo possível (antes de login/dados) para
# reduzir o flash (FOUC) do badge/manage button que o Streamlit Cloud pinta no
# boot. O CSS completo de tema reaplica isso depois via page_header().
st.markdown(
    """
    <style>
    #MainMenu, footer, header[data-testid="stHeader"],
    [data-testid="stToolbar"], [data-testid="stToolbarActions"],
    [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    [data-testid="stAppDeployButton"], [data-testid="stMainMenuButton"],
    [data-testid="manage-app-button"],
    .viewerBadge_container__1QSob, .viewerBadge_link__1S137,
    .viewerBadge_text__1JaDK,
    [class*="viewerBadge_container"], [class*="viewerBadge_link"],
    [class*="_profileContainer"], [class*="_container_"][class*="profile"] {
        display: none !important; visibility: hidden !important; height: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Gate de acesso: só passa quem logar com conta @btsa.com.br.
exigir_login_btsa()


# Cache fica em data.repository (keyado pela janela 8h/15h BR); preparar() é
# passthrough quando o snapshot já traz cupons calculados pelo Fabric.
df = preparar(carregar_dados())
resultado = validar(df)

page_header(
    "Campanha do Milhão",
    f"{CAMPANHA.empresa} · visão executiva da campanha",
    icon="fa-trophy",
    atualizado_em=ultima_atualizacao(),
)

_mob = is_mobile()  # mobile usa tabelas HTML c/ 1a coluna fixa; desktop usa st.dataframe

if not resultado.ok:
    for erro in resultado.erros:
        st.error(erro)
    st.stop()
for aviso in resultado.avisos:
    st.warning(aviso)

m = kpis_carteira(df)
prog = progresso_campanha()
taxa_cadastro = (100 * m["clientes_cadastrados"] / m["clientes_participantes"]
                 if m["clientes_participantes"] else 0)
_cal = calendario_sorteios()
sorteios_realizados = int((_cal["Status"] == "Realizado").sum())
sorteios_total = len(_cal)
# Média de cupons gerados por dia (dias com recebimento = dias pagantes).
_dias_pagantes = df["data_recebimento"].dt.date.nunique() if "data_recebimento" in df else 0
media_cupons_dia = (m["cupons_calculados"] / _dias_pagantes) if _dias_pagantes else 0

# Auto-rotação 10 s entre abas
autoplay_tabs(intervalo=10)

# Inicializar estados antes das tabs para evitar reset de posição no rerun
if "receb_gran" not in st.session_state:
    st.session_state["receb_gran"] = "Diário"

tabs = st.tabs([
    "Visão Geral",
    "Análise por Cidade",
    "Funil da Campanha",
    "Matriz de Participação",
    "Indicadores Executivos",
    "Exportação",
])

# ── Tab 0 — Visão Geral ───────────────────────────────────────────────────────
with tabs[0]:
    banner_premiacao()
    hero(
        "Arrecadação da campanha",
        moeda(m["valor_total_recebido"]),
        [
            f'<i class="fa-solid fa-ticket"></i> <b>{numero(m["cupons_calculados"])}</b> cupons calculados',
            f'<i class="fa-solid fa-users"></i> <b>{numero(m["clientes_participantes"])}</b> participantes',
            f'<i class="fa-solid fa-city"></i> <b>{numero(df["cidade"].nunique())}</b> cidades participantes',
            f'<i class="fa-solid fa-calendar-check"></i> <b>{sorteios_realizados}/{sorteios_total}</b> sorteios realizados',
            f'<i class="fa-regular fa-clock"></i> <b>{prog["dias_restantes"]}</b> dias restantes',
        ],
    )
    # Regra de cupom + ressalva de cupons calculados ≠ oficiais — nota única na
    # primeira página (CONTEXT item 5 / 14.3). Substitui o selo e o rodapé.
    nota_regra(
        "Regra: 1 cupom a cada R$ 100 de valor principal pago. "
        "<span style='opacity:.5'>|</span> "
        "Os cupons exibidos são <strong>calculados internamente</strong> a partir "
        "dos recebimentos. Não representam os cupons <strong>oficiais</strong> "
        "emitidos pela plataforma externa."
    )
    # Indicadores de abrangência e cadência (ex-chips do hero) — fileira única.
    _pag = df[df["valor_total_recebido"] > 0]
    _n_pagantes = _pag["cpf_titular"].nunique()
    _parcela_media = (
        _pag["valor_total_recebido"].sum() / _n_pagantes if _n_pagantes else 0.0
    )
    _dias_atraso_medio = df.loc[df["dias_atraso"] > 0, "dias_atraso"].mean() or 0
    stat_cards([
        {"label": "Cupons/dia (média)", "valor": numero(round(media_cupons_dia)),
         "icon": "fa-chart-line", "cor": "blue",
         "tooltip": "Média diária de cupons gerados: total de cupons ÷ dias com ao menos um recebimento (dias pagantes)."},
        {"label": "Novos clientes (campanha)", "valor": numero(novos_clientes(df)),
         "icon": "fa-user-plus", "cor": "green",
         "tooltip": "Clientes cuja PRIMEIRA venda ocorreu a partir de 01/07/2026 (início da campanha)."},
        {"label": "Saldo inadimplente hoje", "valor": moeda(m["valor_vencido"]),
         "icon": "fa-triangle-exclamation", "cor": "red",
         "tooltip": "Valor total vencido em aberto na carteira (valor_inadimplencia): saldo que clientes NÃO APTO devem na data do snapshot."},
        {"label": "Dias médios em atraso", "valor": numero(round(_dias_atraso_medio)),
         "icon": "fa-clock", "cor": "amber",
         "tooltip": "Média de dias de atraso entre clientes inadimplentes (dias_atraso > 0) na data do snapshot."},
        {"label": "Parcela média paga", "valor": moeda(_parcela_media),
         "icon": "fa-receipt", "cor": "green",
         "tooltip": "Valor médio pago por pagante: total recebido ÷ número de pagantes (CPFs com recebimento > 0)."},
        {"label": "Valor recuperado", "valor": moeda(m["valor_recuperado"]),
         "icon": "fa-rotate-right", "cor": "amber",
         "tooltip": "Pagamentos de parcelas em atraso recuperados no período. Não disponível nesta versão do snapshot."},
    ])
    # Adimplência × inadimplência consolidadas num único bloco (CONTEXT item 4).
    comparativo_carteira(
        adimplentes=m["clientes_elegiveis"],
        inadimplentes=m["inadimplentes"],
        valor_vencido=m["valor_vencido"],
    )
    progress_adimplencia(m["pct_adimplencia"], meta=70.0)

# ── Tab 1 — Análise por Cidade ────────────────────────────────────────────────
with tabs[1]:
    _n_cid = int(df["cidade"].nunique()) or 1
    stat_cards([
        {"label": "Cidades participantes", "valor": numero(_n_cid),
         "icon": "fa-city", "cor": "blue",
         "tooltip": "Municípios distintos com ao menos um cliente ativo no portfólio."},
        {"label": "Cupons / cidade (média)", "valor": numero(round(m["cupons_calculados"] / _n_cid)),
         "icon": "fa-ticket", "cor": "green",
         "tooltip": "Média de cupons gerados por município: total de cupons ÷ número de cidades participantes."},
        {"label": "Elegíveis / cidade (média)", "valor": numero(round(m["clientes_elegiveis"] / _n_cid)),
         "icon": "fa-circle-check", "cor": "green",
         "tooltip": "Média de clientes APTO por município: total de elegíveis ÷ número de cidades participantes."},
        {"label": "Inadimplentes / cidade (média)", "valor": numero(round(m["inadimplentes"] / _n_cid)),
         "icon": "fa-ban", "cor": "red",
         "tooltip": "Média de clientes NÃO APTO por município: total de inadimplentes ÷ número de cidades participantes."},
    ])
    c1, c2 = st.columns(2)
    with c1:
        por_reg_cup = (
            df.groupby("regional", as_index=False)["cupons_calculados"]
            .sum().sort_values("cupons_calculados", ascending=False)
        )
        barras_cidades(
            por_reg_cup, "regional", "cupons_calculados",
            "Engajamento por regional — cupons gerados",
            "Performance: verde=alto · âmbar=médio · vermelho=baixo",
        )
    with c2:
        por_reg_rec = (
            df.groupby("regional", as_index=False)["valor_total_recebido"]
            .sum().sort_values("valor_total_recebido", ascending=False)
        )
        barras_cidades(
            por_reg_rec, "regional", "valor_total_recebido",
            "Volume de recebimento por regional",
            "Volume financeiro total arrecadado por regional",
            is_monetary=True,
        )
    # Participação por cidade — valores numéricos crus p/ ordenação correta.
    # NumberColumn format="localized" segue o locale pt-BR do browser (1.234,56);
    # format="percent" recebe fração (0-1) e renderiza %.
    _pivc = (df.groupby(["cidade", "status_elegibilidade"])["cpf_titular"]
             .nunique().unstack(fill_value=0)
             .reindex(columns=["elegivel", "pendente"], fill_value=0))
    _totc = df.groupby("cidade").agg(cup=("cupons_calculados", "sum"),
                                     val=("valor_total_recebido", "sum"))
    _clientes = (_pivc["elegivel"] + _pivc["pendente"]).astype(int)
    _tot_clientes = int(_clientes.sum()) or 1
    _tot_cupons = float(_totc["cup"].reindex(_pivc.index).fillna(0).sum()) or 1.0

    resumo_cidade = pd.DataFrame({
        "Cidade": _pivc.index,
        "Clientes": _clientes.values,
        "Repres.": (_clientes / _tot_clientes).values,
        "Elegíveis": _pivc["elegivel"].astype(int).values,
        "Pendentes": _pivc["pendente"].astype(int).values,
        "% Inadimpl.": (_pivc["pendente"] / _clientes.clip(lower=1)).values,
        "Cupons": _totc["cup"].reindex(_pivc.index).fillna(0).astype(int).values,
        "% Cupons": (_totc["cup"].reindex(_pivc.index).fillna(0) / _tot_cupons).values,
        "Valor (R$)": _totc["val"].reindex(_pivc.index).fillna(0).values,
    }).sort_values("Clientes", ascending=False).reset_index(drop=True)

    # Styler: formata a EXIBIÇÃO (R$/pt-BR/%) mas mantém as colunas numéricas
    # por baixo — assim a ordenação por clique continua numérica correta.
    _fmt_pct = lambda v: percentual(v * 100)
    _sty = resumo_cidade.style.format({
        "Clientes": numero, "Elegíveis": numero, "Pendentes": numero, "Cupons": numero,
        "Repres.": _fmt_pct, "% Inadimpl.": _fmt_pct, "% Cupons": _fmt_pct,
        "Valor (R$)": moeda,
    })

    with card("Participação por cidade",
              "Representatividade, engajamento (cupons) e inadimplência por município"):
        if _mob:
            # Mobile: HTML com 1a coluna fixa (sticky). Formata os números aqui
            # já que a tabela HTML usa strings prontas.
            _disp_cid = resumo_cidade.copy()
            for _c in ("Clientes", "Elegíveis", "Pendentes", "Cupons"):
                _disp_cid[_c] = _disp_cid[_c].map(numero)
            for _c in ("Repres.", "% Inadimpl.", "% Cupons"):
                _disp_cid[_c] = _disp_cid[_c].map(_fmt_pct)
            _disp_cid["Valor (R$)"] = _disp_cid["Valor (R$)"].map(moeda)
            tabela_html(_disp_cid)
        else:
            st.dataframe(
                _sty,
                hide_index=True,
                height=420,
                width="stretch",
                column_config={
                    "Cidade": st.column_config.TextColumn(
                        "Cidade", pinned=True, width="large"),
                    "Clientes": st.column_config.NumberColumn(
                        "Clientes", width="small",
                        help="Total de clientes únicos (CPF) com venda ativa na cidade."),
                    "Repres.": st.column_config.NumberColumn(
                        "Repres.", width="small",
                        help="Representatividade: participação da cidade no total de clientes do portfólio."),
                    "Elegíveis": st.column_config.NumberColumn(
                        "Elegíveis", width="small",
                        help="Clientes APTO na cidade — sem inadimplência, participam dos sorteios."),
                    "Pendentes": st.column_config.NumberColumn(
                        "Pendentes", width="small",
                        help="Clientes NÃO APTO na cidade — com parcelas vencidas."),
                    "% Inadimpl.": st.column_config.NumberColumn(
                        "% Inadimpl.", width="small",
                        help="Inadimplência da cidade: pendentes ÷ total de clientes da cidade."),
                    "Cupons": st.column_config.NumberColumn(
                        "Cupons", width="small",
                        help="Cupons gerados pelos clientes da cidade (1 cupom por R$ 100 recebido)."),
                    "% Cupons": st.column_config.NumberColumn(
                        "% Cupons", width="small",
                        help="Efeito da cidade: participação no total de cupons gerados na campanha."),
                    "Valor (R$)": st.column_config.NumberColumn(
                        "Valor (R$)",
                        help="Soma do valor total recebido pelos clientes da cidade."),
                },
            )

# ── Tab 2 — Funil da Campanha ─────────────────────────────────────────────────
with tabs[2]:
    stat_cards([
        {"label": "Total participantes", "valor": numero(m["clientes_participantes"]),
         "icon": "fa-users", "cor": "green",
         "tooltip": "Total de clientes únicos (CPF) com venda ativa no portfólio, independente de elegibilidade."},
        {"label": "Elegíveis p/ sorteio", "valor": numero(m["clientes_elegiveis"]),
         "icon": "fa-circle-check", "cor": "green",
         "tooltip": "Clientes com status APTO: sem inadimplência no mês de referência, participam automaticamente dos sorteios."},
        {"label": "Inadimplentes", "valor": numero(m["inadimplentes"]),
         "icon": "fa-ban", "cor": "red",
         "tooltip": "Clientes com status NÃO APTO: possuem parcelas vencidas e não participam dos sorteios mensais."},
        {"label": "Cupons calculados", "valor": numero(m["cupons_calculados"]),
         "icon": "fa-ticket", "cor": "blue",
         "tooltip": "Gerado pelo Fabric: soma de cupons por venda. Regra: 1 cupom a cada R$100 de pagamento válido no mês de referência."},
        {"label": "Sorteios realizados", "valor": f"{sorteios_realizados} / {sorteios_total}",
         "icon": "fa-trophy", "cor": "amber",
         "tooltip": "Sorteios já realizados conforme o calendário da campanha (jul/2026 a jan/2027)."},
        {"label": "Valor recuperado", "valor": moeda(m["valor_recuperado"]),
         "icon": "fa-rotate-right", "cor": "green",
         "tooltip": "Pagamentos de parcelas em atraso recuperados no período. Não disponível nesta versão do snapshot."},
    ])
    @st.fragment
    def _bloco_recebimento():
        # Fragment isola o rerun do toggle Diário/Mensal — não reseta as st.tabs.
        with card("Recebimento acumulado", "Caixa entrando ao longo da campanha"):
            _gran = st.radio(
                "Granularidade", ["Diário", "Mensal"],
                horizontal=True, label_visibility="collapsed",
                key="receb_gran",
            )
            if _gran == "Diário":
                linha_temporal(recebimento_diario(df), "data", "acumulado",
                               skip_card=True)
            else:
                _men = recebimento_mensal(df).copy()
                _men["data"] = _men["data"].apply(mes_ano_pt)
                barras(_men, "data", "valor_total_recebido", "",
                       is_monetary=True, skip_card=True)

    c1, c2 = st.columns(2)
    with c1:
        _bloco_recebimento()
    with c2:
        funil(funil_participacao(df), "clientes", "etapa", "Funil de participação",
              "Do recebimento à elegibilidade")
    c3, c4 = st.columns(2)
    with c3:
        _cupons_mes = cupons_por_mes(df).copy()
        _cupons_mes["mes_referencia"] = _cupons_mes["mes_referencia"].map(mes_extenso_pt)
        barras(_cupons_mes, "mes_referencia", "cupons_calculados",
               "Cupons por mês (concorrem ao sorteio do mês)",
               "Mês atual destacado · acumulado concorre ao prêmio final de R$ 1 milhão",
               destaque=mes_extenso_pt(mes_referencia_atual()))
    with c4:
        donut(recebimento_por_classificacao(df), "classificacao_recebimento",
              "valor_total_recebido", "Origem do recebimento", "Normal vs recuperação",
              cores={"normal": "#2a9d45", "recuperacao": "#f59e0b"})

# ── Tab 3 — Matriz de Participação ────────────────────────────────────────────
with tabs[3]:
    # Pivot: status_elegibilidade vira 2 colunas (Elegíveis × Pendentes) por obra.
    _piv = (df.groupby(["obra", "status_elegibilidade"])["cpf_titular"]
            .nunique().unstack(fill_value=0))
    _tot = df.groupby("obra").agg(cup=("cupons_calculados", "sum"),
                                  val=("valor_total_recebido", "sum"))
    _zero_obra = pd.Series(0, index=_piv.index)
    resumo_obra = pd.DataFrame({
        "Obra": _piv.index,
        "Elegíveis": [numero(v) for v in _piv.get("elegivel", _zero_obra)],
        "Pendentes": [numero(v) for v in _piv.get("pendente", _zero_obra)],
        "Cupons": [numero(v) for v in _tot["cup"].reindex(_piv.index).fillna(0)],
        "Valor": [moeda(v) for v in _tot["val"].reindex(_piv.index).fillna(0)],
    })
    _tc = (
        df.groupby(["nome_cliente", "obra", "status_elegibilidade"], as_index=False)
        .agg(cupons=("cupons_calculados", "sum"), valor=("valor_total_recebido", "sum"))
        .sort_values("cupons", ascending=False)
        .head(15)
        .reset_index(drop=True)
    )
    top_clientes = pd.DataFrame({
        "Cliente": _tc["nome_cliente"],
        "Obra": _tc["obra"],
        "status_elegibilidade": _tc["status_elegibilidade"],  # nome cru p/ badge
        "Cupons": [numero(v) for v in _tc["cupons"]],
        "Valor": [moeda(v) for v in _tc["valor"]],
    })
    top_clientes.index = top_clientes.index + 1
    c1, c2 = st.columns([1, 1.5])
    with c1:
        tabela(resumo_obra, "Resumo por obra e elegibilidade",
               "Elegíveis × pendentes por obra", status=True, altura=580)
    with c2:
        tabela(top_clientes, "Ranking de 15 clientes por cupons",
               "Clientes com maior volume de cupons gerados", status=True, altura=580)

# ── Tab 4 — Indicadores Executivos ───────────────────────────────────────────
with tabs[4]:
    stat_cards([
        {"label": "Ticket médio (por venda)", "valor": moeda(m["ticket_medio"]),
         "icon": "fa-file-invoice-dollar", "cor": "green",
         "tooltip": "Valor médio recebido por venda: total recebido ÷ número de vendas únicas ativas no período."},
        {"label": "Cupons / cliente apto", "valor": str(m["cupons_por_cliente_apto"]),
         "icon": "fa-ticket", "cor": "blue",
         "tooltip": "Média de cupons gerados por cliente elegível: total de cupons ÷ total de clientes com status APTO."},
        {"label": "Taxa de elegibilidade", "valor": f"{taxa_cadastro:.1f}%",
         "icon": "fa-user-check", "cor": "amber",
         "tooltip": "% de clientes com status APTO sobre o total de participantes únicos (CPF) do portfólio."},
        {"label": "Novos clientes (campanha)", "valor": numero(novos_clientes(df)),
         "icon": "fa-user-plus", "cor": "blue",
         "tooltip": "Clientes cuja PRIMEIRA venda ocorreu a partir de 01/07/2026 (início da campanha). Cliente antigo que comprou de novo não conta."},
        {"label": "Valor recuperado", "valor": moeda(m["valor_recuperado"]),
         "icon": "fa-rotate-right", "cor": "green",
         "tooltip": "Pagamentos de parcelas em atraso recuperados no período. Não disponível nesta versão do snapshot."},
    ])
    c1, c2 = st.columns([1, 1])
    with c1:
        cupons_realizados = int(m["cupons_calculados"])
        cupons_limite = CUPONS_DISPONIVEIS or int(
            (m["valor_total_recebido"] + m["valor_vencido"]) / REGRA_CUPOM.valor_por_cupom
        )
        _pct_cupons = 100 * cupons_realizados / max(cupons_limite, 1)
        medidor(_pct_cupons, 100,
                "Aproveitamento de cupons",
                "Quanto dos cupons possíveis já foi gerado",
                sufixo="%", numformat=".1f",
                nota=(
                    f"<b>{numero(cupons_realizados)}</b> cupons já gerados de "
                    f"<b>{numero(cupons_limite)}</b> possíveis.<br>"
                    "<b>Potencial</b> = (valor recebido + saldo a receber da carteira) "
                    "÷ R$ 100 por cupom. Mostra o quanto a campanha pode crescer "
                    "conforme a carteira é paga."
                ))
    with c2:
        barras(inadimplencia_por_faixa(df), "faixa", "clientes",
               "Inadimplência por faixa de atraso",
               "Clientes não aptos segmentados por dias em atraso",
               cor="#ef4444")

    c3, c4 = st.columns([1, 1])
    with c3:
        barras(cupons_media_dia_semana(df), "dia", "cupons",
               "Média de cupons por dia da semana",
               "Cupons gerados em média em cada dia da semana (por data de recebimento)")
    with c4:
        barras(cupons_por_tipo(df), "tipo", "cupons",
               "Cupons por sorteio",
               "Milhão (acumula até o final) × Casas (concorrem no mês)")

# ── Tab 5 — Exportação ───────────────────────────────────────────────────────
with tabs[5]:
    _df_exp = df.copy()
    if "empresa_codigo" not in _df_exp.columns:
        _df_exp["empresa_codigo"] = _df_exp["codempresa"].astype(str)
    _mat = (
        _df_exp.groupby(["regional", "cidade", "empresa_codigo", "obra_nome"], as_index=False)
        .agg(
            empresa_nome=("empresa", "first"),
            clientes=("cpf_titular", "nunique"),
            elegiveis=("status_elegibilidade", lambda s: (s == "elegivel").sum()),
            inadimplentes=("status_elegibilidade", lambda s: (s == "pendente").sum()),
            cupons=("cupons_calculados", "sum"),
            recebido=("valor_total_recebido", "sum"),
        )
        .sort_values(["regional", "cidade", "empresa_codigo", "obra_nome"])
        .reset_index(drop=True)
    )

    _csv_mat = _mat[[
        "regional", "cidade", "empresa_codigo", "empresa_nome", "obra_nome",
        "clientes", "elegiveis", "inadimplentes", "cupons", "recebido",
    ]].rename(columns={
        "regional": "Regional", "cidade": "Cidade", "empresa_codigo": "Cód. Empresa",
        "empresa_nome": "Empresa", "obra_nome": "Produto", "clientes": "Clientes",
        "elegiveis": "Elegíveis", "inadimplentes": "Inadimplentes",
        "cupons": "Cupons", "recebido": "Recebido (R$)",
    })
    def _brl(v): return "R$ {:,.2f}".format(v).replace(",", "X").replace(".", ",").replace("X", ".")
    def _num(v): return "{:,}".format(int(v)).replace(",", ".")

    # Drill-down nativo via <details>/<summary> — sem JS, sem iframe. st.markdown
    # renderiza inline (largura total) e o DOMPurify do Streamlit preserva
    # <details>/<summary>/style (só remove <script>/onclick). Cada linha é um
    # grid de 6 colunas, então as métricas alinham entre todos os níveis. A seta
    # é &#9654; (HTML entity p/ não quebrar no cp1252) e gira via CSS no [open].
    def _cells(s):
        return (
            f'<span class="c">{_num(s.clientes)}</span>'
            f'<span class="c">{_num(s.elegiveis)}</span>'
            f'<span class="c">{_num(s.inadimplentes)}</span>'
            f'<span class="c">{_num(s.cupons)}</span>'
            f'<span class="c">{_brl(s.recebido)}</span>'
        )

    _rows = ""
    for _reg, _g1 in _mat.groupby("regional"):
        _r = _g1[["clientes","elegiveis","inadimplentes","cupons","recebido"]].sum()
        _rows += (f'<details class="lv0"><summary>'
                  f'<span class="nm"><span class="arr">&#9654;</span> <b>{_reg}</b></span>{_cells(_r)}</summary>')
        for _cid, _g2 in _g1.groupby("cidade"):
            _c = _g2[["clientes","elegiveis","inadimplentes","cupons","recebido"]].sum()
            _rows += (f'<details class="lv1"><summary>'
                      f'<span class="nm i1"><span class="arr">&#9654;</span> {_cid}</span>{_cells(_c)}</summary>')
            for _emp, _g3 in _g2.groupby("empresa_codigo"):
                _e = _g3[["clientes","elegiveis","inadimplentes","cupons","recebido"]].sum()
                # Snapshot novo traz nomeempresa; no antigo "empresa" é a
                # constante "Brasil Terrenos" p/ todas → cai no código.
                _emp_nome = str(_g3["empresa_nome"].iloc[0])
                if _emp_nome in ("", "nan", "Brasil Terrenos"):
                    _emp_nome = f"Empresa {_emp}"
                _rows += (f'<details class="lv2"><summary>'
                          f'<span class="nm i2"><span class="arr">&#9654;</span> {_emp_nome}</span>{_cells(_e)}</summary>')
                for _, _row in _g3.iterrows():
                    _rows += (f'<div class="lv3 leaf">'
                              f'<span class="nm i3" tabindex="0">{_row["obra_nome"]}</span>{_cells(_row)}</div>')
                _rows += '</details>'
            _rows += '</details>'
        _rows += '</details>'

    # IMPORTANTE: o <style> vai em um st.markdown SEPARADO do conteúdo. O
    # Streamlit colapsa p/ width:0 qualquer stElementContainer que :has(.stMarkdown
    # style) — tratando markdown-com-style como injetor de CSS puro. Misturar
    # style+tabela no mesmo markdown zeraria a largura da tabela.
    #
    # Mobile usa o mesmo padrão das outras tabelas (.mtbl em ui.py): 1a coluna
    # fixa via position:sticky (o "pinned" do st.dataframe não trava em scroll
    # touch), colunas com largura mínima fixa p/ sempre estourar a tela →
    # sempre dá p/ arrastar, fonte/padding menores, área de scroll com altura
    # máxima de viewport (72vh) igual ao .mtbl-wrap.
    _hx_mobile_css = """
  .hx-scroll{max-height:72vh;-webkit-overflow-scrolling:touch;touch-action:pan-x pan-y}
  .hx-head,.hx summary,.hx .leaf{
    grid-template-columns:148px repeat(4,68px) 104px;
    width:max-content;min-width:calc(100% + 140px)}
  .hx-head>span,.hx summary>span,.hx .leaf>span{padding:7px 8px;font-size:10.5px}
  .hx{font-size:10.5px}
  .hx .nm{position:sticky;left:0;z-index:2;background:#fff;box-shadow:1px 0 0 #e6e8eb}
  .hx-head{z-index:3}
  .hx-head .nm{z-index:4;background:#f5f6f8}
  /* Toque no nome do produto (folha) quebra o texto DENTRO da largura da
     coluna (sem invadir as colunas vizinhas) — a linha toda cresce em
     altura (grid sem altura fixa) e os numeros continuam visiveis ao lado,
     sem precisar arrastar. */
  .hx .leaf .nm.i3{cursor:pointer}
  .hx .leaf .nm.i3:focus{white-space:normal;overflow-wrap:break-word;
    overflow:visible;align-self:stretch;display:flex;align-items:center;
    outline:2px solid #9499a3;z-index:5;background:#fff}
""" if _mob else ""
    st.markdown(f"""
<style>
  .hx{{border:1px solid #e6e8eb;border-radius:6px;font-size:13px;background:#fff;color:#232329}}
  .hx-scroll{{max-height:600px;overflow:auto;border-radius:6px;background:#fff}}
  .hx-head,.hx summary,.hx .leaf{{
    display:grid;grid-template-columns:minmax(260px,1.8fr) repeat(5,1fr);
    align-items:center;column-gap:0;border-bottom:1px solid #e6e8eb}}
  /* celulas: separador vertical entre colunas (igual st.dataframe) */
  .hx-head>span,.hx summary>span,.hx .leaf>span{{
    padding:11px 14px;border-right:1px solid #e6e8eb;
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
  .hx-head>span:last-child,.hx summary>span:last-child,.hx .leaf>span:last-child{{border-right:none}}
  .hx-head{{background:#f5f6f8;color:#6b6b74;font-weight:600;position:sticky;top:0;z-index:1}}
  .hx-head .c,.hx summary .c,.hx .leaf .c{{text-align:left;font-variant-numeric:tabular-nums}}
  .hx .nm{{color:#232329}}
  .hx-head .nm{{color:#6b6b74}}
  /* card branco (so o container do card: tem a linha de colunas titulo+botao E
     a tabela .hx). NAO usar :has(.hx) puro — casaria todo ancestral, inclusive o
     bloco principal do app, pintando barra branca em todas as abas. */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"]):has(.hx){{background:#fff;padding:8px 12px 40px}}
  [data-testid="stElementContainer"]:has([data-testid="stDownloadButton"]){{width:100%}}
  [data-testid="stDownloadButton"]{{display:flex;justify-content:flex-end;width:100%}}
  .hx summary{{cursor:pointer;list-style:none;background:#fff}}
  .hx summary::-webkit-details-marker{{display:none}}
  .hx details.lv0>summary{{font-weight:600}}
  .hx details.lv1>summary{{font-weight:500}}
  .hx .leaf{{background:#fff}}
  .hx summary:hover,.hx .leaf:hover{{background:#f6f9fd}}
  .hx .arr{{display:inline-block;transition:transform .15s;font-size:10px;color:#9499a3}}
  .hx details[open]>summary .arr{{transform:rotate(90deg)}}
  .hx .nm.i1{{padding-left:32px}} .hx .nm.i2{{padding-left:50px}} .hx .nm.i3{{padding-left:68px}}
  {_hx_mobile_css}
</style>
""", unsafe_allow_html=True)
    with card():
        _hc1, _hc2 = st.columns([5, 1], vertical_alignment="center")
        _hc1.markdown(
            '<div class="card-title">Matriz de Exportação</div>'
            '<div class="card-sub">Detalhamento por regional, cidade, empresa e produto</div>',
            unsafe_allow_html=True,
        )
        # Fragment isola o rerun do clique — sem ele o download_button
        # rerodava o script inteiro e o st.tabs voltava pra primeira aba.
        @st.fragment
        def _botao_csv():
            st.download_button("Baixar CSV",
                               _csv_mat.to_csv(index=False, sep=";", decimal=",").encode("utf-8"),
                               "matriz_exportacao.csv", "text/csv")
        with _hc2:
            _botao_csv()
        st.markdown(f"""
<div class="hx"><div class="hx-scroll">
  <div class="hx-head">
    <span class="nm">Regional / Cidade / Empresa / Produto</span>
    <span class="c">Clientes</span><span class="c">Elegíveis</span>
    <span class="c">Inadimpl.</span><span class="c">Cupons</span><span class="c">Recebido (R$)</span>
  </div>
  {_rows}
</div></div>
""", unsafe_allow_html=True)

# ── Rodapé global (todas as abas) ─────────────────────────────────────────────
st.markdown(
    """
    <div style="text-align:center;color:#9499a3;font-size:12px;
                padding:18px 0 8px;margin-top:24px;
                border-top:1px solid #e8e9ec;">
      Painel desenvolvido pelo núcleo de dados Brasil Terrenos
    </div>
    """,
    unsafe_allow_html=True,
)
