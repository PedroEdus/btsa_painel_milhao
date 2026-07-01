"""Configuração central do Painel da Campanha do Milhão.

Carrega variáveis de ambiente (.env local ou st.secrets em produção) e expõe
os parâmetros da campanha e as regras de cupom como objetos imutáveis.

Regras de negócio ainda pendentes (ver CONTEXT seção 13) ficam como PARÂMETROS
aqui, nunca como constantes espalhadas pelo código.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date

from dotenv import load_dotenv

load_dotenv()


def _env_bool(nome: str, padrao: bool) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _env_int(nome: str, padrao: int) -> int:
    valor = os.getenv(nome)
    return int(valor) if valor and valor.strip().isdigit() else padrao


# ── Janela de atualização ───────────────────────────────────────────────────
# A base do Fabric é atualizada às 8h e 15h (horário de Brasília). O painel só
# recarrega dados nessas fronteiras — não há TTL fixo.
TZ_BR = "America/Sao_Paulo"
HORARIOS_ATUALIZACAO: tuple[int, ...] = (8, 15)
# Margem (min) após o horário nominal p/ o pipeline terminar de gravar o
# snapshot antes de o painel buscar dados novos → busca efetiva 8h20/15h20.
ATUALIZACAO_MARGEM_MINUTOS: int = _env_int("ATUALIZACAO_MARGEM_MINUTOS", 20)

# Limite de cupons disponíveis pela receita da empresa (teto = 100% do medidor).
# 0 = automático: estima pelo potencial dos dados (recebido + vencido) / R$100.
CUPONS_DISPONIVEIS: int = _env_int("CUPONS_DISPONIVEIS", 0)


def _env_list(nome: str) -> tuple[str, ...]:
    """Lê uma lista separada por vírgula de uma env var. Vazio → tupla vazia."""
    bruto = os.getenv(nome, "") or ""
    return tuple(item.strip().lower() for item in bruto.split(",") if item.strip())


# ── Controle de acesso (CONTEXT 15) ─────────────────────────────────────────
# Domínios e e-mails autorizados configuráveis via env/secrets — NUNCA hardcode.
# Fallback p/ btsa.com.br mantém compatibilidade com a auth atual.
ALLOWED_EMAIL_DOMAINS: tuple[str, ...] = _env_list("ALLOWED_EMAIL_DOMAINS") or (
    "btsa.com.br",
)
ALLOWED_EMAILS: tuple[str, ...] = _env_list("ALLOWED_EMAILS")


@dataclass(frozen=True)
class RegraCupom:
    """Parâmetros da geração de cupom (CONTEXT seção 5).

    Decisão Pedro: cupom sobre TODO valor que entra no caixa da Buriti.
    Componentes ficam separados p/ auditoria; flags controlam o que entra no
    valor elegível até o regulamento fechar (custas pendente — seção 13).
    """

    versao: str = "v1-2026-06"  # registrar versão da regra (CONTEXT decisão 12)
    valor_por_cupom: float = 100.0
    incluir_principal: bool = True
    incluir_multa: bool = True
    incluir_juros: bool = True
    incluir_custas: bool = _env_bool("CUPOM_INCLUIR_CUSTAS", True)
    # Arredondamento: só blocos completos de R$100 (hipótese do CONTEXT 5.1).
    # PENDENTE confirmar saldo residual (<R$100) — descarta por ora.
    apenas_blocos_completos: bool = True

    @property
    def componentes_elegiveis(self) -> tuple[str, ...]:
        comps: list[str] = []
        if self.incluir_principal:
            comps.append("valor_principal")
        if self.incluir_multa:
            comps.append("valor_multa")
        if self.incluir_juros:
            comps.append("valor_juros")
        if self.incluir_custas:
            comps.append("valor_custas")
        return tuple(comps)


@dataclass(frozen=True)
class Campanha:
    nome: str = "Campanha do Milhão"
    empresa: str = "Brasil Terrenos"
    inicio: date = date(2026, 7, 1)
    fim: date = date(2026, 12, 31)
    qtd_sorteios_mensais: int = 5
    premio_final_reais: float = 1_000_000.0
    # Meta de arrecadação exibida no painel — PENDENTE definir com negócio (seção 13)
    meta_arrecadacao: float = field(default_factory=lambda: float(os.getenv("META_ARRECADACAO", "0") or 0))


REGRA_CUPOM = RegraCupom()
CAMPANHA = Campanha()
