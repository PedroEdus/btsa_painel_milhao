# Identidade Visual — Painel da Campanha do Milhão

Elementos visuais coletados do frontend **CGID** (`cgid/frontend/src`), marca
**Brasil Terrenos**. Implementados em `components/theme.py` (CSS + template Plotly).

## Logos (`assets/`)

| Arquivo | Origem CGID | Uso |
|---|---|---|
| `logo_preta.png` | `logo-bt-colorido.png` | fundo claro (texto preto, casa verde, arco vermelho) |
| `logo_branca.png` | `logo-bt-branco.png` | fundo escuro |
| `logo-bt-colorido.png` | idem | logo completo colorido |
| `logo-bt-branco.png` | idem | logo completo branco |
| `logo-sidebar-full.png` | idem | logo horizontal p/ sidebar expandida |
| `logo-sidebar-icon.png` | idem | ícone (casinha) — **favicon** |

## Cores

### Brand (verde)
`50 #f5f8f6` · `100 #d8f3de` · `200 #b3e6bc` · `300 #7dd190` · `400 #4ab861`
· **`500 #2a9d45`** (primária) · `600 #1e7d34` · `700 #1a6229` · `800 #174f23`
· `900 #0f3317` · `950 #081c0d`

**Vermelho da marca** (arco do logo): `#e2231a` — destaque pontual.

### Cinzas
`0 #ffffff` · `50 #f5f5f6` · `100 #ececed` · `200 #d8d8da` · `300 #b8b8bc`
· `400 #8f8f96` · `500 #6b6b74` · `600 #4e4e57` · `700 #35353e` · `800 #232329`
· `900 #141418` · `950 #0a0a0d`

### Semânticas (50 / 500 / 700)
- **danger** `#fef2f2` / `#ef4444` / `#b91c1c`
- **warning** `#fffbeb` / `#f59e0b` / `#92400e`
- **info** `#eff6ff` / `#3b82f6` / `#1d4ed8`

## Tipografia
- Fonte: **Plus Jakarta Sans** (300–800) — Google Fonts
- Ícones: Font Awesome 6.5
- Título página: 22px / peso 800 / letter-spacing -.3px
- Valor KPI: 34–38px / peso 800 / letter-spacing -1.5px a -2px
- Label: 13px / peso 500 / cinza-500

## Tokens de forma
- Raios: `sm 6px` · `md 10px` · `lg 14px` · `xl 20px`
- Sombras: `sm 0 1px 3px rgba(0,0,0,.06)` · `md 0 6px 18px rgba(0,0,0,.08)` · `xl 0 20px 60px rgba(0,0,0,.14)`
- Easing: `cubic-bezier(.4,0,.2,1)` · transições 150ms / 220ms

## Padrões de componente (do CGID)

- **KPI card** (`.stat-card`): fundo branco, borda cinza-100, radius 14px, barra
  de acento 3px no topo (gradiente brand), ícone em wrap colorido, hover lift -2px.
  → aplicado em `[data-testid="stMetric"]`.
- **Card** (`.card`): header (título 14/700 + sub 12/cinza-400) + body, shadow-sm.
- **Badge/pill**: radius 99px, 11px/600, par fundo-50 + texto-700 por categoria.
- **Botão primário**: gradiente `brand-400→brand-600`, branco, shadow verde, hover lift.
- **Input**: h40-44, fundo cinza-50, foco borda brand-500 + ring `rgba(42,157,69,.12)`.
- **Tabela**: header uppercase 11px cinza-400 fundo cinza-50; linhas hover cinza-50.
- **Modal**: overlay blur, box radius-xl, slide-in.
- **Tabs** (`.cfg-tab`): borda inferior 2px brand-500 no ativo.
- **Toggle**: switch 36x20, ativo brand-500.
- **Login**: painel esquerdo gradiente `brand-600→brand-900`, grid verde sutil.
- **Sidebar**: fundo claro com radial-gradient verde sutil + grid 8px; link ativo
  branco com barra lateral brand-500.

## Onde está no código
- `components/theme.py` — `BRAND`, `GRAY`, `SEMANTIC`, `BRAND_RED`, `RADIUS`,
  `SHADOW`, `COLORWAY`, `aplicar_tema()`, template Plotly `milhao`.
- `.streamlit/config.toml` — `primaryColor #2a9d45`.
- `cabecalho()` aplica o tema no topo de cada página.
