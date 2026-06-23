"""Identidade visual do painel.

Porta o design system do CGID (frontend/src/styles) para Streamlit: brand
verde #2a9d45, Plus Jakarta Sans, Font Awesome, stat-cards com ícone+acento,
cards com header/body. CONTEXT 10.1: executivo, impactante mas não carregado;
legível em TV e celular. Suporta tema claro e escuro (toggle na sidebar).
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ── Tokens de marca (espelham styles/global.css) ─────────────────────────────
BRAND = {
    "50": "#f5f8f6", "100": "#d8f3de", "200": "#b3e6bc", "300": "#7dd190",
    "400": "#4ab861", "500": "#2a9d45", "600": "#1e7d34", "700": "#1a6229",
    "800": "#174f23", "900": "#0f3317", "950": "#081c0d",
}
GRAY = {
    "0": "#ffffff", "50": "#f5f5f6", "100": "#ececed", "200": "#d8d8da",
    "300": "#b8b8bc", "400": "#8f8f96", "500": "#6b6b74", "600": "#4e4e57",
    "700": "#35353e", "800": "#232329", "900": "#141418",
}
BRAND_RED = "#e2231a"
SEMANTIC = {
    "danger_50": "#fef2f2", "danger_500": "#ef4444", "danger_700": "#b91c1c",
    "warning_50": "#fffbeb", "warning_500": "#f59e0b", "warning_700": "#92400e",
    "info_50": "#eff6ff", "info_500": "#3b82f6", "info_700": "#1d4ed8",
}
ACENTO = {
    "amber": SEMANTIC["warning_500"], "red": SEMANTIC["danger_500"],
    "blue": SEMANTIC["info_500"], "green": BRAND["500"],
}
RADIUS = {"sm": "6px", "md": "10px", "lg": "14px", "xl": "20px"}
SHADOW = {
    "sm": "0 1px 3px rgba(0,0,0,.06)",
    "md": "0 6px 18px rgba(0,0,0,.08)",
    "xl": "0 20px 60px rgba(0,0,0,.14)",
}
FONT = '"Segoe UI", system-ui, Arial, sans-serif'  # fonte de texto do portal_campanha_v8
FAVICON = "assets/logo-sidebar-icon.png"
LOGO_FULL = "assets/logo-sidebar-full.png"
COLORWAY = [
    BRAND["500"], BRAND["300"], ACENTO["blue"], ACENTO["amber"],
    BRAND["700"], BRAND_RED, BRAND["200"], GRAY["400"],
]

# ── Paletas de superfície por modo ───────────────────────────────────────────
PALETAS = {
    "claro": {
        "bg": GRAY["50"], "surface": GRAY["0"], "text": GRAY["900"],
        "muted": GRAY["400"], "label": GRAY["500"], "border": GRAY["100"],
        "border2": GRAY["200"], "grid": GRAY["100"], "hover": "rgba(15,23,42,.05)",
        "sidebar_bg": GRAY["50"], "sidebar_border": "#e4e8ee", "shadow": SHADOW["sm"],
        "shadow_h": SHADOW["md"], "neutral_bg": GRAY["100"], "neutral_fg": GRAY["600"],
        "input_bg": GRAY["0"], "hover_bg": "#fafafa",
    },
    "escuro": {
        "bg": "#0f1714", "surface": "#18211d", "text": "#eef2f0",
        "muted": "#8fa399", "label": "#b3c2ba",
        # bordas mais definidas (fronteiras visuais nítidas = sofisticação)
        "border": "#33473c", "border2": "#415546",
        # gridlines quase fantasma (discretas)
        "grid": "rgba(255,255,255,.045)", "hover": "rgba(255,255,255,.06)",
        "sidebar_bg": "#121a16", "sidebar_border": "#26332c",
        "shadow": "0 1px 3px rgba(0,0,0,.45)", "shadow_h": "0 8px 22px rgba(0,0,0,.55)",
        "neutral_bg": "rgba(255,255,255,.10)", "neutral_fg": "#b3c2ba",
        "input_bg": "#1e2823", "hover_bg": "rgba(255,255,255,.04)",
    },
}


def _css(P: dict) -> str:
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@500;600;700&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css');

/* ── Tokens de tipografia (CONTEXT item 1) ───────────────────
   --font-text : Segoe UI p/ títulos, labels, textos.
   --font-num  : DIN p/ números/KPIs/valores/percentuais; fallback seguro
                 Arial Narrow / Roboto Condensed (carregada acima) / Arial. */
:root {{
  --font-text: "Segoe UI", "Segoe UI Variable", system-ui, -apple-system, Roboto, Arial, sans-serif;
  --font-num: "Roboto Condensed", "Bahnschrift", "Arial Narrow", sans-serif;
}}

/* ── Base ──────────────────────────────────────────────────── */
/* Segoe UI como fonte de texto. !important p/ vencer o tema default do
   Streamlit (Source Sans), que aplica em seletores de alta especificidade. */
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"],
.stMarkdown, .stMarkdown p, h1, h2, h3, h4, h5, h6, label,
.ph-title, .ph-sub, .card-title, .card-sub, .stat-label, .cmp-hd, .cmp-sub,
button[data-baseweb="tab"], [data-testid="stWidgetLabel"] p {{
  font-family: var(--font-text) !important; }}
/* Números/valores/percentuais em DIN (KPIs, hero, progresso, tabelas) */
.stat-val, .hero-value, .prog-adim-pct, .prog-adim-delta, .ph-stamp,
.rank-val, .rank-n, .cmp-num, .cmp-pct, [data-testid="stMetricValue"] {{
  font-family: var(--font-num) !important; font-feature-settings: "tnum" 1; }}
.stApp, [data-testid="stApp"] {{ background: {P['bg']} !important; color: {P['text']}; }}
[data-testid="stAppViewContainer"] {{ background: {P['bg']} !important; color: {P['text']}; }}
[data-testid="stMain"] {{ background: {P['bg']} !important; }}
.stMarkdown, .stMarkdown p, label, [data-testid="stWidgetLabel"] p {{ color: {P['text']}; }}

/* Crossfade ao trocar claro↔escuro.
   IMPORTANTE: NÃO transicionar o fundo de .stApp/sidebar — na troca de página o
   Streamlit pinta o bg padrão (branco) antes do CSS injetar e a transição
   ANIMA branco→escuro = flash. Sem transição no bg grande, o snap é imperceptível.
   Transição fica só nos textos/cards (toggle continua suave). */
.ph-stamp, .ph-title, .ph-sub, .card-title, .card-sub, .stat-val, .stat-label,
input, textarea, h1, h2, h3, .stMarkdown p {{
  transition: color .45s ease, border-color .45s ease; }}
/* superfícies grandes NUNCA transicionam bg (mata o flash branco na navegação) */
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
[data-testid="stSidebar"], section.main {{ transition:none !important; }}

/* Chrome do Streamlit: esconde menu/deploy/toolbar/footer/status (CONTEXT item 3).
   display:none (não só visibility) p/ não reservar espaço na publicação. */
#MainMenu, footer, header[data-testid="stHeader"],
[data-testid="stMainMenuButton"], [data-testid="stAppDeployButton"],
[data-testid="stToolbar"], [data-testid="stToolbarActions"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] {{
  display:none !important; visibility:hidden !important; }}
/* Sidebar completamente removida — sem widget oculto, display:none é seguro. */
[data-testid="stSidebar"],
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stBaseButton-headerNoPadding"] {{ display: none !important; }}
/* Usa 100% da largura sem a margem da sidebar */
[data-testid="stAppViewContainer"] {{ margin-left: 0 !important; }}
.block-container {{ padding: 0.1rem 2rem 2rem !important; max-width: 100% !important; width: 100% !important; }}
[data-testid="stAppViewContainer"] {{ padding-left: 0 !important; }}

/* Blocos utilitários (iframes de script via components.html + <style> injetado)
   saem do fluxo com position:absolute → não geram slot de gap no topo da página
   e não expõem a altura default do iframe (150px). O iframe segue no DOM e
   executa o JS normalmente (boot-tema/auto-refresh/autoplay). Não afeta o splash
   (markdown fixo) nem os gráficos (plotly, sem iframe). */
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:has(> iframe),
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:has(.stMarkdown style),
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:has(.splash) {{
  position: absolute !important; height: 0 !important; width: 0 !important;
  overflow: hidden !important; pointer-events: none !important; }}

h1, h2, h3 {{ font-weight:800 !important; color:{P['text']}; letter-spacing:-.3px; }}

/* ── Page header (.ph) ─────────────────────────────────────── */
.ph {{ display:flex; align-items:center; justify-content:space-between; gap:16px; margin:0 0 22px; }}
.ph-l {{ display:flex; align-items:center; gap:0; }}
.ph-logo-box {{
  display:flex; align-items:center; justify-content:center;
  height:66px; flex-shrink:0;
}}
.ph-logo-img {{ height:48px; width:auto; object-fit:contain; display:block; }}
.ph-sep {{ width:1px; height:42px; background:{P['border2']}; flex-shrink:0; margin:0 18px; }}
.ph-title {{ font-size:18px; font-weight:700; color:{P['text']}; letter-spacing:-.2px; line-height:1.2; }}
.ph-sub {{ font-size:12px; color:{P['muted']}; margin-top:3px; }}
.ph-stamp {{ font-size:12px; color:{P['muted']}; white-space:nowrap;
  display:inline-flex; align-items:center; gap:6px; background:{P['surface']};
  border:1px solid {P['border']}; padding:7px 12px; border-radius:99px; box-shadow:{P['shadow']}; }}
.ph-stamp i {{ color:{BRAND['500']}; }}

/* ── Hero band (destaque de arrecadação) ───────────────────── */
.hero {{ position:relative; border-radius:18px; overflow:hidden; margin-bottom:18px;
  background: linear-gradient(120deg, {BRAND['700']} 0%, {BRAND['600']} 45%, {BRAND['800']} 100%);
  box-shadow: 0 12px 34px rgba(15,51,23,.4); animation: fadeUp .5s cubic-bezier(.4,0,.2,1) both; }}
.hero::before {{ content:''; position:absolute; inset:0;
  background:
    radial-gradient(ellipse 55% 130% at 88% -10%, rgba(255,215,0,.24) 0%, transparent 60%),
    repeating-linear-gradient(63deg, rgba(255,255,255,.045) 0 1px, transparent 1px 34px); }}
.hero::after {{ content:''; position:absolute; left:0; top:0; bottom:0; width:5px;
  background: linear-gradient(180deg,#fff7cc,#ffd700,#b8860b); }}
.hero-inner {{ position:relative; padding:24px 30px; }}
.hero-label {{ font-size:12.5px; font-weight:700; letter-spacing:1.4px; text-transform:uppercase;
  color: rgba(255,255,255,.72); }}
.hero-value {{ font-size:clamp(26px,3vw,40px); font-weight:800; letter-spacing:-.4px; line-height:1.05;
  color:#fff; margin-top:3px; text-shadow:0 2px 10px rgba(0,0,0,.28); }}
.hero-chips {{ display:flex; flex-wrap:wrap; gap:9px; margin-top:16px; }}
.hero-chip {{ display:inline-flex; align-items:center; gap:6px; font-size:12.5px; font-weight:600;
  color:#fff; padding:6px 14px; border-radius:99px;
  background:rgba(255,255,255,.13); border:1px solid rgba(255,255,255,.22); }}
.hero-chip b {{ color:#ffe27a; font-weight:800; }}

/* ── Stat cards ────────────────────────────────────────────── */
.stats-row {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(225px,1fr)); gap:16px; margin-bottom:8px; }}
.stat-card {{ background:{P['surface']}; border:1px solid {P['border']}; border-radius:{RADIUS['lg']};
  padding:20px 22px; box-shadow:{P['shadow']}; position:relative; overflow:visible;
  transition: box-shadow 150ms cubic-bezier(.4,0,.2,1), transform 150ms cubic-bezier(.4,0,.2,1),
              background-color .45s ease, border-color .45s ease; }}
.stat-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:3px;
  border-radius:{RADIUS['lg']} {RADIUS['lg']} 0 0; background: linear-gradient(90deg, {BRAND['400']}, {BRAND['300']}); }}
.stat-card.amber::before {{ background: linear-gradient(90deg, {ACENTO['amber']}, #fbbf24); }}
.stat-card.red::before   {{ background: linear-gradient(90deg, {ACENTO['red']}, #f87171); }}
.stat-card.blue::before  {{ background: linear-gradient(90deg, {ACENTO['blue']}, #60a5fa); }}
.stat-card:hover {{ box-shadow:{P['shadow_h']}; transform:translateY(-2px); border-color:{P['border2']}; z-index:1000; }}
.stat-top {{ display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }}
.stat-top > div:first-child {{ flex:1; min-width:0; }}
.stat-icon {{ width:44px; height:44px; border-radius:12px; flex-shrink:0; display:flex;
  align-items:center; justify-content:center; font-size:18px; background:{BRAND['50']}; color:{BRAND['600']}; }}
.stat-icon.amber {{ background:{SEMANTIC['warning_50']}; color:{SEMANTIC['warning_500']}; }}
.stat-icon.red   {{ background:{SEMANTIC['danger_50']};  color:{SEMANTIC['danger_500']}; }}
.stat-icon.blue  {{ background:{SEMANTIC['info_50']};    color:{SEMANTIC['info_500']}; }}
.stat-val {{ font-size:30px; font-weight:700; color:{P['text']}; line-height:1.08;
  letter-spacing:-.2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.stat-label {{ font-size:13px; color:{P['label']}; font-weight:500; margin-top:4px; }}
.stat-trend {{ display:inline-flex; align-items:center; gap:4px; margin-top:11px;
  font-size:11.5px; font-weight:600; padding:3px 9px; border-radius:99px; }}
.stat-trend.up {{ background:{BRAND['50']}; color:{BRAND['700']}; }}
.stat-trend.neutral {{ background:{P['neutral_bg']}; color:{P['neutral_fg']}; }}

/* ── Cards: st.container(border=True) vira stVerticalBlock COM borda.
   Override de border-color só afeta os que já têm borda (os demais têm
   border-style:none, então a cor não aparece). Fronteira visual nítida. */
[data-testid="stVerticalBlock"] {{ border-color:{P['border']} !important; border-width:1px; }}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"]:first-child .card-hd) {{
  background:{P['surface']}; border-radius:{RADIUS['lg']}; box-shadow:{P['shadow']}; height:100%; }}
/* Coluna estica o card à altura da linha (cards lado a lado iguais).
   Estrutura Streamlit atual: stColumn > stVerticalBlock > stLayoutWrapper >
   stVerticalBlock(card). A altura precisa propagar em cada nível, senão o
   height:100% do card resolve contra um pai não-esticado e o card encolhe. */
[data-testid="stColumn"]:has(.card-hd) {{ display: flex !important; }}
[data-testid="stColumn"]:has(.card-hd) > [data-testid="stVerticalBlock"] {{
  display: flex !important; flex-direction: column !important;
  width: 100% !important; height: 100% !important; }}
[data-testid="stColumn"]:has(.card-hd) > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] {{
  display: flex !important; flex-direction: column !important;
  flex: 1 1 auto !important; height: 100% !important; }}
[data-testid="stColumn"]:has(.card-hd) > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"] > [data-testid="stVerticalBlock"] {{
  flex: 1 1 auto !important; height: 100% !important;
  display: flex !important; flex-direction: column !important; }}
/* min-height reserva espaço do subtítulo → cards com/sem sub ficam na mesma altura */
.card-hd {{ display:flex; flex-direction:column; justify-content:center;
  padding:4px 8px 2px; margin-bottom:4px; min-height:48px; }}
/* colunas lado a lado esticam à mesma altura */
[data-testid="stHorizontalBlock"] {{ align-items:stretch; }}
.card-title {{ font-size:14px; font-weight:700; color:{P['text']}; }}
.card-sub {{ font-size:12px; color:{P['muted']}; margin-top:1px; }}

/* ── Badges / pills (chips coloridos — funcionam em ambos os modos) ── */
.bt-badge {{ display:inline-flex; align-items:center; gap:5px; padding:3px 10px;
  border-radius:99px; font-size:11.5px; font-weight:600; white-space:nowrap; }}
.bt-badge.green {{ background:{BRAND['50']}; color:{BRAND['700']}; border:1px solid {BRAND['100']}; }}
.bt-badge.red   {{ background:{SEMANTIC['danger_50']}; color:{SEMANTIC['danger_700']}; border:1px solid #fecaca; }}
.bt-badge.amber {{ background:{SEMANTIC['warning_50']}; color:{SEMANTIC['warning_700']}; border:1px solid #fde68a; }}
.bt-badge.blue  {{ background:{SEMANTIC['info_50']}; color:{SEMANTIC['info_700']}; border:1px solid #bfdbfe; }}
.bt-badge.gray  {{ background:{P['neutral_bg']}; color:{P['muted']}; border:1px solid {P['border2']}; }}

[data-testid="stAlert"],
[data-testid="stAlertContainer"],
[data-testid="stAlertContentInfo"] {{
  background:transparent !important;
  border:none !important;
  color:#1a1a1a !important;
  box-shadow:none !important;
}}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlertContainer"] p,
[data-testid="stAlertContainer"] span {{ color:#1a1a1a !important; }}

/* ── Sidebar ───────────────────────────────────────────────── */
[data-testid="stSidebar"] {{ background:{P['sidebar_bg']};
  background-image:
    radial-gradient(ellipse 120% 24% at 50% 0%, rgba(42,157,69,.16) 0%, transparent 100%),
    linear-gradient(rgba(42,157,69,.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(42,157,69,.05) 1px, transparent 1px);
  background-size: 100% 100%, 9px 9px, 9px 9px; border-right:1px solid {P['sidebar_border']}; }}
[data-testid="stSidebarNav"] {{ padding-top:8px; }}
[data-testid="stSidebarNav"] a {{ border-radius:8px; margin:2px 8px; }}
[data-testid="stSidebarNav"] a span {{ color:{P['text']}; }}
[data-testid="stSidebarNav"] a:hover {{ background:{P['hover']}; }}
/* Textos da sidebar (header "Filtros", labels) acompanham o tema */
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] [data-testid="stHeading"], [data-testid="stSidebar"] [data-testid="stHeading"] *,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p {{ color:{P['text']} !important; }}

/* ── Botões / inputs ───────────────────────────────────────── */
.stButton > button {{ border-radius:{RADIUS['md']}; font-weight:600; }}
.stButton > button[kind="primary"] {{ background: linear-gradient(135deg, {BRAND['400']}, {BRAND['600']});
  border:none; box-shadow:0 2px 8px rgba(42,157,69,.25); }}
.stButton > button[kind="primary"]:hover {{ box-shadow:0 4px 14px rgba(42,157,69,.35); transform:translateY(-1px); }}
input, textarea, [data-baseweb="input"], [data-baseweb="select"] > div {{
  background-color:{P['input_bg']} !important; color:{P['text']} !important; }}
input:focus, textarea:focus, [data-baseweb="input"]:focus-within {{
  border-color:{BRAND['400']} !important; box-shadow:0 0 0 3px rgba(42,157,69,.12) !important; }}

[data-testid="stDataFrame"] {{ border-radius:12px; overflow:hidden; border:1px solid {P['border']}; }}
hr {{ border-color:{P['border']}; }}

/* ── Motion: entrada escalonada (leve, abertura) ───────────── */
@keyframes fadeUp {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:none; }} }}
.ph {{ animation: fadeUp .45s cubic-bezier(.4,0,.2,1) both; }}
.stats-row .stat-card {{ animation: fadeUp .5s cubic-bezier(.4,0,.2,1) both; }}
.stats-row .stat-card:nth-child(1) {{ animation-delay:.04s; }}
.stats-row .stat-card:nth-child(2) {{ animation-delay:.09s; }}
.stats-row .stat-card:nth-child(3) {{ animation-delay:.14s; }}
.stats-row .stat-card:nth-child(4) {{ animation-delay:.19s; }}
.stats-row .stat-card:nth-child(5) {{ animation-delay:.24s; }}
.stats-row .stat-card:nth-child(6) {{ animation-delay:.29s; }}
.stats-row .stat-card:nth-child(7) {{ animation-delay:.34s; }}
.stats-row .stat-card:nth-child(8) {{ animation-delay:.39s; }}
[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"]:first-child .card-hd) {{
  animation: fadeUp .5s cubic-bezier(.4,0,.2,1) both .12s; }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation:none !important; }} }}

/* ── Splash lúdico: chuva de moedas + barras de ouro ────────── */
@keyframes splashOut {{ 0%,76% {{ opacity:1; }} 100% {{ opacity:0; visibility:hidden; }} }}
@keyframes splashLogo {{ 0% {{ opacity:0; transform:translateY(16px) scale(.92); }}
  55% {{ opacity:1; transform:none; }} 100% {{ opacity:1; transform:none; }} }}
@keyframes splashBar {{ from {{ width:0; }} to {{ width:100%; }} }}
@keyframes coinFall {{ 0% {{ transform:translateY(-14vh) rotate(0deg); opacity:0; }}
  12% {{ opacity:1; }} 100% {{ transform:translateY(116vh) rotate(420deg); opacity:.95; }} }}
@keyframes barPop {{ 0% {{ transform:translateY(26px) scale(.7) rotate(-6deg); opacity:0; }}
  60% {{ transform:translateY(0) scale(1.05); opacity:1; }} 100% {{ transform:none; opacity:1; }} }}
@keyframes shine {{ 0% {{ left:-70%; }} 55%,100% {{ left:130%; }} }}
@keyframes goldShimmer {{ 0% {{ background-position:0% center; }} 100% {{ background-position:200% center; }} }}
@keyframes spin {{ to {{ transform:translate(-50%,-50%) rotate(360deg); }} }}
@keyframes badgePop {{ 0% {{ transform:scale(.72); opacity:0; }}
  60% {{ transform:scale(1.06); opacity:1; }} 100% {{ transform:scale(1); opacity:1; }} }}
.splash {{ position:fixed; inset:0; z-index:99999; overflow:hidden;
  background: radial-gradient(ellipse 75% 60% at 50% 42%, {BRAND['600']} 0%, {BRAND['800']} 48%, #05140a 100%);
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:30px;
  animation: splashOut 2.4s ease forwards; pointer-events:none; }}
/* padrão diamante (argyle) sutil */
.splash::before {{ content:''; position:absolute; inset:0; opacity:.5;
  background:
    repeating-linear-gradient(63deg, rgba(255,255,255,.035) 0 1px, transparent 1px 38px),
    repeating-linear-gradient(-63deg, rgba(255,255,255,.035) 0 1px, transparent 1px 38px); }}
.splash-rain {{ position:absolute; inset:0; pointer-events:none; }}
.coin {{ position:absolute; top:0; will-change:transform;
  filter: drop-shadow(0 4px 6px rgba(0,0,0,.3)); animation: coinFall linear both; }}

/* emblema central */
.emblem-wrap {{ position:relative; display:flex; align-items:center; justify-content:center;
  width:min(340px,82vw); aspect-ratio:1; }}
.sunburst {{ position:absolute; left:50%; top:50%; width:150%; height:150%;
  transform:translate(-50%,-50%); border-radius:50%;
  background: repeating-conic-gradient(from 0deg,
    rgba(255,223,90,0) 0deg 5deg, rgba(255,223,90,.55) 5deg 6.2deg);
  -webkit-mask: radial-gradient(circle, #000 18%, rgba(0,0,0,.5) 42%, transparent 66%);
  mask: radial-gradient(circle, #000 18%, rgba(0,0,0,.5) 42%, transparent 66%);
  animation: spin 22s linear infinite; }}
.badge {{ position:relative; width:78%; aspect-ratio:1; border-radius:50%;
  background: radial-gradient(circle at 50% 38%, {BRAND['600']} 0%, {BRAND['800']} 70%, {BRAND['900']} 100%);
  box-shadow: inset 0 0 34px rgba(0,0,0,.45),
    0 0 0 2px #6b4e00, 0 0 0 11px #e6b800, 0 0 0 12px #fff3b0, 0 0 0 17px #8a6508,
    0 18px 46px rgba(0,0,0,.55);
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px;
  animation: badgePop .9s cubic-bezier(.34,1.56,.64,1) both .15s; }}
.emblem-top {{ font-size:14px; font-weight:800; letter-spacing:4px; text-transform:uppercase;
  background:linear-gradient(180deg,#fff7cc,#e6b800); -webkit-background-clip:text; background-clip:text;
  -webkit-text-fill-color:transparent; }}
.emblem-milhao {{ font-size:clamp(38px,11vw,60px); font-weight:900; letter-spacing:1px; line-height:.92;
  background:linear-gradient(180deg,#fff7cc 0%,#ffe27a 22%,#f5c200 50%,#cf9b00 72%,#9a6f00 100%);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
  text-shadow: 0 2px 0 rgba(120,80,0,.6), 0 4px 9px rgba(0,0,0,.5);
  filter: drop-shadow(0 1px 0 #8a6508); }}
.emblem-plate {{ margin-top:8px; padding:5px 18px; border-radius:8px;
  font-size:12px; font-weight:800; letter-spacing:2px; color:#0f3317;
  background:linear-gradient(180deg,#fff7cc,#ffd700 45%,#e6b800);
  box-shadow:0 3px 8px rgba(0,0,0,.4), inset 0 1px 0 rgba(255,255,255,.7),
    0 0 0 1px #8a6508; }}
.clover {{ position:absolute; font-size:34px; filter:drop-shadow(0 4px 8px rgba(0,0,0,.4));
  animation: badgePop .8s cubic-bezier(.34,1.56,.64,1) both .4s; }}
.clover.cTop {{ top:4%; right:6%; transform:rotate(18deg); }}
.clover.cBot {{ bottom:6%; left:4%; transform:rotate(-22deg); }}
.splash img {{ width:min(220px,56vw); height:auto; position:relative;
  animation: splashLogo .85s cubic-bezier(.34,1.56,.64,1) both .1s; }}
/* loader: cifrões dourados pulsando (substitui a barra) */
@keyframes cifraPulse {{ 0%,100% {{ opacity:.28; transform:translateY(3px) scale(.82); }}
  50% {{ opacity:1; transform:translateY(-4px) scale(1.14); }} }}
.cifra-load {{ display:flex; gap:16px; align-items:center; position:relative; }}
.cifra-load span {{ font-size:30px; font-weight:900; line-height:1;
  background:linear-gradient(180deg,#fff7cc 0%,#ffd700 45%,#e6b800 75%,#b8860b 100%);
  -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
  filter: drop-shadow(0 0 10px rgba(255,215,0,.45));
  animation: cifraPulse 1.3s ease-in-out infinite; }}
.splash-cap {{ font-size:12.5px; color:rgba(255,255,255,.7); letter-spacing:.3px; position:relative;
  display:inline-flex; align-items:center; gap:7px; }}

/* ── Responsivo ────────────────────────────────────────────── */
/* ── Dark/light button in page header (.ph-tema-btn) ─────── */
.ph-actions {{ display: flex; align-items: center; gap: 10px; flex-shrink: 0;
  align-self: flex-end; position: relative; z-index: 5;
  /* desce p/ a linha das abas (área vazia à direita); translate não reflui.
     52px alinha com o TEXTO das abas (o botão tem padding-bottom de 12px). */
  transform: translateY(52px); }}
.ph-tema-btn {{
  display: inline-flex; align-items: center; justify-content: center;
  border: 1px solid {P['border2']}; background: {P['surface']};
  border-radius: {RADIUS['md']}; padding: 7px 11px;
  cursor: pointer; color: {P['text']}; font-size: 15px; line-height: 1;
  text-decoration: none !important;
  transition: background .15s, transform .15s, color .15s;
}}
.ph-tema-btn:hover {{ background: {P['hover_bg']}; transform: scale(1.06); color: {P['text']}; }}
.ph-tema-btn:active {{ transform: scale(.94); }}

/* ── TV-off state: botão dimmed ─────────────────────────── */
.ph-tema-btn.tv-off {{ opacity: 0.38; }}

/* ── st.tabs() → estilo HTML v8 .nav ────────────────────── */
[data-testid="stTabBar"] {{
  gap: 0 !important;
  border-bottom: 1px solid {P['border']} !important;
  padding: 0 4px !important;
  background: {P['bg']} !important;
  overflow-x: auto !important;
  margin-bottom: 4px !important;
  /* barra de abas fixa ao rolar (logo abaixo do header) */
  position: sticky !important; top: 74px !important; z-index: 99 !important;
}}
[data-testid="stTabBar"]::-webkit-scrollbar {{ display: none; }}
button[data-baseweb="tab"] {{
  padding: 0 16px 12px !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  color: {P['muted']} !important;
  border-bottom: 2.5px solid transparent !important;
  background: transparent !important;
  border-radius: 0 !important;
  white-space: nowrap !important;
  transition: color .18s, border-color .18s !important;
  font-family: var(--font-text) !important;
}}
button[data-baseweb="tab"]:hover {{ color: {P['text']} !important; }}
button[data-baseweb="tab"][aria-selected="true"] {{
  color: {BRAND['500']} !important;
  border-bottom-color: {BRAND['500']} !important;
  font-weight: 600 !important;
}}
[data-testid="stTabsContent"] {{ padding-top: 8px !important; }}

/* ── Header + barra de abas fixos no topo ao rolar (navegação) ── */
[data-testid="stMainBlockContainer"] [data-testid="stElementContainer"]:has(.ph) {{
  position: sticky !important; top: 0 !important; z-index: 100 !important;
  background: {P['bg']} !important; }}
/* Barra de abas fixa ao rolar. O pai imediato da tab-list tem só a altura da
   barra (curto) → confina o sticky. display:contents nesse wrapper remove a
   caixa dele, e a tab-list passa a stickar dentro do container alto das abas. */
[data-testid="stTabs"] div:has(> [data-baseweb="tab-list"]) {{ display: contents !important; }}
[data-baseweb="tab-list"] {{
  position: sticky !important; top: 72px !important; z-index: 99 !important;
  background: {P['bg']} !important; }}

@media (max-width: 720px) {{
  .block-container {{ padding: 0.75rem 0.85rem 1.4rem !important; }}
  /* st.columns empilham em 1 coluna */
  [data-testid="stHorizontalBlock"] {{ flex-direction:column; gap:14px; }}
  [data-testid="stHorizontalBlock"] > div {{ width:100% !important; flex:1 1 100% !important; }}
  .stats-row {{ grid-template-columns:1fr 1fr; gap:12px; }}
  /* Header empilhado */
  .ph {{ flex-direction:column; }}
  .ph-actions {{ transform:none; align-self:flex-start; }}
  .ph-title {{ font-size:20px; }}
  .ph-ico {{ width:40px; height:40px; font-size:16px; }}
  .stat-card {{ padding:16px 16px; }}
  .stat-val {{ font-size:24px; letter-spacing:-.2px; }}
  .stat-icon {{ width:38px; height:38px; font-size:15px; }}
  /* Abas: rolagem horizontal sem quebrar, sticky no topo correto */
  [data-baseweb="tab-list"] {{ top:0 !important; overflow-x:auto !important;
    flex-wrap:nowrap !important; -webkit-overflow-scrolling:touch; }}
  button[data-baseweb="tab"] {{ white-space:nowrap !important; font-size:13px !important; }}
  /* Hero / banner mais compactos */
  .hero-inner {{ padding:18px 18px; }}
  .hero-chips {{ gap:7px; }}
  .hero-chip {{ font-size:11.5px; }}
  .banner-prem {{ flex-direction:column; gap:12px; }}
  .banner-prem-h {{ font-size:15px; }}
  /* 2 pills por linha no mobile (!important: a base .banner-pills vem depois) */
  .banner-pills {{ display:grid !important; grid-template-columns:1fr 1fr !important; gap:8px !important; }}
  .banner-pill {{ min-width:0 !important; padding:7px 8px; }}
  .banner-pill-m {{ font-size:10px; letter-spacing:.3px; }}
  .banner-pill-t {{ font-size:11.5px; }}
  .card-title {{ font-size:13.5px; }}
  /* Tabelas: encolhe o conteúdo (canvas não aceita font-size via CSS) p/ caber
     mais colunas. Largura compensada p/ preencher o container após o scale. */
  [data-testid="stDataFrame"] {{ transform:scale(0.82); transform-origin:top left; }}
}}
@media (max-width: 420px) {{
  .stats-row {{ grid-template-columns:1fr; }}
  .hero-value {{ font-size:24px !important; }}
  .banner-pills {{ gap:8px; }}
}}

/* ── Reveal animation (bars, rank fills) ────────────────── */
@keyframes revealFill {{
  from {{ clip-path: inset(0 100% 0 0); }}
  to   {{ clip-path: inset(0 0%   0 0); }}
}}

/* ── Progress adimplência (.prog-adim-*) ─────────────────── */
.prog-adim-wrap {{
  background: {P['surface']}; border: 1px solid {P['border']};
  border-radius: {RADIUS['md']};
  padding: 20px 24px; margin-bottom: 18px; box-shadow: {P['shadow']};
}}
.prog-adim-row {{
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 13px; gap: 12px;
}}
.prog-adim-title {{ font-size: 15px; font-weight: 600; color: {P['text']}; margin-bottom: 3px; }}
.prog-adim-sub   {{ font-size: 11.5px; color: {P['muted']}; }}
.prog-adim-pct   {{ font-size: 30px; font-weight: 700; line-height: 1; letter-spacing: -.2px; }}
.prog-adim-delta {{ font-size: 11px; font-weight: 600; margin-top: 2px; }}
.prog-adim-track {{
  height: 12px; background: {P['grid']}; border-radius: 20px;
  overflow: visible; margin-bottom: 8px; position: relative;
  box-shadow: inset 0 1px 3px rgba(0,0,0,.07);
}}
.prog-adim-fill {{
  height: 100%; border-radius: 20px;
  background: linear-gradient(90deg, {SEMANTIC['danger_500']} 0%, {ACENTO['amber']} 50%, {BRAND['500']} 100%);
  animation: revealFill 1.5s cubic-bezier(.4,0,.2,1) both .35s;
}}
.prog-adim-meta {{
  position: absolute; top: -5px; bottom: -5px; width: 2.5px;
  background: {ACENTO['amber']}; border-radius: 3px; transform: translateX(-50%);
}}
.prog-adim-meta::after {{
  content: ''; position: absolute; top: -5px; left: 50%;
  transform: translateX(-50%); border: 5px solid transparent;
  border-top-color: {ACENTO['amber']};
}}
.prog-adim-leg {{ display: flex; justify-content: space-between; font-size: 11px; color: {P['muted']}; }}

/* ── Rank list (.rank-*) ────────────────────────────────── */
.rank-list {{ list-style: none; padding: 0; margin: 4px 0 0; }}
.rank-item {{
  display: flex; align-items: center; gap: 9px;
  padding: 9px 0; border-bottom: 1px solid {P['border']};
}}
.rank-item:last-child {{ border: none; }}
.rank-n  {{ font-size: 11px; color: {P['muted']}; width: 14px; flex-shrink: 0; font-weight: 600; }}
.rank-nm {{ font-size: 12.5px; color: {P['text']}; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.rank-track {{ width: 80px; height: 5px; background: {P['border2']}; border-radius: 10px; overflow: hidden; flex-shrink: 0; }}
.rank-fill  {{
  height: 100%; border-radius: 10px;
  animation: revealFill 1.2s cubic-bezier(.4,0,.2,1) both;
}}
.rank-item:nth-child(1) .rank-fill {{ animation-delay: .10s; }}
.rank-item:nth-child(2) .rank-fill {{ animation-delay: .18s; }}
.rank-item:nth-child(3) .rank-fill {{ animation-delay: .26s; }}
.rank-item:nth-child(4) .rank-fill {{ animation-delay: .34s; }}
.rank-item:nth-child(5) .rank-fill {{ animation-delay: .42s; }}
.rank-val {{ font-size: 12px; font-weight: 600; min-width: 68px; text-align: right; flex-shrink: 0; }}

/* ── Banner premiação (.banner-prem*) ───────────────────── */
.banner-prem {{
  background: {P['surface']}; border: 1px solid {P['border']};
  border-left: 4px solid {BRAND['500']}; border-radius: {RADIUS['md']};
  padding: 16px 20px; margin-bottom: 18px; box-shadow: {P['shadow']};
  display: flex; align-items: flex-start; justify-content: space-between;
  gap: 16px; flex-wrap: wrap;
  animation: fadeUp .45s cubic-bezier(.4,0,.2,1) both .08s;
}}
.banner-prem-h {{ font-size: 16px; font-weight: 700; color: {P['text']}; margin-bottom: 4px; }}
.banner-prem-s {{ font-size: 12px; color: {P['muted']}; line-height: 1.5; max-width: 420px; }}
.banner-pills  {{ display: flex; gap: 10px; flex-wrap: wrap; }}
.banner-pill {{
  display: flex; flex-direction: column; align-items: center;
  border: 1px solid {P['border2']}; border-radius: 10px;
  padding: 10px 18px; min-width: 118px; background: {P['bg']};
}}
.banner-pill-star {{ background: {BRAND['500']}; border-color: {BRAND['500']}; }}
.banner-pill-m {{
  font-size: 11px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .5px; color: {P['muted']};
}}
.banner-pill-t {{ font-size: 13px; font-weight: 500; color: {P['text']}; margin-top: 3px; text-align: center; }}
.banner-pill-star .banner-pill-m {{ color: rgba(255,255,255,.65); }}
.banner-pill-star .banner-pill-t {{ color: #fff; font-weight: 600; }}

/* ── Card comparativo adimplência × inadimplência (.cmp-*) ─ */
.cmp-wrap {{
  background:{P['surface']}; border:1px solid {P['border']};
  border-radius:{RADIUS['lg']}; box-shadow:{P['shadow']};
  padding:18px 22px; margin-bottom:8px;
}}
.cmp-hd {{ font-size:14px; font-weight:700; color:{P['text']}; margin-bottom:2px; }}
.cmp-sub {{ font-size:12px; color:{P['muted']}; margin-bottom:14px; }}
.cmp-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
.cmp-cell {{ border:1px solid {P['border']}; border-radius:{RADIUS['md']};
  padding:14px 16px; position:relative; }}
.cmp-cell.ok  {{ border-left:4px solid {BRAND['500']}; }}
.cmp-cell.bad {{ border-left:4px solid {SEMANTIC['danger_500']}; }}
.cmp-cap {{ font-size:11.5px; font-weight:600; color:{P['label']};
  text-transform:uppercase; letter-spacing:.4px; display:flex; align-items:center; gap:6px; }}
.cmp-num {{ font-size:30px; font-weight:700; line-height:1.1; letter-spacing:-.2px; margin-top:6px; }}
.cmp-cell.ok  .cmp-num {{ color:{BRAND['600']}; }}
.cmp-cell.bad .cmp-num {{ color:{SEMANTIC['danger_700']}; }}
.cmp-pct {{ font-size:12.5px; font-weight:600; color:{P['muted']}; margin-top:3px; }}
.cmp-bar {{ height:8px; border-radius:20px; background:{P['grid']}; overflow:hidden; margin-top:18px; display:flex; }}
.cmp-bar-ok  {{ background:{BRAND['500']}; height:100%; }}
.cmp-bar-bad {{ background:{SEMANTIC['danger_500']}; height:100%; }}

/* Destaque sutil do mês atual em barras/listas (CONTEXT item 6) */
.mes-atual-badge {{ display:inline-flex; align-items:center; gap:5px;
  font-size:10.5px; font-weight:700; color:{BRAND['700']};
  background:{BRAND['50']}; border:1px solid {BRAND['100']};
  padding:2px 8px; border-radius:99px; letter-spacing:.3px; }}

/* Nota de regra discreta (CONTEXT item 5) */
.nota-regra {{ font-size:11.5px; color:{P['muted']}; margin:2px 0 10px;
  padding-left:23px; display:inline-flex; align-items:center; gap:6px; }}
.nota-regra i {{ color:{BRAND['500']}; font-size:12px; }}

/* ── Calendário de sorteios (.cal-*) ────────────────────── */
.cal-table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
.cal-table th {{
  text-align: left; padding: 8px 11px; background: {P['bg']};
  color: {P['muted']}; font-size: 10px; font-weight: 700;
  text-transform: uppercase; letter-spacing: .5px;
  border-bottom: 1px solid {P['border2']};
}}
.cal-table td {{ padding: 9px 11px; border-bottom: 1px solid {P['border']}; color: {P['text']}; }}
.cal-table tr:last-child td {{ border: none; }}
.cal-table tr:hover td {{ background: {P['hover_bg']}; }}
.cal-final-row td {{ font-weight: 600; }}
.cal-badge {{
  display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px;
  border-radius: 20px; font-size: 10.5px; font-weight: 600;
}}
.cal-done   {{ background: {BRAND['50']};              color: {BRAND['700']};              border: 1px solid {BRAND['100']}; }}
.cal-soon   {{ background: {SEMANTIC['warning_50']};   color: {SEMANTIC['warning_700']};   border: 1px solid #fde68a; }}
.cal-future {{ background: {P['neutral_bg']};          color: {P['muted']};                border: 1px solid {P['border2']}; }}
.cal-final  {{ background: {SEMANTIC['danger_50']};    color: {SEMANTIC['danger_700']};    border: 1px solid #fecaca; }}
@media (min-width: 1700px) {{
  .block-container {{ max-width:100% !important; padding:0.1rem 3rem 2.4rem !important; }}
  .ph-title {{ font-size:30px; }}
  .ph-ico {{ width:54px; height:54px; font-size:23px; }}
  .stats-row {{ gap:22px; grid-template-columns:repeat(auto-fit, minmax(260px,1fr)); }}
  .stat-card {{ padding:26px 28px; }}
  .stat-val {{ font-size:40px; letter-spacing:-.4px; }}
  .stat-label {{ font-size:14px; }}
  .stat-icon {{ width:50px; height:50px; font-size:21px; }}
  .card-title {{ font-size:16px; }}
}}
/* Respiro entre a barra de abas e o conteúdo */
.stTabs [data-baseweb="tab-panel"] {{ padding-top:10px; }}
</style>
"""


def _registrar_template_plotly(P: dict) -> None:
    tpl = go.layout.Template()
    tpl.layout = go.Layout(
        font=dict(family=FONT, color=P["label"], size=13),
        colorway=COLORWAY,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=20, t=10, b=10),
        xaxis=dict(gridcolor=P["grid"], linecolor=P["border2"], zeroline=False),
        yaxis=dict(gridcolor=P["grid"], linecolor=P["border2"], zeroline=False),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-.18),
        hoverlabel=dict(font=dict(family=FONT)),
        colorscale=dict(sequential=[[0, BRAND["100"]], [1, BRAND["600"]]]),
    )
    pio.templates["milhao"] = tpl
    pio.templates.default = "plotly_white+milhao"


def aplicar_tema() -> None:
    """Injeta CSS + registra template Plotly (sempre claro). 1x por página."""
    P = PALETAS["claro"]
    _registrar_template_plotly(P)
    st.markdown(_css(P), unsafe_allow_html=True)
