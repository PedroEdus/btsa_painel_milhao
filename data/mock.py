"""Gerador de dados mock fiéis ao contrato (CONTEXT Etapa 3).

Usado enquanto a view do Fabric não existe. Mesma estrutura/colunas que a
view real, para que toda a camada de métricas e visual já funcione e seja
trocada por dados reais sem mexer no painel.

NUNCA apresentar estes números como cupons oficiais (CONTEXT 14.3): a coluna
cupons_oficiais vem nula no mock de propósito.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config.settings import CAMPANHA
from data.contract import COLUNAS

_RNG = np.random.default_rng(42)

_EMPRESAS = ["Brasil Terrenos"]
_OBRAS = ["Residencial Aurora", "Parque das Águas", "Vale Verde", "Solar do Campo"]
_CIDADES = {"Residencial Aurora": "Goiânia", "Parque das Águas": "Aparecida",
            "Vale Verde": "Anápolis", "Solar do Campo": "Trindade"}
_TIPOS = ["regular", "vencida", "negociacao", "antecipacao", "quitacao"]
_ORIGENS = ["boleto", "pix", "cartao", "transferencia"]


def gerar(n_vendas: int = 600) -> pd.DataFrame:
    """Gera ~n_vendas vendas distribuídas pelos meses da campanha."""
    meses = pd.period_range(CAMPANHA.inicio, CAMPANHA.fim, freq="M").astype(str).tolist()
    linhas: list[dict] = []

    for i in range(n_vendas):
        obra = _RNG.choice(_OBRAS)
        venda = f"V{100000 + i}"
        cpf = f"{_RNG.integers(0, 999999999):09d}"
        nome = f"Cliente {i:04d}"
        compradores = int(_RNG.choice([1, 1, 1, 2], p=[0.7, 0.15, 0.1, 0.05]))
        cadastrado = bool(_RNG.random() < 0.65)

        # cada venda paga em 1..4 meses
        for mes in _RNG.choice(meses, size=int(_RNG.integers(1, 5)), replace=False):
            tipo = _RNG.choice(_TIPOS)
            vencido = tipo in {"vencida", "quitacao"}
            recuperacao = vencido and _RNG.random() < 0.8

            principal = float(_RNG.integers(100, 5000))
            multa = round(principal * _RNG.uniform(0, 0.02), 2) if vencido else 0.0
            juros = round(principal * _RNG.uniform(0, 0.05), 2) if vencido else 0.0
            custas = round(_RNG.uniform(0, 50), 2) if vencido else 0.0
            total = round(principal + multa + juros + custas, 2)

            linhas.append({
                "empresa": "Brasil Terrenos",
                "obra": obra,
                "cidade": _CIDADES[obra],
                "produto": f"Lote {obra}",
                "num_venda": venda,
                "cpf_titular": cpf,
                "nome_cliente": nome,
                "telefone": f"62 9{_RNG.integers(10000000, 99999999)}",
                "email": f"cliente{i:04d}@exemplo.com",
                "titular_principal": True,
                "qtd_compradores": compradores,
                "data_recebimento": pd.Timestamp(mes + "-15"),
                "mes_referencia": mes,
                "valor_principal": principal,
                "valor_multa": multa,
                "valor_juros": juros,
                "valor_custas": custas,
                "valor_total_recebido": total,
                "tipo_parcela": tipo,
                "origem_pagamento": _RNG.choice(_ORIGENS),
                "flag_antecipacao": tipo == "antecipacao",
                "flag_negociacao": tipo == "negociacao",
                "flag_vencido": vencido,
                "qtd_parcelas_pagas": int(_RNG.integers(1, 4)),
                "status_cadastro": "cadastrado" if cadastrado else "nao_cadastrado",
                "status_elegibilidade": "elegivel" if cadastrado else "pendente",
                "motivo_bloqueio": "" if cadastrado else "sem_cadastro",
                "cupons_oficiais": pd.NA,  # mock NUNCA simula oficial
                "flag_contemplado_casa": False,
                "participa_proximos_sorteios": True,
                "data_ultima_atualizacao": pd.Timestamp.now(),
                "status_inadimplencia_antes": "inadimplente" if vencido else "adimplente",
                "dias_atraso": int(_RNG.integers(1, 180)) if vencido else 0,
                "qtd_parcelas_vencidas": int(_RNG.integers(1, 6)) if vencido else 0,
                "valor_vencido_antes": total if vencido else 0.0,
                "valor_recuperado": total if recuperacao else 0.0,
                "status_apos_pagamento": "adimplente",
                "classificacao_recebimento": "recuperacao" if recuperacao else "normal",
            })

    df = pd.DataFrame(linhas)
    # garantir dtypes do contrato
    for col, dtype in COLUNAS.items():
        if col in df.columns:
            try:
                df[col] = df[col].astype(dtype)
            except (TypeError, ValueError):
                pass
    return df
