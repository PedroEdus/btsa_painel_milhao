"""Componentes visuais (CONTEXT 10). Espelham os componentes do CGID:
page-header, stat-cards, cards com header, badges. Render via HTML + CSS de
components.theme (Font Awesome p/ ícones).
"""

from __future__ import annotations

import base64
import os
from contextlib import contextmanager, nullcontext as _null_ctx
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from components.format import (
    mes_ano_pt,
    moeda as _moeda,
    numero as _numero,
    pct_valor,
    percentual,
)
from components.theme import ACENTO, BRAND, FONT, PALETAS, RADIUS, SEMANTIC, aplicar_tema
from config.settings import CACHE_TTL_SEGUNDOS

_ASSETS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
LOGO_CLARA = os.path.join(_ASSETS, "logo_preta.png")     # fundo claro
LOGO_ESCURA = os.path.join(_ASSETS, "logo_branca.png")   # fundo escuro


def _b64(caminho: str) -> str:
    with open(caminho, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _logo_path() -> str | None:
    logo = LOGO_CLARA
    if not os.path.exists(logo):
        logo = LOGO_CLARA if os.path.exists(LOGO_CLARA) else LOGO_ESCURA
    return logo if os.path.exists(logo) else None


def tema_toggle() -> None:
    pass


def logo() -> None:
    """Logo Brasil Terrenos no topo da sidebar."""
    cam = _logo_path()
    if not cam:
        return
    st.sidebar.markdown(
        f"""<div style="display:flex;justify-content:center;padding:6px 4px 14px;">
        <img src="data:image/png;base64,{_b64(cam)}" style="width:min(180px,80%);height:auto;">
        </div>""",
        unsafe_allow_html=True,
    )


_MOEDAS = ["💰", "🪙", "💵", "💲", "🤑", "💴"]


def _chuva_moedas(n: int = 22) -> str:
    """Spans de moedas/cifrões caindo, espalhados de forma determinística."""
    spans = []
    for i in range(n):
        left = (i * 37 + 11) % 100              # espalha horizontal
        dur = 1.6 + (i % 5) * 0.35              # 1.6–3.0s
        delay = (i % 7) * 0.22                  # escalonado
        size = 20 + (i % 4) * 9                 # 20–47px
        emoji = _MOEDAS[i % len(_MOEDAS)]
        spans.append(
            f'<span class="coin" style="left:{left}%;'
            f'animation-duration:{dur:.2f}s;animation-delay:{delay:.2f}s;'
            f'font-size:{size}px;">{emoji}</span>'
        )
    return "".join(spans)


def splash() -> None:
    """Animação lúdica de abertura: chuva de moedas + barras de ouro (CONTEXT 10.1).

    Só toca em CARGA REAL da página (sessão nova) — não em reruns/filtros.
    O auto-reload de 10 min recria a sessão, então toca a cada atualização.
    """
    if st.session_state.get("_splashed"):
        return
    st.session_state["_splashed"] = True
    # fundo escuro → logo branca
    cam = LOGO_ESCURA if os.path.exists(LOGO_ESCURA) else _logo_path()
    img = f'<img src="data:image/png;base64,{_b64(cam)}">' if cam and os.path.exists(cam) else ""
    cifras = "".join(
        f'<span style="animation-delay:{i * 0.15:.2f}s">$</span>' for i in range(6)
    )
    st.markdown(
        f"""
        <div class="splash">
          <div class="splash-rain">{_chuva_moedas()}</div>
          {img}
          <div class="emblem-wrap">
            <div class="sunburst"></div>
            <span class="clover cTop">🍀</span>
            <span class="clover cBot">🍀</span>
            <div class="badge">
              <div class="emblem-top">Campanha do</div>
              <div class="emblem-milhao">MILHÃO</div>
              <div class="emblem-plate">BRASIL TERRENOS</div>
            </div>
          </div>
          <div class="cifra-load">{cifras}</div>
          <div class="splash-cap">Atualizando dados da campanha…</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def boot_tema() -> None:
    """Injeta um <style> PERSISTENTE no <head> do documento pai com o bg do tema.

    Resolve o flash branco na navegação: o style do tema normal fica no <body> e
    é removido/recriado a cada troca de página (gap de 1 frame = flash). Este, no
    <head>, sobrevive à navegação client-side → o 1º paint da nova página já vem
    na cor certa.
    """
    P = PALETAS["claro"]
    bg, sb = P["bg"], P["sidebar_bg"]
    components.html(
        f"""<script>
        const d = window.parent.document;
        let el = d.getElementById('boot-theme');
        if(!el){{ el=d.createElement('style'); el.id='boot-theme'; d.head.appendChild(el); }}
        el.textContent =
          'html,body,.stApp,[data-testid=\"stApp\"],[data-testid=\"stAppViewContainer\"],'
          + '[data-testid=\"stMain\"],header[data-testid=\"stHeader\"]'
          + '{{background-color:{bg} !important;}}'
          + '[data-testid=\"stSidebar\"],[data-testid=\"stSidebarContent\"]'
          + '{{background-color:{sb} !important;}}';
        </script>""",
        height=0,
    )


def auto_refresh(segundos: int = CACHE_TTL_SEGUNDOS) -> None:
    """Recarrega a página inteira a cada `segundos` (CONTEXT 9 — near real-time).

    Full reload → cache expira → dados novos + splash toca de novo.
    """
    components.html(
        f"<script>setTimeout(function(){{window.parent.location.reload();}}, {segundos * 1000});</script>",
        height=0,
    )


def page_header(
    titulo: str, subtitulo: str = "", icon: str = "fa-chart-line",
    atualizado_em: datetime | None = None,
) -> None:
    """Cabeçalho de página (.ph do CGID). Aplica tema + logo na sidebar."""
    _show_counter[0] = 0
    tema_toggle()
    boot_tema()
    aplicar_tema()
    splash()
    auto_refresh()

    # TV mode button — puro JS, sem rerun Streamlit; ícone muda pause↔play
    tv_onclick = (
        "(function(btn){"
        "var P=window.parent;"
        "var on=P._tvEnabled!==false;"
        "if(on){"
          "P._tvEnabled=false;"
          "if(P._stopAp)P._stopAp();"
          "btn.querySelector('i').className='fa-solid fa-play';"
          "btn.title='Ativar modo TV';"
        "}else{"
          "P._tvEnabled=true;"
          "if(P._startAp)P._startAp();"
          "btn.querySelector('i').className='fa-solid fa-pause';"
          "btn.title='Desativar modo TV';"
        "}"
        "})(this)"
    )
    tv_btn = (
        f'<button class="ph-tema-btn" title="Ativar modo TV" onclick="{tv_onclick}">'
        f'<i class="fa-solid fa-play"></i></button>'
    )

    stamp = ""
    if atualizado_em:
        stamp = (
            f'<span class="ph-stamp"><i class="fa-regular fa-clock"></i>'
            f'Atualizado {atualizado_em:%d/%m/%Y %H:%M}</span>'
        )
    sub = f'<div class="ph-sub">{subtitulo}</div>' if subtitulo else ""

    # logo Brasil Terrenos embutida (base64) — sem depender de path em produção
    logo_tag = ""
    logo_path = os.path.join(_ASSETS, "logo_preta.png")
    if os.path.exists(logo_path):
        logo_b64 = _b64(logo_path)
        logo_tag = (
            f'<div class="ph-logo-box">'
            f'<img src="data:image/png;base64,{logo_b64}" class="ph-logo-img" alt="Brasil Terrenos">'
            f'</div>'
            f'<div class="ph-sep"></div>'
        )

    st.markdown(
        f"""
        <div class="ph">
          <div class="ph-l">
            {logo_tag}
            <div><div class="ph-title">{titulo}</div>{sub}</div>
          </div>
          <div class="ph-actions">{tv_btn}{stamp}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def autoplay_tabs(intervalo: int = 10, iniciar_ativo: bool = False) -> None:
    """Autoplay de abas + botão TV (pause/play). Timer via parent window.

    iniciar_ativo=False (padrão): modo TV começa DESLIGADO ao abrir o app;
    usuário liga no botão do header.
    """
    js_default = "true" if iniciar_ativo else "false"
    components.html(
        f"""<script>
        (function() {{
          var P = window.parent;

          // Estado inicial do modo TV (uma vez por sessão da janela).
          if (P._tvInit === undefined) {{
            P._tvInit = true;
            P._tvEnabled = {js_default};
          }}

          // ── Barra de progresso ──────────────────────────────────────────
          var bar = P.document.getElementById('_ap_bar');
          if (!bar) {{
            bar = P.document.createElement('div');
            bar.id = '_ap_bar';
            bar.style.cssText = [
              'position:fixed','top:0','left:0','height:3px',
              'background:{BRAND["500"]}','width:0%','z-index:99999',
              'border-radius:0 3px 3px 0',
              'box-shadow:0 0 8px rgba(42,125,50,.5)',
              'pointer-events:none','transition:none'
            ].join(';');
            P.document.body.appendChild(bar);
          }}

          function resetBar() {{
            bar.style.transition = 'none'; bar.style.width = '0%';
            bar.getBoundingClientRect();
            bar.style.transition = 'width {intervalo}s linear';
            bar.style.width = '100%';
          }}

          function nextTab() {{
            var tabs = P.document.querySelectorAll('button[data-baseweb="tab"]');
            if (!tabs.length) return;
            var cur = Array.from(tabs).findIndex(function(t) {{
              return t.getAttribute('aria-selected') === 'true';
            }});
            tabs[(cur + 1) % tabs.length].click();
            resetBar();
          }}

          P._stopAp = function() {{
            clearInterval(P._apTimer); P._apTimer = null; P._apRunning = false;
            bar.style.transition = 'none'; bar.style.width = '0%';
          }};

          P._startAp = function() {{
            if (P._apRunning) return;
            P._apRunning = true;
            bar.style.opacity = '1';
            resetBar();
            P._apTimer = setInterval(nextTab, {intervalo * 1000});
          }};

          if (P._tvEnabled !== false && !P._apRunning) {{
            P._apRunning = true;
            resetBar();
            P._apTimer = setInterval(nextTab, {intervalo * 1000});
          }}

          // ── Handlers dos botões header (onclick stripado pelo Streamlit) ──
          function attachHandlers() {{
            var btns = Array.from(P.document.querySelectorAll('.ph-tema-btn'));

            // Botão TV
            var tvBtn = btns.find(function(b) {{ return b.title.indexOf('TV') !== -1; }});
            if (tvBtn && !tvBtn._h) {{
              tvBtn._h = true;
              tvBtn.style.cursor = 'pointer';
              tvBtn.addEventListener('click', function() {{
                var on = P._tvEnabled !== false;
                if (on) {{
                  P._tvEnabled = false;
                  if (P._stopAp) P._stopAp();
                  tvBtn.querySelector('i').className = 'fa-solid fa-play';
                  tvBtn.title = 'Ativar modo TV';
                }} else {{
                  P._tvEnabled = true;
                  if (P._startAp) P._startAp();
                  tvBtn.querySelector('i').className = 'fa-solid fa-pause';
                  tvBtn.title = 'Desativar modo TV';
                }}
              }});
            }}

            // Mantém ícone/título do botão em sincronia com o estado atual.
            if (tvBtn) {{
              var _on = P._tvEnabled !== false;
              tvBtn.querySelector('i').className = _on ? 'fa-solid fa-pause' : 'fa-solid fa-play';
              tvBtn.title = _on ? 'Desativar modo TV' : 'Ativar modo TV';
            }}

          }}

          attachHandlers();
          setTimeout(attachHandlers, 600);
          setTimeout(attachHandlers, 1500);
        }})();
        </script>""",
        height=0,
    )


_STAT_TIP_CSS = """
<style>
.stat-tip{display:inline-flex;align-items:center;justify-content:center;
  width:14px;height:14px;border-radius:50%;background:#e2e8f0;color:#64748b;
  font-size:8px;cursor:help;position:relative;margin-left:5px;
  vertical-align:middle;flex-shrink:0;line-height:1;}
.stat-tip::after{content:attr(data-tip);position:absolute;bottom:calc(100% + 8px);
  left:50%;transform:translateX(-50%);background:#1e293b;color:#f8fafc;
  font-size:11px;line-height:1.5;padding:8px 11px;border-radius:7px;width:230px;
  white-space:normal;z-index:9999;display:none;text-align:left;font-weight:400;
  box-shadow:0 4px 14px rgba(0,0,0,.28);}
.stat-tip::before{content:'';position:absolute;bottom:calc(100% + 2px);left:50%;
  transform:translateX(-50%);border:5px solid transparent;
  border-top-color:#1e293b;z-index:9999;display:none;}
.stat-tip:hover::after,.stat-tip:hover::before{display:block;}
/* Valor em largura total + ícone pequeno embaixo (cabe valores longos) */
.stat-card .stat-val{font-size:25px;line-height:1.15;word-break:break-word;}
.stat-foot{display:flex;align-items:center;gap:8px;margin-top:8px;}
.stat-ico-sm{display:inline-flex;align-items:center;justify-content:center;
  width:24px;height:24px;border-radius:7px;font-size:12px;flex-shrink:0;
  background:#eef6f0;color:#2a9d45;}
.stat-ico-sm.blue{background:#eaf1fe;color:#2563eb;}
.stat-ico-sm.amber{background:#fef6e7;color:#b45309;}
.stat-ico-sm.red{background:#fdecec;color:#dc2626;}
.stat-foot .stat-label{margin:0;}
</style>
"""


def stat_cards(cards: list[dict]) -> None:
    """Grade de KPI stat-cards (.stat-card do CGID).

    Cada card: {label, valor, icon (FA), cor (green|amber|red|blue), trend?, tooltip?}.
    tooltip: texto exibido no ícone ? ao passar o mouse — explica o cálculo.
    """
    # CSS do tooltip em chamada separada — misturar <style> com as divs no mesmo
    # bloco markdown faz o sanitizer do Streamlit engolir os cards.
    st.markdown(_STAT_TIP_CSS, unsafe_allow_html=True)
    html = ['<div class="stats-row">']
    for c in cards:
        cor = c.get("cor", "green")
        tip = c.get("tooltip", "")
        tip_html = ""
        if tip:
            tip_esc = tip.replace('"', "&quot;")
            tip_html = (
                f'<span class="stat-tip" data-tip="{tip_esc}">?</span>'
            )
        trend = ""
        if c.get("trend"):
            t = c["trend"]
            html_t = t.get("tipo", "neutral")
            ico = t.get("icon", "fa-minus")
            trend = (
                f'<div class="stat-trend {html_t}">'
                f'<i class="fa-solid {ico}"></i>{t["texto"]}</div>'
            )
        html.append(
            f'<div class="stat-card {cor}">'
            f'<div class="stat-val">{c["valor"]}</div>'
            f'<div class="stat-foot">'
            f'<span class="stat-ico-sm {cor}"><i class="fa-solid {c.get("icon","fa-coins")}"></i></span>'
            f'<span class="stat-label">{c["label"]}{tip_html}</span>'
            f'</div>{trend}'
            f'</div>'
        )
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)


def comparativo_carteira(
    adimplentes: int, inadimplentes: int, valor_vencido: float = 0.0,
) -> None:
    """Bloco único comparando adimplentes × inadimplentes (CONTEXT item 4).

    Consolida os dois stat-cards antes separados, com proporção visual e % da
    carteira. Percentuais via cálculo seguro (sem divisão por zero).
    """
    total = adimplentes + inadimplentes
    pct_ok = pct_valor(adimplentes, total)
    pct_bad = pct_valor(inadimplentes, total)
    venc = f' · {_moeda(valor_vencido)} vencidos' if valor_vencido else ""
    st.markdown(
        f"""
        <div class="cmp-wrap">
          <div class="cmp-hd">Situação da carteira</div>
          <div class="cmp-sub">Elegíveis participam dos sorteios · base de {_numero(total)} clientes{venc}</div>
          <div class="cmp-grid">
            <div class="cmp-cell ok">
              <div class="cmp-cap"><i class="fa-solid fa-user-check"></i> Adimplentes</div>
              <div class="cmp-num">{_numero(adimplentes)}</div>
              <div class="cmp-pct">{percentual(pct_ok)} da carteira</div>
            </div>
            <div class="cmp-cell bad">
              <div class="cmp-cap"><i class="fa-solid fa-user-xmark"></i> Inadimplentes</div>
              <div class="cmp-num">{_numero(inadimplentes)}</div>
              <div class="cmp-pct">{percentual(pct_bad)} da carteira</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def card(titulo: str = "", sub: str = ""):
    """Card com header (.card do CGID). Usar como `with card(...): ...`."""
    cont = st.container(border=True)
    with cont:
        if titulo:
            s = f'<div class="card-sub">{sub}</div>' if sub else ""
            st.markdown(
                f'<div class="card-hd"><div class="card-title">{titulo}</div>{s}</div>',
                unsafe_allow_html=True,
            )
        yield cont


def badge(texto: str, cor: str = "green", icon: str = "") -> str:
    """Retorna HTML de um badge/pill. cor: green|red|amber|blue|gray."""
    i = f'<i class="fa-solid {icon}"></i>' if icon else ""
    return f'<span class="bt-badge {cor}">{i}{texto}</span>'


def hero(label: str, valor: str, chips: list[str]) -> None:
    """Banner de destaque (arrecadação). Gradiente brand + ouro, número grande."""
    chips_html = "".join(f'<span class="hero-chip">{c}</span>' for c in chips)
    st.markdown(
        f"""
        <div class="hero">
          <div class="hero-inner">
            <div class="hero-label">{label}</div>
            <div class="hero-value">{valor}</div>
            <div class="hero-chips">{chips_html}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def donut(df: pd.DataFrame, names: str, values: str, titulo: str, sub: str = "",
          cores: dict | None = None) -> None:
    """Donut — v8: hole 60%, separador branco grosso, total no centro, legenda lateral com
    pct grande, nome e contagem, hover com detalhes, pull leve."""
    with card(titulo, sub):
        total = int(df[values].sum())
        _default_colors = [BRAND["600"], SEMANTIC["danger_500"], ACENTO["amber"],
                            BRAND["300"], SEMANTIC["info_500"]]
        color_seq = list(cores.values()) if cores else _default_colors

        fig = px.pie(df, names=names, values=values, hole=.60,
                     color=names, color_discrete_map=cores,
                     color_discrete_sequence=color_seq)
        ht = "<b>%{label}</b><br>Recebido: <b>R$ %{value:,.2f}</b> (%{percent:.1%})<extra></extra>"
        fig.update_traces(
            textinfo="none",
            marker=dict(line=dict(color="#fff", width=3)),
            hovertemplate=ht,
            pull=[0.02] * len(df),
        )
        fig.add_annotation(
            text=f"<b>{_numero(total)}</b><br><span style='font-size:9.5px;color:#94A3B8;"
                 f"letter-spacing:.5px'>TOTAL</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20, color="#0F172A", family=_V8_FONT),
            xref="paper", yref="paper", align="center",
        )
        fig.update_layout(
            showlegend=False,
            margin=dict(l=0, r=0, t=4, b=4),
        )

        legend_items = []
        name_to_color: dict = {}
        for i, (_, row) in enumerate(df.iterrows()):
            nm = str(row[names])
            cor = (cores or {}).get(nm) or color_seq[i % len(color_seq)]
            name_to_color[nm] = cor

        for _, row in df.iterrows():
            pct = 100 * row[values] / total if total else 0
            nm = str(row[names])
            cor = name_to_color.get(nm, BRAND["500"])
            val_fmt = _moeda(row[values]) if row[values] > 1000 else _numero(int(row[values]))
            legend_items.append(
                f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:14px">'
                f'<span style="width:11px;height:11px;border-radius:3px;background:{cor};'
                f'flex-shrink:0;margin-top:4px"></span>'
                f'<div>'
                f'<div style="font-size:17px;font-weight:700;color:#0F172A;'
                f'font-family:{_V8_FONT};line-height:1.15">{pct:.1f}%</div>'
                f'<div style="font-size:12px;font-weight:500;color:#374151;'
                f'font-family:{_V8_FONT};margin-top:1px">{nm}</div>'
                f'<div style="font-size:11px;color:#6B7280;font-family:{_V8_FONT};margin-top:1px">'
                f'{val_fmt}</div>'
                f'</div></div>'
            )

        # Donut à esquerda (coluna larga p/ centralizar), legenda à direita.
        cols = st.columns([1.7, 1])
        with cols[0]:
            _show(fig, 320, legenda=False)
        with cols[1]:
            st.markdown(
                '<div style="display:flex;flex-direction:column;justify-content:center;'
                'height:320px;padding:4px 0 4px 8px">' + "".join(legend_items) + "</div>",
                unsafe_allow_html=True,
            )


def medidor(valor: float, maximo: float, titulo: str, sub: str = "",
            sufixo: str = "%", numformat: str | None = None,
            nota: str = "") -> None:
    with card(titulo, sub):
        P = PALETAS["claro"]
        fig = go.Figure(go.Indicator(
            mode="gauge", value=valor,
            gauge={
                "axis": {"range": [0, maximo], "tickcolor": P["muted"],
                         "tickfont": {"color": P["muted"], "size": 10}},
                "bar": {"color": BRAND["500"], "thickness": .3},
                "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
                "steps": [{"range": [0, maximo], "color": P["grid"]}],
            },
        ))
        # % como anotação centralizada (número nativo do plotly fica deslocado).
        _vfmt = (f"{{:{numformat}}}".format(valor) if numformat else f"{valor:g}")
        fig.add_annotation(
            text=f"<b>{_vfmt}{sufixo}</b>",
            x=0.5, y=0.18, showarrow=False,
            xref="paper", yref="paper", xanchor="center",
            font=dict(size=46, color=BRAND["600"], family=_V8_FONT),
        )
        _show(fig, 300)
        if nota:
            st.markdown(
                f'<div style="font-size:12.5px;color:#475569;line-height:1.5;'
                f'background:#f8fafc;border:1px solid #eef1f5;border-radius:9px;'
                f'padding:10px 13px;margin-top:2px">{nota}</div>',
                unsafe_allow_html=True,
            )


def funil(df: pd.DataFrame, x: str, y: str, titulo: str, sub: str = "") -> None:
    with card(titulo, sub):
        fig = px.funnel(df, x=x, y=y)
        # Texto com valor cheio pt-BR (sem abreviação SI do plotly) + % inicial.
        base = float(df[x].iloc[0]) if len(df) else 0.0
        _txt = [
            f'{int(v):,}'.replace(",", ".") + f'<br>{(100*v/base if base else 0):.0f}%'
            for v in df[x]
        ]
        fig.update_traces(marker_color=BRAND["500"], text=_txt, textinfo="text",
                          textfont_size=13, name=titulo)
        fig.update_layout(
            xaxis=dict(title="", showticklabels=False, showgrid=False),
            yaxis=dict(title=""),
            hoverlabel=_v8_hoverlabel(),
        )
        _show(fig, 320)


def selo_calculado_vs_oficial() -> None:
    """Aviso fixo: cupons calculados ≠ oficiais (CONTEXT 14.3)."""
    st.markdown(
        '<p class="nota-regra"><i class="fa-solid fa-circle-info"></i>'
        '<span>Os cupons exibidos são <strong>calculados internamente</strong> a partir dos '
        'recebimentos. Não representam os cupons <strong>oficiais</strong> emitidos pela '
        'plataforma externa.</span></p>',
        unsafe_allow_html=True,
    )


def nota_regra(texto: str) -> None:
    """Observação discreta e institucional (ex.: regra de cupom). CONTEXT item 5."""
    st.markdown(
        f'<p class="nota-regra"><i class="fa-solid fa-circle-info"></i><span>{texto}</span></p>',
        unsafe_allow_html=True,
    )


# ── Gráficos — estilo v8 (ApexCharts → Plotly) ───────────────────────────────
_show_counter: list[int] = [0]

_V8_GRID  = "#F1F5F9"
_V8_LABEL = "#6B7280"
_V8_FONT  = '"Segoe UI", system-ui, Arial, sans-serif'  # fonte de texto do portal_campanha_v8
_V8_TT_BG = "#FFFFFF"
_V8_TT_BORDER = "#E2E8F0"


def _v8_hoverlabel() -> dict:
    return dict(
        bgcolor=_V8_TT_BG,
        bordercolor=_V8_TT_BORDER,
        font=dict(family=_V8_FONT, size=13, color="#1E293B"),
        align="left",
        namelength=0,
    )


def _fmt_k(v: float) -> str:
    """Formata número: 0→'0', <1000→inteiro, ≥1000→'XK'."""
    if v == 0:
        return "0"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1000:
        return f"{v/1000:.0f}K"
    return str(int(v))


def _show(fig, altura: int = 320, legenda: bool = True) -> None:
    """Base render: grid v8, fundo transparente, font/label padronizados, tooltip estilo v8."""
    fig.update_layout(
        height=altura,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=_V8_FONT, color=_V8_LABEL, size=11),
        hoverlabel=_v8_hoverlabel(),
        showlegend=legenda,
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="left", x=0.0,
            bgcolor="rgba(0,0,0,0)",
            borderwidth=0,
            font=dict(size=11, color=_V8_LABEL, family=_V8_FONT),
            itemsizing="constant",
            tracegroupgap=0,
        ),
        margin=dict(l=4, r=4, t=32, b=4),
    )
    _eixo = dict(
        gridcolor=_V8_GRID, gridwidth=1, griddash="dot",
        linecolor="rgba(0,0,0,0)", zeroline=False, ticks="",
        tickfont=dict(size=11, color=_V8_LABEL, family=_V8_FONT),
        showline=False,
    )
    fig.update_xaxes(**_eixo, showgrid=False)
    fig.update_yaxes(**_eixo)
    _show_counter[0] += 1
    # staticPlot: gráfico sem interação (toque/scroll não agarram). Rótulos já
    # mostram os valores, então o hover não faz falta. Tabelas seguem interativas.
    st.plotly_chart(fig, key=f"chart_{_show_counter[0]}", width="stretch",
                    config={"displayModeBar": False, "staticPlot": True})


def linha_temporal(df: pd.DataFrame, x: str, y: str, titulo: str = "", sub: str = "",
                   skip_card: bool = False) -> None:
    """Área suave — v8: fill gradiente, markers brancos, anotação no último."""
    ctx = card(titulo, sub) if not skip_card else _null_ctx()
    with ctx:
        fig = px.area(df, x=x, y=y, line_shape="spline")
        ht = "<b>%{x}</b><br>Acumulado: <b>R$ %{y:,.2f}</b><extra></extra>"
        fig.update_traces(
            line=dict(color=BRAND["500"], width=2.5),
            fillcolor="rgba(46,125,50,.12)",
            marker=dict(
                color=BRAND["500"], size=5,
                line=dict(color="#fff", width=2),
                symbol="circle",
            ),
            mode="lines+markers",
            name=titulo,
            hovertemplate=ht,
        )
        # anotação no último ponto (label com fundo verde = v8 xaxis annotation)
        if not df.empty:
            last_x = df[x].iloc[-1]
            last_y = float(df[y].iloc[-1])
            try:
                fig.add_vline(
                    x=last_x,
                    line=dict(color=BRAND["600"], width=1.5, dash="dot"),
                )
            except Exception:
                pass
            fig.add_annotation(
                x=last_x, y=0,
                text=f"Total: R$ {_fmt_k(last_y)}",
                showarrow=False,
                xref="x", yref="paper",
                yanchor="top", xanchor="center",
                bgcolor=BRAND["600"],
                font=dict(color="#fff", size=10, family=_V8_FONT),
                borderpad=5,
            )
        fig.update_layout(
            yaxis=dict(tickformat=".2s"),
            # dd/mm — neutro, evita meses em inglês do plotly (May, Jun…)
            xaxis=dict(tickangle=0, tickformat="%d/%m"),
        )
        _show(fig)


def barras(df: pd.DataFrame, x: str, y: str, titulo: str = "", sub: str = "",
           color: str | None = None, is_monetary: bool = False,
           destaque: str | None = None, skip_card: bool = False) -> None:
    """Barras coluna — v8: borderRadius 5, labels XK brancos dentro, tooltip pt-BR, hover darken."""
    with (card(titulo, sub) if not skip_card else _null_ctx()):
        # Valores cheios (sem abreviação), label vertical acima da barra.
        labels = [_moeda(v) if is_monetary else _numero(int(v)) for v in df[y]]
        fig = px.bar(df, x=x, y=y)

        if is_monetary:
            ht = "<b>%{x}</b><br>Valor: <b>R$ %{y:,.2f}</b><extra></extra>"
        else:
            ht = "<b>%{x}</b><br>Quantidade: <b>%{y:,.0f}</b><extra></extra>"

        if destaque is not None and destaque in set(df[x].astype(str)):
            cores_barra = ["#e6b800" if str(v) == str(destaque) else BRAND["500"]
                           for v in df[x]]
        else:
            cores_barra = BRAND["500"]

        fig.update_traces(
            marker_color=cores_barra,
            marker_line_width=0,
            marker_cornerradius=5,
            textposition="outside",
            textangle=-90,
            text=labels,
            textfont=dict(color="#1E293B", size=10, family=_V8_FONT),
            cliponaxis=False,
            width=0.45,
            name=titulo,
            hovertemplate=ht,
        )
        _maxy = float(df[y].max()) if len(df) else 1.0
        fig.update_layout(
            yaxis=dict(showgrid=True, showticklabels=True, tickformat=".2s",
                       title="", range=[0, _maxy * 1.5]),
            xaxis=dict(title="", type="category"),
            bargap=0.5,
            hoverlabel=_v8_hoverlabel(),
        )
        _show(fig)


def _faixa_cores_v8(valores: pd.Series) -> list[str]:
    """Cores por faixa proporcional — espelha plotOptions.bar.colors.ranges do v8."""
    mx = float(valores.max()) if len(valores) else 0.0
    if mx == 0:
        return [BRAND["500"]] * len(valores)
    resultado = []
    for v in valores:
        r = float(v) / mx
        if r >= 0.80:
            resultado.append(BRAND["900"])   # #1B5E20 — topo
        elif r >= 0.60:
            resultado.append(BRAND["700"])   # #2E7D32
        elif r >= 0.40:
            resultado.append(BRAND["500"])   # #388E3C
        elif r >= 0.20:
            resultado.append(ACENTO["amber"])
        else:
            resultado.append(SEMANTIC["warning_700"])
    return resultado


def barras_cidades(df: pd.DataFrame, x: str, y: str, titulo: str, sub: str = "", is_monetary: bool = False) -> None:
    """Barras coluna coloridas por faixa — v8 ch0bar/ch1eng: borderRadius, hover darken, tooltip pt-BR."""
    with card(titulo, sub):
        # Valores cheios (sem abreviação), label vertical acima da barra.
        labels = [_moeda(v) if is_monetary else _numero(int(v)) for v in df[y]]
        fig = px.bar(df, x=x, y=y)
        cores = _faixa_cores_v8(df[y])

        if is_monetary:
            ht = "<b>%{x}</b><br>Valor: <b>R$ %{y:,.2f}</b><extra></extra>"
        else:
            ht = "<b>%{x}</b><br>Cupons: <b>%{y:,.0f}</b><extra></extra>"

        fig.update_traces(
            marker_color=cores,
            marker_line_width=0,
            marker_cornerradius=5,
            textposition="outside",
            textangle=-90,
            text=labels,
            textfont=dict(color="#1E293B", size=13, family=_V8_FONT),
            cliponaxis=False,
            width=0.55,
            name=titulo,
            hovertemplate=ht,
        )
        _maxy = float(df[y].max()) if len(df) else 1.0
        # Monetário tem rótulo vertical mais comprido → precisa de mais headroom.
        _topo = 2.4 if is_monetary else 1.8
        fig.update_layout(
            # Força o tamanho do rótulo (plotly encolhe texto externo que não cabe).
            uniformtext_minsize=13, uniformtext_mode="show",
            yaxis=dict(showgrid=True, tickformat=".2s", title="",
                       range=[0, _maxy * _topo],
                       tickfont=dict(size=14, color="#475569", family=_V8_FONT)),
            xaxis=dict(title="", tickangle=-45 if len(df) > 6 else 0,
                       tickfont=dict(size=14, color="#334155", family=_V8_FONT)),
            bargap=0.5,
            hoverlabel=_v8_hoverlabel(),
        )
        _show(fig)


def progress_adimplencia(pct: float, meta: float = 70.0) -> None:
    """Barra de progresso adimplência vs meta (estilo .track HTML v8)."""
    P = PALETAS["claro"]
    pct_w = min(100.0, max(0.0, pct))
    meta_w = min(100.0, max(0.0, meta))
    delta = pct - meta
    delta_str = f"+{delta:.1f} pp" if delta >= 0 else f"{delta:.1f} pp"
    delta_cor = BRAND["600"] if delta >= 0 else SEMANTIC["danger_500"]
    val_cor = BRAND["500"] if pct >= meta else (ACENTO["amber"] if pct >= meta * 0.75 else SEMANTIC["danger_500"])
    st.markdown(
        f"""
        <div class="prog-adim-wrap">
          <div class="prog-adim-row">
            <div>
              <div class="prog-adim-title">Adimplência da carteira</div>
              <div class="prog-adim-sub">Meta: {meta:.0f}% — clientes elegíveis participam dos sorteios</div>
            </div>
            <div style="text-align:right">
              <div class="prog-adim-pct" style="color:{val_cor}">{pct:.1f}%</div>
              <div class="prog-adim-delta" style="color:{delta_cor}">{delta_str} vs meta</div>
            </div>
          </div>
          <div class="prog-adim-track">
            <div class="prog-adim-fill" style="width:{pct_w:.1f}%"></div>
            <div class="prog-adim-meta" style="left:{meta_w:.1f}%"></div>
          </div>
          <div class="prog-adim-leg">
            <span>0%</span>
            <span style="color:{ACENTO['amber']};font-weight:600">▲ Meta {meta:.0f}%</span>
            <span>100%</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ranking_cidades(
    df: pd.DataFrame, nome_col: str, valor_col: str,
    titulo: str, sub: str = "", cor: str = "red",
    total: float | None = None,
) -> None:
    """Lista de ranking estilo HTML v8 com barra proporcional animada.

    total: base p/ % de participação (CONTEXT item 11). Se None, usa a soma do
    próprio recorte. Percentual calculado de forma segura (sem div/0) e em BR.
    """
    _cor_map = {
        "red":   (SEMANTIC["danger_500"],  SEMANTIC["danger_700"]),
        "green": (BRAND["500"],            BRAND["700"]),
        "amber": (ACENTO["amber"],         SEMANTIC["warning_700"]),
    }
    c_fill, c_val = _cor_map.get(cor, _cor_map["red"])
    mx = float(df[valor_col].max()) if not df.empty else 1.0
    base_total = float(total) if total is not None else (
        float(df[valor_col].sum()) if not df.empty else 0.0
    )

    items = []
    for idx, (_, row) in enumerate(df.iterrows()):
        pct = int(100 * float(row[valor_col]) / mx) if mx > 0 else 0
        pct_part = percentual(pct_valor(float(row[valor_col]), base_total))
        items.append(
            f'<li class="rank-item">'
            f'<span class="rank-n">{idx + 1}</span>'
            f'<span class="rank-nm">{row[nome_col]}</span>'
            f'<div class="rank-track"><div class="rank-fill" style="width:{pct}%;background:{c_fill}"></div></div>'
            f'<span class="rank-val" style="color:{c_val}">{_moeda(row[valor_col])}'
            f'<span style="color:{PALETAS["claro"]["muted"]};font-weight:500;font-size:10.5px;display:block;text-align:right">{pct_part}</span>'
            f'</span>'
            f'</li>'
        )
    with card(titulo, sub):
        st.markdown(f'<ul class="rank-list">{"".join(items)}</ul>', unsafe_allow_html=True)


def ranking_cidades_tabela(
    df: pd.DataFrame, nome_col: str, valor_col: str,
    titulo: str, sub: str = "", cor: str = "red",
    total: float | None = None,
) -> None:
    """Ranking de cidades em tabela (estilo .cal-table). % sobre o total informado."""
    _cor_val = {
        "red": SEMANTIC["danger_700"], "green": BRAND["700"],
        "amber": SEMANTIC["warning_700"],
    }.get(cor, SEMANTIC["danger_700"])
    base_total = float(total) if total is not None else (
        float(df[valor_col].sum()) if not df.empty else 0.0
    )
    muted = PALETAS["claro"]["muted"]
    rows_html = []
    for idx, (_, row) in enumerate(df.iterrows()):
        pct = percentual(pct_valor(float(row[valor_col]), base_total))
        rows_html.append(
            f'<tr>'
            f'<td style="color:{muted};width:28px">{idx + 1}</td>'
            f'<td>{row[nome_col]}</td>'
            f'<td style="color:{_cor_val};font-weight:600;text-align:right">{_moeda(row[valor_col])}</td>'
            f'<td style="color:{muted};text-align:right;width:84px">{pct}</td>'
            f'</tr>'
        )
    with card(titulo, sub):
        st.markdown(
            '<table class="cal-table"><thead><tr>'
            '<th>#</th><th>Cidade</th>'
            '<th style="text-align:right">Valor vencido</th>'
            '<th style="text-align:right">% do total</th>'
            f'</tr></thead><tbody>{"".join(rows_html)}</tbody></table>',
            unsafe_allow_html=True,
        )


def calendario_sorteios_comp(df: pd.DataFrame) -> None:
    """Tabela visual do calendário de sorteios (estilo HTML v8)."""
    _status_cls = {
        "Realizado": ("cal-done",   '<i class="fa-solid fa-check"></i> '),
        "Em breve":  ("cal-soon",   '<i class="fa-regular fa-clock"></i> '),
        "Futuro":    ("cal-future", ""),
        "Final":     ("cal-final",  '<i class="fa-solid fa-trophy"></i> '),
    }
    rows_html = []
    for _, r in df.iterrows():
        cls, ico = _status_cls.get(r["Status"], ("cal-future", ""))
        final_cls = " cal-final-row" if r.get("_final") else ""
        rows_html.append(
            f'<tr class="{final_cls}">'
            f'<td>{r["Pagamento"]}</td>'
            f'<td>{r["Sorteio"]}</td>'
            f'<td class="cal-premio">{r["Prêmio"]}</td>'
            f'<td><span class="cal-badge {cls}">{ico}{r["Status"]}</span></td>'
            f'</tr>'
        )
    with card("Calendário de sorteios", "Pagamento → sorteio → prêmio"):
        st.markdown(
            f'<div style="overflow-x:auto"><table class="cal-table">'
            f'<thead><tr><th>Pagamento</th><th>Sorteio</th><th>Prêmio</th><th>Status</th></tr></thead>'
            f'<tbody>{"".join(rows_html)}</tbody>'
            f'</table></div>',
            unsafe_allow_html=True,
        )


def banner_premiacao() -> None:
    """Banner com pills dos sorteios mensais (estilo .banner + .pills HTML v8)."""
    import pandas as pd
    from datetime import date
    from config.settings import CAMPANHA
    meses = pd.period_range(CAMPANHA.inicio, CAMPANHA.fim, freq="M")
    # Sorteio acontece no mês seguinte ao pagamento (mes+1). O destaque verde
    # acompanha o sorteio mais próximo de acontecer: primeiro cujo mês de sorteio
    # ainda não passou em relação a hoje. Se todos já passaram, destaca o último.
    hoje = pd.Period(date.today(), freq="M")
    proximo = next((i for i, mes in enumerate(meses) if (mes + 1) >= hoje),
                   len(meses) - 1)
    pills = []
    for i, mes in enumerate(meses):
        mes_sor = mes + 1
        is_final = i == len(meses) - 1
        premio = "R$&nbsp;1.000.000" if is_final else "Casa + Carro"
        cls = " banner-pill-star" if i == proximo else ""
        pills.append(
            f'<div class="banner-pill{cls}">'
            f'<span class="banner-pill-m">{mes_ano_pt(mes, ano_curto=True)}</span>'
            f'<span class="banner-pill-t">{mes_ano_pt(mes_sor, ano_curto=True)} - {premio}</span>'
            f'</div>'
        )
    st.markdown(
        f'<div class="banner-prem">'
        f'<div><div class="banner-prem-h">5 Casas + R$&nbsp;1.000.000 em prêmios</div>'
        f'<div class="banner-prem-s">Clientes elegíveis participam automaticamente dos '
        f'sorteios mensais e do prêmio final.</div></div>'
        f'<div class="banner-pills">{"".join(pills)}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# Mapa valor → (fundo, texto) para badges em célula (espelha .status-badge do CGID)
_COR_STATUS = {
    "elegivel": ("#d8f3de", "#1a6229"), "cadastrado": ("#d8f3de", "#1a6229"),
    "adimplente": ("#d8f3de", "#1a6229"), "normal": ("#d8f3de", "#1a6229"),
    "pendente": ("#fffbeb", "#92400e"), "recuperacao": ("#fffbeb", "#92400e"),
    "bloqueado": ("#fef2f2", "#b91c1c"), "inadimplente": ("#fef2f2", "#b91c1c"),
    "nao_cadastrado": ("#ececed", "#6b6b74"),
}
# Colunas que recebem coloração de status
_COLS_STATUS = (
    "status_elegibilidade", "status_cadastro", "classificacao_recebimento",
    "status_inadimplencia_antes", "status_apos_pagamento", "motivo_bloqueio",
)


def _estilo_celula(v) -> str:
    par = _COR_STATUS.get(str(v).strip().lower())
    if not par:
        return ""
    bg, fg = par
    return f"background-color:{bg};color:{fg};font-weight:600;border-radius:6px;"


def tabela(df: pd.DataFrame, titulo: str = "", sub: str = "", status: bool = True,
           altura: int | None = None, pin_primeira: bool = True) -> None:
    """Tabela com coloração semântica nas colunas de status (CGID .status-badge).

    altura: altura fixa em px (None = automática do Streamlit).
    pin_primeira: congela a 1ª coluna (fica fixa ao rolar na horizontal).
    """
    if status:
        cols = [c for c in _COLS_STATUS if c in df.columns]
        obj = df.style.map(_estilo_celula, subset=cols) if cols else df
    else:
        obj = df

    # Só a 1ª coluna visível tem largura fixa (medium) e fica congelada (pinned);
    # as demais ficam sem width p/ expandir e preencher o container no desktop
    # (width="stretch"). No mobile o container é estreito → colunas encolhem e
    # rola na horizontal, com a 1ª fixa. (ignora colunas técnicas de status.)
    col_cfg = None
    if pin_primeira:
        _visiveis = [c for c in df.columns if c not in _COLS_STATUS]
        if _visiveis:
            col_cfg = {_visiveis[0]: st.column_config.Column(pinned=True, width="medium")}

    if titulo:
        with card(titulo, sub):
            st.dataframe(obj, hide_index=True, width="stretch", height=altura,
                         column_config=col_cfg)
    else:
        st.dataframe(obj, hide_index=True, width="stretch", height=altura,
                     column_config=col_cfg)
