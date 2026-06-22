"""Contrato de dados da view de consumo (CONTEXT seção 6/7).

Fonte única de verdade dos nomes/tipos de coluna esperados do Fabric.
O painel depende DESTE contrato, mesmo que a origem ainda mude (CONTEXT Etapa 2).
A validação (services/validation.py) confere a view real contra este contrato.

Granularidade: empresa x obra x venda x cpf_titular x mes_referencia.
"""

from __future__ import annotations

# coluna -> dtype pandas esperado
COLUNAS: dict[str, str] = {
    # 6.1 Identificação venda/cliente
    "empresa": "string",
    "obra": "string",
    "cidade": "string",
    "produto": "string",
    "num_venda": "string",
    "cpf_titular": "string",
    "nome_cliente": "string",
    "telefone": "string",
    "email": "string",
    "titular_principal": "boolean",
    "qtd_compradores": "Int64",
    # 6.2 Financeiro
    "data_recebimento": "datetime64[ns]",
    "mes_referencia": "string",          # competência da campanha (YYYY-MM)
    "valor_principal": "Float64",
    "valor_multa": "Float64",
    "valor_juros": "Float64",
    "valor_custas": "Float64",
    "valor_total_recebido": "Float64",
    "tipo_parcela": "string",
    "origem_pagamento": "string",
    "flag_antecipacao": "boolean",
    "flag_negociacao": "boolean",
    "flag_vencido": "boolean",
    "qtd_parcelas_pagas": "Int64",
    # 6.3 Elegibilidade / cupons
    "status_cadastro": "string",         # cadastrado | nao_cadastrado
    "status_elegibilidade": "string",    # elegivel | bloqueado | pendente
    "motivo_bloqueio": "string",
    "cupons_oficiais": "Int64",          # nullable — só quando integração externa
    "flag_contemplado_casa": "boolean",
    "participa_proximos_sorteios": "boolean",
    "data_ultima_atualizacao": "datetime64[ns]",
    # 6.4 Inadimplência
    "status_inadimplencia_antes": "string",
    "dias_atraso": "Int64",
    "qtd_parcelas_vencidas": "Int64",
    "valor_vencido_antes": "Float64",
    "valor_recuperado": "Float64",
    "status_apos_pagamento": "string",
    "classificacao_recebimento": "string",  # normal | recuperacao
}

# Chave da venda (não duplicar cupom por múltiplos compradores — CONTEXT 5.8/14.2)
CHAVE_VENDA: tuple[str, ...] = ("empresa", "obra", "num_venda")
# Chave de grão do consumo
CHAVE_GRAO: tuple[str, ...] = ("empresa", "obra", "num_venda", "cpf_titular", "mes_referencia")

# Colunas obrigatórias (sem elas o painel não roda)
OBRIGATORIAS: tuple[str, ...] = (
    "empresa", "obra", "num_venda", "cpf_titular", "mes_referencia",
    "valor_principal", "valor_multa", "valor_juros", "valor_custas",
    "valor_total_recebido", "status_cadastro", "status_elegibilidade",
)
