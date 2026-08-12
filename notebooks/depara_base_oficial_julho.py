# Notebook Fabric - De-para: snapshot de julho x nova base oficial (11/08/2026)
# Compara a foto batida em 31/07 (parquet do lakehouse) com a NOVA base
# oficial de julho (sql/query_sorteio_milhao_julho.sql, exportada do SSMS
# e subida ao lakehouse como xlsx/csv) e responde:
#   - quantos casos SAIRAM da base (estao na foto e nao voltam na nova)
#   - quantos casos ENTRARAM (resgatados: cessoes, quitadas, baixas
#     tardias, distratos pos-fechamento), classificados por motivo
#   - quem mudou de aptidao e quem ganhou/perdeu cupons
# Requisitos:
#   - lakehouse lh_bronze_campanha_1m anexado como padrao
#   - export da query de julho subido em ARQUIVO_BASE_NOVA (ajustar abaixo)
# Saidas: CSVs em Files/painel_milhao/depara/07_2026/ (CONTEM CPF - manter
# no lakehouse, nao baixar para local sem canal seguro).

# ============================================================
# CELL 1 - Configuracao e funcoes de apoio
# ============================================================
import os
import unicodedata

import pandas as pd

RAIZ_LAKE = '/lakehouse/default/'

# Foto oficial de 31/07. Usar a versao _cupons_ajustados (regra nova de
# cupom aplicada em 10/08). Se nao existir, apontar para backup_julho.parquet
# (cupons da regra antiga - comparacao de cupons fica enviesada).
ARQUIVO_SNAPSHOT = (
    'Files/painel_milhao/snapshot/'
    'snapshoots_mensais/07_2026/backup_julho_cupons_ajustados.parquet'
)

# Export do SSMS da nova base oficial (sql/query_sorteio_milhao_julho.sql).
# Subir o arquivo para o lakehouse e ajustar o nome aqui (.xlsx ou .csv).
ARQUIVO_BASE_NOVA = (
    'Files/painel_milhao/base_oficial/07_2026/base_oficial_julho.xlsx'
)

PASTA_SAIDA = 'Files/painel_milhao/depara/07_2026/'


def sem_acento(texto):
    nfd = unicodedata.normalize('NFD', str(texto))
    return ''.join(c for c in nfd if not unicodedata.combining(c))


def para_numero(valor):
    """Converte 'R$ 1.234,56', '1.234,56' ou numero puro em float."""
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


def normaliza_sim_nao(valor):
    return sem_acento(valor).upper().strip() == 'SIM' if pd.notna(valor) else False


def acha_coluna(df, nome_alvo, obrigatoria=True):
    alvo = sem_acento(nome_alvo).lower().replace(' ', '').replace('.', '')
    for c in df.columns:
        if sem_acento(c).lower().replace(' ', '').replace('.', '') == alvo:
            return c
    if obrigatoria:
        raise SystemExit(
            f'Coluna [{nome_alvo}] nao encontrada no export. '
            f'Colunas disponiveis: {list(df.columns)}'
        )
    return None


print('Config ok.')
print(f'Snapshot:   {ARQUIVO_SNAPSHOT}')
print(f'Base nova:  {ARQUIVO_BASE_NOVA}')

# ============================================================
# CELL 2 - Carga dos dois lados
# ============================================================
snap = pd.read_parquet(RAIZ_LAKE + ARQUIVO_SNAPSHOT)
print(f'Snapshot: {len(snap)} linhas')
if 'snapshot_gerado_em' in snap.columns:
    print(f"Foto gerada em: {pd.to_datetime(snap['snapshot_gerado_em'].iloc[0])}")

caminho_nova = RAIZ_LAKE + ARQUIVO_BASE_NOVA
if caminho_nova.lower().endswith(('.xlsx', '.xlsm')):
    nova = pd.read_excel(caminho_nova, dtype=str)
else:
    nova = None
    for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            tmp = pd.read_csv(caminho_nova, sep=None, engine='python',
                              encoding=enc, dtype=str)
            if tmp.shape[1] > 1:
                nova = tmp
                break
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    if nova is None:
        raise SystemExit('Nao consegui ler o CSV da base nova.')
print(f'Base nova: {len(nova)} linhas')

# ============================================================
# CELL 3 - Normalizacao e chave (empresa, obra, venda)
# ============================================================
s = pd.DataFrame({
    'empresa': pd.to_numeric(snap['codempresa'], errors='coerce').astype('Int64'),
    'obra': snap['codobra'].astype(str).str.strip(),
    'venda': pd.to_numeric(snap['venda'], errors='coerce').astype('Int64'),
    'nome_snap': snap['nomecliente'],
    'cpf_snap': snap['cpf_pes'],
    'status_snap': snap['status_sorteio'].map(normaliza_status),
    'cupons_snap': snap['cupons_casas'].map(para_numero),
})

col = {campo: acha_coluna(nova, campo) for campo in (
    'CodEmpresa', 'CodObra', 'Venda', 'NomeCliente', 'cpf_pes',
    'Status Sorteio', 'Cupons Casas', 'Cupons Milhao', 'Motivo',
)}
col_opcional = {campo: acha_coluna(nova, campo, obrigatoria=False) for campo in (
    'Cessao', 'Venda Origem Cessao', 'Contrato Quitado',
    'Contrato Cedido', 'Venda Nova Cessao', 'Distrato Apos Fechamento',
)}

n = pd.DataFrame({
    'empresa': pd.to_numeric(nova[col['CodEmpresa']], errors='coerce').astype('Int64'),
    'obra': nova[col['CodObra']].astype(str).str.strip(),
    'venda': pd.to_numeric(nova[col['Venda']], errors='coerce').astype('Int64'),
    'nome_nova': nova[col['NomeCliente']],
    'cpf_nova': nova[col['cpf_pes']],
    'status_nova': nova[col['Status Sorteio']].map(normaliza_status),
    'cupons_nova': nova[col['Cupons Casas']].map(para_numero),
    'motivo_status': nova[col['Motivo']].map(normaliza_status),
})
for campo, c in col_opcional.items():
    rotulo = campo.lower().replace(' ', '_')
    if c is None:
        n[rotulo] = ''
        print(f'AVISO: coluna [{campo}] ausente no export - flag vazia.')
    else:
        n[rotulo] = nova[c]

chave = ['empresa', 'obra', 'venda']
for lado, df in (('snapshot', s), ('base nova', n)):
    dups = df.duplicated(subset=chave).sum()
    if dups:
        print(f'ATENCAO: {dups} chaves duplicadas no lado {lado} - '
              f'investigar antes de confiar nos numeros.')

m = s.merge(n, on=chave, how='outer', indicator=True)
print(f'Chaves combinadas: {len(m)}')

# ============================================================
# CELL 4 - Classificacao
# ============================================================
def motivo_entrada(row):
    """Explica por que o contrato aparece na base nova e nao na foto."""
    partes = []
    if str(row.get('distrato_apos_fechamento', '')).strip() in ('1', '1.0'):
        partes.append('DISTRATO APOS FECHAMENTO (ativa em 31/07)')
    if normaliza_sim_nao(row.get('contrato_cedido')):
        partes.append('CEDENTE RESGATADO (cessao)')
    if normaliza_sim_nao(row.get('cessao')):
        partes.append('VENDA NOVA DE CESSAO')
    if normaliza_sim_nao(row.get('contrato_quitado')):
        partes.append('QUITADA RESGATADA')
    return ' + '.join(partes) if partes else 'BAIXA TARDIA / OUTROS'


sumiram = m[m['_merge'] == 'left_only'].copy()          # SAIRAM da base
entraram = m[m['_merge'] == 'right_only'].copy()        # so na base nova
ambos = m[m['_merge'] == 'both']

entraram['motivo_entrada'] = entraram.apply(motivo_entrada, axis=1)

resgatados_apto = ambos[
    (ambos['status_snap'] == 'NAO APTO') & (ambos['status_nova'] == 'APTO')
]
perderam_apto = ambos[
    (ambos['status_snap'] == 'APTO') & (ambos['status_nova'] == 'NAO APTO')
]
ganharam_cupons = ambos[ambos['cupons_nova'] > ambos['cupons_snap']]
perderam_cupons = ambos[ambos['cupons_nova'] < ambos['cupons_snap']]

# ============================================================
# CELL 5 - Resumo
# ============================================================
print('=== DE-PARA: FOTO 31/07 x NOVA BASE OFICIAL DE JULHO ===')
print(f'Contratos na foto:        {len(s):>8}')
print(f'Contratos na base nova:   {len(n):>8}')
print(f'Presentes nos dois lados: {len(ambos):>8}')
print()
print(f'SAIRAM da base (so na foto):      {len(sumiram):>6}')
print(f'ENTRARAM na base (so na nova):    {len(entraram):>6}')
print()
print('Motivos de entrada (regras novas de 11/08):')
if len(entraram):
    print(entraram['motivo_entrada'].value_counts().to_string())
else:
    print('  (nenhum)')
print()
print(f'Recuperaram aptidao (NAO APTO -> APTO): {len(resgatados_apto):>6}')
print(f'Perderam aptidao (APTO -> NAO APTO):    {len(perderam_apto):>6}')
print(f'Ganharam cupons (nova > foto):          {len(ganharam_cupons):>6}')
print(f'Perderam cupons (nova < foto):          {len(perderam_cupons):>6}')
print()
print(f"Cupons Casas foto:      {s['cupons_snap'].sum():>12,.0f}")
print(f"Cupons Casas base nova: {n['cupons_nova'].sum():>12,.0f}")
print(f"Aptos foto:             {(s['status_snap'] == 'APTO').sum():>8}")
print(f"Aptos base nova:        {(n['status_nova'] == 'APTO').sum():>8}")
print()
print('Quem SAIU nao tem flags na base nova - motivos provaveis: distrato/')
print('cancelamento aprovado ate 31/07, cessao sem pagamento real pre-cessao,')
print('quitada sem recebimento em julho. Conferir lista "sairam" caso a caso.')

# ============================================================
# CELL 6 - Gravacao das saidas (CSV no lakehouse) e amostras
# ============================================================
os.makedirs(RAIZ_LAKE + PASTA_SAIDA, exist_ok=True)

saidas = {
    'sairam': sumiram,
    'entraram': entraram,
    'recuperaram_aptidao': resgatados_apto,
    'perderam_aptidao': perderam_apto,
    'ganharam_cupons': ganharam_cupons,
    'perderam_cupons': perderam_cupons,
}
for nome, df in saidas.items():
    caminho = f'{PASTA_SAIDA}depara_julho_{nome}.csv'
    df.drop(columns=['_merge']).to_csv(
        RAIZ_LAKE + caminho, index=False, sep=';', encoding='utf-8-sig'
    )
    print(f'Gravado: {caminho} ({len(df)} linhas)')

print()
print('Arquivos contem CPF - manter no lakehouse (acesso restrito).')

# Amostras para inspecao rapida no proprio notebook
display(entraram[['empresa', 'obra', 'venda', 'nome_nova', 'status_nova',
                  'cupons_nova', 'motivo_entrada']].head(50))
display(sumiram[['empresa', 'obra', 'venda', 'nome_snap', 'status_snap',
                 'cupons_snap']].head(50))
