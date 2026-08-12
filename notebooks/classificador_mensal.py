# Notebook Fabric - Classificador mensal da base completa (Painel do Milhao)
# Versao Fabric do scripts/classificador_julho_2026.py (que lia o export
# xlsx local): aqui a fonte e a TABELA Delta base_oficial_<mes> do
# lakehouse (gerada pelo dataflow mensal com a query do mes fechado).
# Saida: base COMPLETA do mes (~98k linhas, sem filtro de elegibilidade)
# com Classificacao + Diagnostico, e um resumo por classe.
# Classes (ordem de prioridade):
#   DISTRATADO   = [Distrato Apos Fechamento] = 1. Na saida, as duas
#                  aptidoes sao forcadas para NAO APTO.
#   CESSAO       = movimento de cessao DENTRO do mes analisado:
#                  [Data Cedida] no mes (contrato cedido) ou [Data Cessao]
#                  no mes (venda nova por transferencia). Cessao de outro
#                  mes pagando normal NAO conta.
#   QUITADO      = [Contrato Quitado] = Sim.
#   INADIMPLENTE = [Aptidao Sorteio] diferente de APTO.
#   ADIMPLENTE   = demais.
# Virada de mes: editar so a CELL 1 (MES_REF, TABELA_BASE_OFICIAL).
# Requisitos: lakehouse lh_bronze_campanha_1m anexado como padrao.
# Saidas: Files/painel_milhao/sorteio/<MES_REF>/ (CONTEM CPF - manter no
# lakehouse, compartilhar somente por canal seguro; nao imprimir CPF).

# ============================================================
# CELL 1 - Parametros do mes + funcoes de apoio
# ============================================================
import os
import re
import unicodedata

import pandas as pd

RAIZ_LAKE = '/lakehouse/default/'

# ---- TROCAR A CADA FECHAMENTO ------------------------------------
MES_REF = '07_2026'
TABELA_BASE_OFICIAL = 'base_oficial_07_2026'
# ------------------------------------------------------------------

PASTA_SAIDA = f'Files/painel_milhao/sorteio/{MES_REF}/'

_mes, _ano = MES_REF.split('_')
INI_MES = pd.Timestamp(int(_ano), int(_mes), 1)
PROX_MES = INI_MES + pd.offsets.MonthBegin(1)


def sem_acento(texto):
    nfd = unicodedata.normalize('NFD', str(texto))
    return ''.join(c for c in nfd if not unicodedata.combining(c))


def para_numero(valor):
    """'R$ 1.234,56', '1.234,56' ou numero puro -> float."""
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


def normaliza_status(valor):
    if pd.isna(valor):
        return ''
    return sem_acento(valor).upper().strip()


def eh_sim(valor):
    return normaliza_status(valor) == 'SIM'


def para_data(valor):
    """datetime, 'dd/mm/aaaa' ou 'yyyymmdd' -> Timestamp (NaT se vazio)."""
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, pd.Timestamp):
        return valor
    s = str(valor).strip()
    if s == '':
        return pd.NaT
    if re.fullmatch(r'\d{8}', s):
        return pd.to_datetime(s, format='%Y%m%d', errors='coerce')
    return pd.to_datetime(s, dayfirst=True, errors='coerce')


def fmt_data(d):
    return d.strftime('%d/%m/%Y') if pd.notna(d) else ''


def acha_coluna(df, nome_alvo, obrigatoria=True):
    """Match ignorando acento, caixa, espaco, underscore e ponto.
    Cobre as 3 grafias possiveis: query ('Aptidao Casas'), Delta
    sanitizada ('Aptidao_Casas') e pipeline da viva ('aptidao_casas')."""
    alvo = sem_acento(nome_alvo).lower().replace(' ', '').replace('_', '').replace('.', '')
    for c in df.columns:
        if sem_acento(c).lower().replace(' ', '').replace('_', '').replace('.', '') == alvo:
            return c
    if obrigatoria:
        raise SystemExit(
            f'Coluna [{nome_alvo}] nao encontrada. Colunas: {list(df.columns)}'
        )
    return None


print('Parametros ok.')
print(f'Mes de referencia: {MES_REF} ({fmt_data(INI_MES)} a {fmt_data(PROX_MES - pd.Timedelta(days=1))})')
print(f'Base oficial:      tabela {TABELA_BASE_OFICIAL}')

# ============================================================
# CELL 2 - Carga da tabela e mapeamento de colunas
# ============================================================
base = spark.read.table(TABELA_BASE_OFICIAL).toPandas()
print(f'Base oficial: {len(base)} linhas, {len(base.columns)} colunas')

col = {campo: acha_coluna(base, campo) for campo in (
    'CodEmpresa', 'CodObra', 'Venda', 'NomeCliente', 'cpf_pes',
    'Aptidao Casas', 'Aptidao Sorteio', 'Valor Recebido',
    'Cupons Milhao', 'Cupons Casas', 'Dt Venda',
    'Data Cedida', 'Data Cessao', 'Contrato Quitado',
)}
col_opcional = {campo: acha_coluna(base, campo, obrigatoria=False) for campo in (
    'Distrato Apos Fechamento', 'Motivo', 'Data Ultimo Recebimento',
)}
for campo, c in col_opcional.items():
    if c is None:
        print(f'AVISO: coluna [{campo}] ausente na tabela - seguindo sem ela.')

# ============================================================
# CELL 3 - Classificacao
# ============================================================
dt_cedida = base[col['Data Cedida']].map(para_data)
dt_cessao = base[col['Data Cessao']].map(para_data)
dt_venda = base[col['Dt Venda']].map(para_data)

c_ult = col_opcional['Data Ultimo Recebimento']
dt_ult = base[c_ult].map(para_data) if c_ult else pd.Series(pd.NaT, index=base.index)

cedida_no_mes = (dt_cedida >= INI_MES) & (dt_cedida < PROX_MES)
cessao_no_mes = (dt_cessao >= INI_MES) & (dt_cessao < PROX_MES)
quitado = base[col['Contrato Quitado']].map(eh_sim)
apto_sorteio = base[col['Aptidao Sorteio']].map(normaliza_status) == 'APTO'

c_dpf = col_opcional['Distrato Apos Fechamento']
distratado = (
    base[c_dpf].astype(str).str.strip().isin(('1', '1.0'))
    if c_dpf else pd.Series(False, index=base.index)
)

classif = pd.Series('ADIMPLENTE', index=base.index)
classif[~apto_sorteio] = 'INADIMPLENTE'
classif[quitado] = 'QUITADO'
classif[cedida_no_mes | cessao_no_mes] = 'CESSAO'
classif[distratado] = 'DISTRATADO'

# Distrato pos-fechamento sai NAO APTO nas duas reguas
apt_casas_out = base[col['Aptidao Casas']].fillna('').astype(str).str.strip()
apt_sorteio_out = base[col['Aptidao Sorteio']].fillna('').astype(str).str.strip()
apt_casas_out[distratado] = 'NÃO APTO'
apt_sorteio_out[distratado] = 'NÃO APTO'

c_motivo = col_opcional['Motivo']
motivo = (
    base[c_motivo].fillna('').astype(str).str.strip()
    if c_motivo else pd.Series('', index=base.index)
)


def diagnostico(i):
    c = classif.at[i]
    ult = fmt_data(dt_ult.at[i])
    suf_ult = f' — último recebimento {ult}' if ult else ' — sem recebimento na janela'
    if c == 'DISTRATADO':
        return 'Distrato após fechamento — marcado NÃO APTO'
    if c == 'CESSAO':
        partes = []
        if cedida_no_mes.at[i]:
            partes.append(f'contrato cedido em {fmt_data(dt_cedida.at[i])}')
        if cessao_no_mes.at[i]:
            partes.append(f'venda nova por cessão em {fmt_data(dt_cessao.at[i])}')
        return ('Cessão no mês: ' + ' e '.join(partes)).capitalize()
    if c == 'QUITADO':
        return f'Contrato quitado{suf_ult}'
    if c == 'INADIMPLENTE':
        m = motivo.at[i]
        base_txt = m.capitalize() if m and normaliza_status(m) != 'ADIMPLENTE' else 'Não apto no sorteio'
        return f'{base_txt}{suf_ult}'
    return f'Em dia{suf_ult}'


diag = pd.Series([diagnostico(i) for i in base.index], index=base.index)

# ============================================================
# CELL 4 - Saida unica (CSV no lakehouse) + resumo impresso +
# diagnostico de 1 linha
# ============================================================
saida = pd.DataFrame({
    'CodEmpresa': base[col['CodEmpresa']],
    'CodObra': base[col['CodObra']],
    'Venda': base[col['Venda']],
    'NomeCliente': base[col['NomeCliente']],
    'CPF': base[col['cpf_pes']],
    'Aptidao Casas': apt_casas_out,
    'Aptidao Sorteio': apt_sorteio_out,
    'Valor Recebido': base[col['Valor Recebido']].map(para_numero),
    'Cupons Milhao': base[col['Cupons Milhao']].map(para_numero).round(0).astype(int),
    'Cupons Casas': base[col['Cupons Casas']].map(para_numero).round(0).astype(int),
    'Data Venda': dt_venda.map(fmt_data),
    'Classificacao': classif,
    'Diagnostico': diag,
})

os.makedirs(RAIZ_LAKE + PASTA_SAIDA, exist_ok=True)
arquivo = f'{PASTA_SAIDA}base_completa_classificada_{MES_REF}.csv'
saida.to_csv(RAIZ_LAKE + arquivo, index=False, sep=';',
             encoding='utf-8-sig', decimal=',')

ordem = ['DISTRATADO', 'CESSAO', 'QUITADO', 'INADIMPLENTE', 'ADIMPLENTE']
resumo = (
    saida.groupby('Classificacao')
    .agg(Contratos=('Venda', 'size'), Valor_Recebido=('Valor Recebido', 'sum'),
         Cupons_Milhao=('Cupons Milhao', 'sum'), Cupons_Casas=('Cupons Casas', 'sum'))
    .reindex(ordem)
    .fillna(0)
)
for _c in ('Contratos', 'Cupons_Milhao', 'Cupons_Casas'):
    resumo[_c] = resumo[_c].astype(int)
resumo['Pct'] = (100 * resumo['Contratos'] / len(saida)).round(2)

print('RESUMO:')
print(resumo.to_string())
print()
partes = ' '.join(f'{k}={int(v)}' for k, v in resumo['Contratos'].items())
print(f'DIAG {MES_REF}: {len(saida)} linhas gravadas | {partes} | {arquivo}')
print('Arquivos contem CPF - manter no lakehouse (acesso restrito).')
