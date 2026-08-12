"""Validacao do fechamento de julho/2026 - base = snapshot de 31/07.

Cruza os 97.450 contratos do snapshot com a apuracao retroativa v2
(Excel exportado do SSMS, universo completo com status/distrato) e
entrega 1 status para CADA contrato do snapshot. O que a apuracao traz
a mais (historico de canceladas/quitadas antigas) e descartado.

Uso:
    python scripts/gera_validacao_julho.py \
        --apuracao caminho/Validacao.xlsx \
        [--snapshot painel_milhao_snapshot_20260731.parquet]

Saida: saidas/validacao_julho_contratos.csv e .xlsx (contem CPF -
pasta fora do git, compartilhar so por canal seguro).
"""

import argparse
import os
import unicodedata

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COLS_APURACAO = [
    'Valor Gera Cupom Julho', 'Valor Recebido Julho', 'Cupons Casas Julho',
    'Ultimo Recebimento Julho',
    'Status Fechamento Julho', 'Motivo', 'Pgto 30-31/07', 'Fonte Venda',
    'Status Venda', 'Distrato Aprovado', 'Classificacao Distrato',
    'Tipo Distrato', 'Categoria Distrato', 'Motivo Distrato',
    'Data Geracao Distrato', 'Data Aprovacao Distrato',
    'Distrato Apos Fechamento', 'Cessao Hist', 'Renegociacao Hist',
]


def sem_acento(t):
    nfd = unicodedata.normalize('NFD', str(t))
    return ''.join(c for c in nfd if not unicodedata.combining(c))


def para_numero(valor):
    """Converte 'R$ 1.234,56', '5.000000' ou numero puro em float."""
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    t = str(valor).replace('R$', '').replace('\xa0', '').strip()
    if ',' in t:
        t = t.replace('.', '').replace(',', '.')
    try:
        return float(t)
    except ValueError:
        return 0.0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apuracao', required=True)
    parser.add_argument(
        '--snapshot',
        default=os.path.join(RAIZ, 'painel_milhao_snapshot_20260731.parquet'),
    )
    args = parser.parse_args()

    snap = pd.read_parquet(args.snapshot)
    apur = pd.read_excel(args.apuracao)

    # Correcao de escala: import de numerico com 6 casas no Excel pt-BR
    # engole o ponto decimal (fator 1e6). Detecta pela razao com cupons.
    val = pd.to_numeric(apur['Valor Gera Cupom Julho'], errors='coerce')
    cup = pd.to_numeric(apur['Cupons Casas Julho'], errors='coerce')
    razao = val.sum() / max(cup.sum() * 100, 1)
    if razao > 1000:
        apur['Valor Gera Cupom Julho'] = val / 1_000_000
        print(f'Valor Gera Cupom corrigido /1e6 (razao detectada: {razao:,.0f})')

    # Base = snapshot; apuracao entra por join. Excesso da apuracao cai fora.
    # Colunas-chave do parquet que o operador do sorteio usa: identificacao
    # do lote/empreendimento, cupons gerados (Milhao acumulado + Casas do
    # mes), valores de recebimento e contato do cliente.
    base = pd.DataFrame({
        'CodEmpresa': pd.to_numeric(snap['codempresa']).astype('Int64'),
        'CodObra': snap['codobra'].astype(str).str.strip(),
        'Venda': pd.to_numeric(snap['venda']).astype('Int64'),
        'NomeCliente': snap['nomecliente'],
        'CPF': snap['cpf_pes'],
        'EmailCliente': snap['emailcliente'],
        'Telefone': snap['telefoneformatado'],
        'Empreendimento': snap['nomeobra'],
        'Identificador Lote': snap['identificador'],
        'Produto': snap['produto'],
        'Cidade': snap['cidade'],
        'Regional': snap['regional'],
        'Status Foto 31/07': snap['status_sorteio'].map(
            lambda v: sem_acento(v).upper().strip()),
        'Cupons Foto 31/07': pd.to_numeric(snap['cupons_casas'], errors='coerce'),
        'Cupons Milhao Foto 31/07': snap['cupons_milhao'].map(para_numero).astype(int),
        'Valor Gera Cupom Foto 31/07': snap['valor_gera_cupom'].map(para_numero),
        'Valor Recebido Foto 31/07': snap['valor_recebido'].map(para_numero),
        'Data Ultimo Recebimento Foto': snap['data_ultimo_recebimento'],
    })

    apur = apur.copy()
    apur['CodEmpresa'] = pd.to_numeric(apur['CodEmpresa']).astype('Int64')
    apur['CodObra'] = apur['CodObra'].astype(str).str.strip()
    apur['Venda'] = pd.to_numeric(apur['Venda']).astype('Int64')

    chave = ['CodEmpresa', 'CodObra', 'Venda']
    cols = [c for c in COLS_APURACAO if c in apur.columns]
    faltantes = set(COLS_APURACAO) - set(cols)
    if faltantes:
        print(f'AVISO: colunas ausentes no export (seguindo sem): {sorted(faltantes)}')
    m = base.merge(apur[chave + cols], on=chave, how='left')

    sem_status = m['Status Fechamento Julho'].isna()
    status_apur = m['Status Fechamento Julho'].fillna('').str.strip()

    m['Resgatado Baixa Tardia'] = (
        (m['Status Foto 31/07'] == 'NAO APTO') & (status_apur == 'APTO')
    ).astype(int)
    m['Perdeu Aptidao'] = (
        (m['Status Foto 31/07'] == 'APTO') & (status_apur == 'NAO APTO')
    ).astype(int)

    # Status consolidado do contrato para leitura rapida
    def situacao(row):
        if pd.isna(row['Status Fechamento Julho']):
            return 'SEM RETORNO NA APURACAO - INVESTIGAR'
        if row['Distrato Aprovado'] == 'Sim' and row['Distrato Apos Fechamento'] == 1:
            return 'DISTRATADA APOS FECHAMENTO - DECISAO PENDENTE'
        if row['Distrato Aprovado'] == 'Sim':
            return 'DISTRATADA'
        if row['Status Venda'] == 'QUITADA':
            return 'QUITADA - ' + row['Status Fechamento Julho']
        return row['Status Fechamento Julho']

    m['Situacao Contrato'] = m.apply(situacao, axis=1)

    m = m.sort_values(
        ['Situacao Contrato', 'Resgatado Baixa Tardia', 'NomeCliente'],
        ascending=[True, False, True],
    )

    pasta = os.path.join(RAIZ, 'saidas')
    os.makedirs(pasta, exist_ok=True)
    m.to_csv(os.path.join(pasta, 'validacao_julho_contratos.csv'),
             index=False, sep=';', encoding='utf-8-sig')
    m.to_excel(os.path.join(pasta, 'validacao_julho_contratos.xlsx'), index=False)

    print()
    print('=== VALIDACAO JULHO - BASE SNAPSHOT 31/07 ===')
    print(f'Contratos no snapshot:        {len(base):>8}')
    print(f'Com status na apuracao:       {int((~sem_status).sum()):>8}')
    print(f'SEM retorno (investigar):     {int(sem_status.sum()):>8}')
    print(f'Descartados da apuracao:      {len(apur) - int((~sem_status).sum()):>8}')
    print()
    print('Situacao Contrato:')
    for k, v in m['Situacao Contrato'].value_counts().items():
        print(f'  {k:<48} {v:>8}')
    print()
    resg = m[m['Resgatado Baixa Tardia'] == 1]
    print(f'Resgatados baixa tardia: {int(m["Resgatado Baixa Tardia"].sum())}')
    print(f'  por Status Venda: {resg["Status Venda"].value_counts().to_dict()}')
    print(f'  com Pgto 30-31/07: '
          f'{int(pd.to_numeric(resg["Pgto 30-31/07"], errors="coerce").fillna(0).sum())}')
    print(f'Perderam aptidao:        {int(m["Perdeu Aptidao"].sum())}')
    print()

    if sem_status.any():
        print('Contratos SEM retorno na apuracao (chaves para investigar na origem):')
        print(m.loc[sem_status, ['CodEmpresa', 'CodObra', 'Venda',
                                 'Status Foto 31/07', 'Cupons Foto 31/07']]
              .to_string(index=False))
        print()

    teste = m[m['Categoria Distrato'].astype(str).str.contains(
        'TESTE', case=False, na=False)]
    if len(teste):
        print(f'Vendas de TESTE do ERP no snapshot (excluir do sorteio): '
              f'{len(teste)} | cupons na foto: {teste["Cupons Foto 31/07"].sum():.0f}')
        print()
    print('Categoria Distrato (contratos do snapshot com distrato):')
    com_dist = m[m['Distrato Aprovado'] == 'Sim']
    for k, v in com_dist['Categoria Distrato'].value_counts(dropna=False).head(10).items():
        print(f'  {str(k):<48} {v:>8}')
    print()
    print('Cessao Hist=Sim:', int((m['Cessao Hist'] == 'Sim').sum()),
          '| Renegociacao Hist=Sim:', int((m['Renegociacao Hist'] == 'Sim').sum()))
    print()
    print('Arquivos: saidas/validacao_julho_contratos.csv | .xlsx (contem CPF)')


if __name__ == '__main__':
    main()
