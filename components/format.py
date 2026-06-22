"""Formatação BR de moeda/número/percentual + mascaramento de dados sensíveis.

Ponto único de formatação do painel (CONTEXT 20): moeda R$ 1.234.567,89,
percentual com vírgula, número com separador de milhar em ponto. Mascaramento
de CPF/telefone/e-mail p/ telas executivas (CONTEXT 15 — LGPD).
"""

from __future__ import annotations


def moeda(valor: float) -> str:
    return (
        f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )


def numero(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def moeda_compacta(valor: float) -> str:
    """Moeda abreviada p/ cards estreitos: R$ 3,14 bi · R$ 86,8 mi · R$ 12 mil."""
    v = float(valor or 0)
    if abs(v) >= 1_000_000_000:
        s = f"R$ {v / 1_000_000_000:.2f} bi"
    elif abs(v) >= 1_000_000:
        s = f"R$ {v / 1_000_000:.1f} mi"
    elif abs(v) >= 1_000:
        s = f"R$ {v / 1_000:.0f} mil"
    else:
        return moeda(v)
    return s.replace(".", ",")


def percentual(valor: float, casas: int = 1) -> str:
    """Percentual em padrão BR: 12,3%. `valor` já em escala 0-100."""
    return f"{valor:.{casas}f}%".replace(".", ",")


def percentual_seguro(parte: float, total: float, casas: int = 1) -> str:
    """Percentual de participação com proteção contra divisão por zero.

    Retorna string BR (ex.: '12,3%'). Se total==0 ou inválido → '0,0%'.
    """
    pct = pct_valor(parte, total)
    return percentual(pct, casas)


def pct_valor(parte: float, total: float) -> float:
    """Razão parte/total em escala 0-100, segura contra divisão por zero."""
    try:
        if not total:
            return 0.0
        return 100.0 * float(parte) / float(total)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


# ── Mascaramento de dados sensíveis (CONTEXT 15) ─────────────────────────────
def mascarar_cpf(cpf: str | None) -> str:
    """CPF → ***.***.***-XX (mantém só os 2 últimos dígitos)."""
    if not cpf:
        return ""
    digitos = "".join(ch for ch in str(cpf) if ch.isdigit())
    if len(digitos) < 2:
        return "***.***.***-**"
    return f"***.***.***-{digitos[-2:]}"


def mascarar_telefone(tel: str | None) -> str:
    """Telefone → mantém DDD + 2 primeiros e 2 últimos: (62) 9****-**21."""
    if not tel:
        return ""
    digitos = "".join(ch for ch in str(tel) if ch.isdigit())
    if len(digitos) < 4:
        return "****"
    return f"{digitos[:2]} {digitos[2:3]}****-**{digitos[-2:]}"


def mascarar_email(email: str | None) -> str:
    """E-mail → primeira letra + *** + domínio: c***@exemplo.com."""
    if not email or "@" not in str(email):
        return ""
    usuario, dominio = str(email).split("@", 1)
    if not usuario:
        return f"***@{dominio}"
    return f"{usuario[0]}***@{dominio}"
