# Notebook Fabric - Lista do sorteio mensal + validacoes (Painel do Milhao)
# Arquitetura (11/08/2026, revisada apos decisao de gravar a query mensal
# em TABELA do lakehouse):
#   FONTE DA LISTA  = tabela base_oficial_<mes> (Delta, gerada pelo
#     dataflow mensal com sql/query_sorteio_milhao_julho.sql - janelas
#     travadas no mes fechado, apto retroativo, regras de cessao).
#     A LISTA NAO sai da tabela viva: em agosto a viva ja mostra cupons
#     Casas de agosto - o sorteio de julho precisa da base de julho.
#   COMPARACAO 1 (LEGADO, so julho/2026) = foto parquet batida em 31/07
#     -> auditoria da transicao: pagamentos retroativos que a foto nao
#     viu, mudancas de aptidao, entradas por motivo. A partir de agosto
#     NAO existe mais foto parquet mensal - a tabela base_oficial_<mes>
#     E a foto oficial (reconstruida apos as baixas). Deixar o caminho
#     vazio ('') pula esta comparacao.
#   COMPARACAO 2    = tabela VIVA do OneLake (sempre) -> reconciliacao:
#     contratos da base oficial que ja sairam da viva (cessao/distrato
#     apos o fechamento) e vice-versa.
# Regras de elegibilidade (decisoes 11/08/2026):
#   Casas  = [Aptidao Casas] APTO + Cupons Casas > 0
#   Milhao = [Aptidao Sorteio] APTO + Cupons Milhao > 0
#   Distrato pos-fechamento ja sai NAO APTO na propria query mensal.
# Virada de mes: editar so a CELL 1 (MES_REF, TABELA_BASE_OFICIAL,
#   ARQUIVO_SNAPSHOT_ANTIGO, PRIMEIRO_MES_CAMPANHA).
# Requisitos: lakehouse lh_bronze_campanha_1m anexado como padrao.
# Saidas: Files/painel_milhao/sorteio/<MES_REF>/ (CONTEM CPF - manter no
# lakehouse, compartilhar somente por canal seguro).
# Docs: sql/docs/diagnostico_cessoes_base_oficial_julho.md
#       vault > Painel do Milhao - Sorteio 5 Casas e 1 Milhao

# ============================================================
# CELL 1 - Parametros do mes + funcoes de apoio
# ============================================================
import os
import unicodedata

import pandas as pd

RAIZ_LAKE = '/lakehouse/default/'

# ---- TROCAR A CADA FECHAMENTO ------------------------------------
MES_REF = '07_2026'
PRIMEIRO_MES_CAMPANHA = True   # julho: Milhao acumulado == Casas do mes

# Tabela Delta gerada pelo dataflow mensal (query de julho/mes fechado).
TABELA_BASE_OFICIAL = 'base_oficial_07_2026'

# LEGADO (so julho/2026): foto parquet de 31/07 p/ auditoria da
# transicao. Padrao VAZIO = pula. Para a auditoria unica de julho, usar:
# 'Files/painel_milhao/snapshot/snapshoots_mensais/07_2026/backup_julho_cupons_ajustados.parquet'
ARQUIVO_SNAPSHOT_ANTIGO = ''
# ------------------------------------------------------------------

# Tabela viva do painel (fixo - sobrescrita a cada janela 8h/15h).
# Diretorio parquet: nome do arquivo Spark varia a cada geracao.
DIR_TABELA_VIVA = 'Files/painel_milhao/snapshot/painel_milhao_snapshot'

PASTA_SAIDA = f'Files/painel_milhao/sorteio/{MES_REF}/'


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
print(f'Mes de referencia: {MES_REF}')
print(f'Base oficial:      tabela {TABELA_BASE_OFICIAL}')
print(f'Foto antiga:       {ARQUIVO_SNAPSHOT_ANTIGO or "(sem comparacao)"}')
print(f'Tabela viva:       {DIR_TABELA_VIVA}')

# ============================================================
# CELL 2 - Carga dos tres lados
# ============================================================
oficial_raw = spark.read.table(TABELA_BASE_OFICIAL).toPandas()
print(f'Base oficial: {len(oficial_raw)} linhas, {len(oficial_raw.columns)} colunas')

viva_raw = spark.read.parquet(DIR_TABELA_VIVA).toPandas()
print(f'Tabela viva:  {len(viva_raw)} linhas')
if 'snapshot_gerado_em' in viva_raw.columns:
    print(f"Viva gerada em: {pd.to_datetime(viva_raw['snapshot_gerado_em'].iloc[0])}")

foto_raw = None
if ARQUIVO_SNAPSHOT_ANTIGO:
    foto_raw = pd.read_parquet(RAIZ_LAKE + ARQUIVO_SNAPSHOT_ANTIGO)
    print(f'Foto antiga:  {len(foto_raw)} linhas')

# ============================================================
# CELL 3 - Normalizacao (chave: empresa, obra, venda)
# ============================================================
def normaliza_lado(df, sufixo, minimo=False):
    """minimo=True (foto antiga): so chave + status + cupons + recebido."""
    d = pd.DataFrame({
        'empresa': pd.to_numeric(df[acha_coluna(df, 'codempresa')], errors='coerce').astype('Int64'),
        'obra': df[acha_coluna(df, 'codobra')].astype(str).str.strip(),
        'venda': pd.to_numeric(df[acha_coluna(df, 'venda')], errors='coerce').astype('Int64'),
        f'status_{sufixo}': df[acha_coluna(df, 'status_sorteio')].map(normaliza_status),
        f'cupons_casas_{sufixo}': df[acha_coluna(df, 'cupons_casas')].map(para_numero),
        f'cupons_milhao_{sufixo}': df[acha_coluna(df, 'cupons_milhao')].map(para_numero),
        f'valor_recebido_{sufixo}': df[acha_coluna(df, 'valor_recebido')].map(para_numero),
    })
    if minimo:
        return d
    d[f'nome_{sufixo}'] = df[acha_coluna(df, 'nomecliente')]
    d[f'cpf_{sufixo}'] = df[acha_coluna(df, 'cpf_pes')]
    _c_dtv = acha_coluna(df, 'Dt Venda', obrigatoria=False)
    d[f'data_venda_{sufixo}'] = df[_c_dtv] if _c_dtv is not None else ''
    opcionais = {
        'aptidao_casas': 'Aptidao Casas', 'aptidao_sorteio': 'Aptidao Sorteio',
        'cessao': 'Cessao', 'contrato_quitado': 'Contrato Quitado',
        'contrato_cedido': 'Contrato Cedido', 'data_cessao': 'Data Cessao',
        'data_cedida': 'Data Cedida',
        'distrato_apos_fechamento': 'Distrato Apos Fechamento',
    }
    faltantes = []
    for rotulo, nome in opcionais.items():
        c = acha_coluna(df, nome, obrigatoria=False)
        d[f'{rotulo}_{sufixo}'] = df[c] if c is not None else ''
        if c is None:
            faltantes.append(nome)
    if faltantes:
        print(f'AVISO ({sufixo}): colunas ausentes: {faltantes}')
    return d


o = normaliza_lado(oficial_raw, 'of')
v = normaliza_lado(viva_raw, 'viva')
f = normaliza_lado(foto_raw, 'foto', minimo=True) if foto_raw is not None else None
chave = ['empresa', 'obra', 'venda']
print('Lados normalizados.')

# ============================================================
# CELL 4 - Validacoes estruturais da BASE OFICIAL
# (qualquer FALHA precisa ser resolvida ANTES de usar a lista)
# ============================================================
problemas = []

dups = o.duplicated(subset=chave).sum()
print(f"{'FALHA' if dups else 'OK   '} 4.1 Duplicatas de chave: {dups}")
if dups:
    problemas.append(f'{dups} chaves duplicadas na base oficial')

tem_aptidao = (o['aptidao_sorteio_of'] != '').any()
if not tem_aptidao:
    print('FALHA 4.2 Colunas de aptidao ausentes na base oficial - conferir '
          'o dataflow mensal (query de 11/08 tem [Aptidao Casas/Sorteio]).')
    problemas.append('base oficial sem colunas de aptidao')
else:
    dif = (o['status_of'] != o['aptidao_sorteio_of'].map(normaliza_status)).sum()
    print(f"{'FALHA' if dif else 'OK   '} 4.2 Status Sorteio != Aptidao Sorteio: {dif}")
    if dif:
        problemas.append(f'{dif} linhas com Status Sorteio != Aptidao Sorteio')

resg = o[o['contrato_quitado_of'].map(eh_sim) | o['contrato_cedido_of'].map(eh_sim)]
print(f"INFO  4.3 Resgatadas: {len(resg)} "
      f"(quitadas {int(o['contrato_quitado_of'].map(eh_sim).sum())}, "
      f"cedidas {int(o['contrato_cedido_of'].map(eh_sim).sum())})")

dpf = o['distrato_apos_fechamento_of'].astype(str).str.strip().isin(('1', '1.0'))
inapto_dpf = (o.loc[dpf, 'status_of'] != 'NAO APTO').sum() if dpf.any() else 0
print(f"{'FALHA' if inapto_dpf else 'OK   '} 4.4 Distrato pos-fechamento "
      f"({int(dpf.sum())}) todos NAO APTO: {int(dpf.sum() - inapto_dpf)}/{int(dpf.sum())}")
if inapto_dpf:
    problemas.append(f'{inapto_dpf} distratos pos-fechamento marcados APTO')

if PRIMEIRO_MES_CAMPANHA:
    tm, tc = o['cupons_milhao_of'].sum(), o['cupons_casas_of'].sum()
    ok = abs(tm - tc) < 1
    print(f"{'OK   ' if ok else 'FALHA'} 4.5 1o mes: Milhao ({tm:,.0f}) == Casas ({tc:,.0f})")
    if not ok:
        problemas.append('Milhao != Casas no primeiro mes da campanha')

neg = ((o['cupons_casas_of'] < 0) | (o['cupons_milhao_of'] < 0)).sum()
print(f"{'FALHA' if neg else 'OK   '} 4.6 Cupons negativos: {neg}")
if neg:
    problemas.append(f'{neg} linhas com cupom negativo')

print()
print(f'Validacao estrutural: {"PROBLEMAS -> " + "; ".join(problemas) if problemas else "tudo OK"}')

# ============================================================
# CELL 5 - Comparacao 1: BASE OFICIAL x FOTO ANTIGA do fechamento
# Pagamentos retroativos = recebido cresceu vs a foto (baixa rodou
# depois que a foto foi batida). Entradas classificadas por motivo.
# ============================================================
if f is not None:
    m = f.merge(o, on=chave, how='outer', indicator=True)
    ambos = m[m['_merge'] == 'both']

    TOLERANCIA = 0.01
    retro = ambos[
        ambos['valor_recebido_of'] > ambos['valor_recebido_foto'] + TOLERANCIA
    ].copy()
    retro['valor_retroativo'] = retro['valor_recebido_of'] - retro['valor_recebido_foto']
    retro['cupons_ganhos'] = retro['cupons_milhao_of'] - retro['cupons_milhao_foto']

    recuperaram_apto = ambos[
        (ambos['status_foto'] == 'NAO APTO') & (ambos['status_of'] == 'APTO')
    ]
    perderam_apto = ambos[
        (ambos['status_foto'] == 'APTO') & (ambos['status_of'] == 'NAO APTO')
    ]

    def motivo_entrada(row):
        partes = []
        if str(row.get('distrato_apos_fechamento_of', '')).strip() in ('1', '1.0'):
            partes.append('DISTRATO APOS FECHAMENTO (NAO APTO)')
        if eh_sim(row.get('contrato_cedido_of')):
            partes.append('CEDENTE RESGATADO (cessao)')
        if eh_sim(row.get('cessao_of')):
            partes.append('VENDA NOVA DE CESSAO')
        if eh_sim(row.get('contrato_quitado_of')):
            partes.append('QUITADA RESGATADA')
        return ' + '.join(partes) if partes else 'BAIXA TARDIA / OUTROS'

    entraram = m[m['_merge'] == 'right_only'].copy()
    entraram['motivo_entrada'] = entraram.apply(motivo_entrada, axis=1)
    sairam = m[m['_merge'] == 'left_only'].copy()

    print('=== BASE OFICIAL x FOTO ANTIGA ===')
    print(f'Na foto: {len(f)} | Na oficial: {len(o)} | Nos dois: {len(ambos)}')
    print()
    print(f'PAGAMENTOS RETROATIVOS (baixa apos a foto): {len(retro)}')
    if len(retro):
        print(f"  Valor retroativo total: R$ {retro['valor_retroativo'].sum():,.2f}")
        print(f"  Cupons Milhao ganhos:   {retro['cupons_ganhos'].sum():,.0f}")
    print()
    print(f'Recuperaram aptidao (NAO APTO -> APTO): {len(recuperaram_apto)}')
    print(f'Perderam aptidao (APTO -> NAO APTO):    {len(perderam_apto)}')
    print(f'Entraram na base oficial: {len(entraram)}')
    if len(entraram):
        print(entraram['motivo_entrada'].value_counts().to_string())
    print(f'Sairam (so na foto): {len(sairam)} - conferir caso a caso')
else:
    retro = recuperaram_apto = perderam_apto = entraram = sairam = pd.DataFrame()
    print('Comparacao 1 pulada (ARQUIVO_SNAPSHOT_ANTIGO vazio).')

# ============================================================
# CELL 6 - Comparacao 2: BASE OFICIAL x TABELA VIVA (reconciliacao)
# Esperado: oficial tem contratos que ja sairam da viva (cessao/
# distrato aprovados depois do fechamento) e a viva tem vendas novas
# do mes seguinte. Numeros grandes aqui = investigar.
# ============================================================
ko = set(map(tuple, o[chave].itertuples(index=False, name=None)))
kv = set(map(tuple, v[chave].itertuples(index=False, name=None)))
so_oficial = ko - kv
so_viva = kv - ko
print('=== BASE OFICIAL x VIVA ===')
print(f'Nas duas: {len(ko & kv)}')
print(f'So na oficial (sairam da viva apos o fechamento): {len(so_oficial)}')
print(f'So na viva (novas apos o fechamento):             {len(so_viva)}')
if so_oficial:
    _so = o[o[chave].apply(tuple, axis=1).isin(so_oficial)]
    _flags = {
        'distrato pos-fechamento': int(_so['distrato_apos_fechamento_of']
                                       .astype(str).str.strip().isin(('1', '1.0')).sum()),
        'cedidas': int(_so['contrato_cedido_of'].map(eh_sim).sum()),
        'quitadas': int(_so['contrato_quitado_of'].map(eh_sim).sum()),
    }
    print(f'  Composicao (so oficial): {_flags}')

# ============================================================
# CELL 7 - LISTA DO SORTEIO (a partir da BASE OFICIAL do mes)
# ============================================================
apto_casas = o['aptidao_casas_of'].map(normaliza_status) == 'APTO'
apto_milhao = o['aptidao_sorteio_of'].map(normaliza_status) == 'APTO'

lista_casas = o[apto_casas & (o['cupons_casas_of'] > 0)] \
    .sort_values('cupons_casas_of', ascending=False)
lista_milhao = o[apto_milhao & (o['cupons_milhao_of'] > 0)] \
    .sort_values('cupons_milhao_of', ascending=False)

print('=== LISTAS DO SORTEIO (base oficial) ===')
print(f"Casas  ({MES_REF}): {len(lista_casas):>6} elegiveis | "
      f"{lista_casas['cupons_casas_of'].sum():,.0f} cupons")
print(f"Milhao (acum.):   {len(lista_milhao):>6} elegiveis | "
      f"{lista_milhao['cupons_milhao_of'].sum():,.0f} cupons")

# ============================================================
# CELL 8 - Saida unica + diagnostico de 1 linha
# Recorte da BASE COMPLETA do mes (mesmas ~98k linhas da query), com
# identificacao, as 2 aptidoes, valor recebido, data da venda e a
# classificacao do cliente:
#   CESSAO       = movimento de cessao DENTRO do mes analisado:
#                  cedeu no mes ([Data Cedida]) ou venda nova nascida por
#                  transferencia no mes ([Data Cessao]). Cessao de outro
#                  mes pagando normal NAO conta.
#   QUITADO      = contrato quitado resgatado (status 3; so entra na base
#                  com recebimento no mes, entao o movimento e do mes)
#   INADIMPLENTE = Aptidao Sorteio NAO APTO (parcela vencida)
#   ADIMPLENTE   = demais
# Relatorios de comparacao ficam em memoria (retro, entraram, sairam).
# Arquivo contem CPF - manter no lakehouse.
# ============================================================
os.makedirs(RAIZ_LAKE + PASTA_SAIDA, exist_ok=True)

# Janela do mes analisado, derivada de MES_REF ('07_2026' -> jul/2026)
_mes, _ano = MES_REF.split('_')
INI_MES = pd.Timestamp(int(_ano), int(_mes), 1)
PROX_MES = INI_MES + pd.offsets.MonthBegin(1)

_dt_cessao = pd.to_datetime(o['data_cessao_of'], dayfirst=True, errors='coerce')
_dt_cedida = pd.to_datetime(o['data_cedida_of'], dayfirst=True, errors='coerce')
_cessao_no_mes = (
    ((_dt_cedida >= INI_MES) & (_dt_cedida < PROX_MES))
    | ((_dt_cessao >= INI_MES) & (_dt_cessao < PROX_MES))
)
_quitado = o['contrato_quitado_of'].map(eh_sim)
_inadimplente = o['aptidao_sorteio_of'].map(normaliza_status) != 'APTO'

recorte = o.copy()
recorte['classificacao'] = 'ADIMPLENTE'
recorte.loc[_inadimplente, 'classificacao'] = 'INADIMPLENTE'
recorte.loc[_quitado, 'classificacao'] = 'QUITADO'
recorte.loc[_cessao_no_mes, 'classificacao'] = 'CESSAO'

recorte = recorte[['empresa', 'obra', 'venda', 'nome_of', 'cpf_of',
                   'aptidao_casas_of', 'aptidao_sorteio_of',
                   'valor_recebido_of', 'data_venda_of', 'classificacao']]
recorte.columns = ['CodEmpresa', 'CodObra', 'Venda', 'NomeCliente', 'CPF',
                   'Aptidao Casas', 'Aptidao Sorteio', 'Valor Recebido',
                   'Data Venda', 'Classificacao']

arquivo = f'{PASTA_SAIDA}lista_sorteio_{MES_REF}.csv'
recorte.to_csv(RAIZ_LAKE + arquivo, index=False, sep=';', encoding='utf-8-sig')

_status = 'FALHA: ' + '; '.join(problemas) if problemas else 'OK'
print(f'DIAGNOSTICO {MES_REF}: {_status} | base {len(o):,} | '
      f"casas {len(lista_casas):,} eleg/{lista_casas['cupons_casas_of'].sum():,.0f} cupons | "
      f"milhao {len(lista_milhao):,}/{lista_milhao['cupons_milhao_of'].sum():,.0f} | "
      f'retroativos {len(retro):,} | oficial-viva {len(so_oficial)}/{len(so_viva)} | '
      f"classif {recorte['Classificacao'].value_counts().to_dict()} | "
      f'gravado {arquivo} ({len(recorte):,} linhas)')
