"""Atualiza os cupons do snapshot para a regra nova (valor recebido integral).

Decisao conjunta em reuniao (10/08/2026): cupom = FLOOR(valor recebido
INTEGRAL / 100), incluindo multa, juros/correcao de atraso e taxa de boleto.

FONTE dos valores = apuracao retroativa v3 (export do SSMS com a coluna
[Valor Recebido Julho]), NUNCA a coluna valor_recebido do proprio parquet:
a foto de 31/07 nao tem as baixas tardias (os 986 resgatados ficariam com
cupom errado de novo).

Colunas substituidas no parquet: SOMENTE cupons_casas e cupons_milhao
(julho e o 1o mes da campanha: acumulado = mes). As colunas de valor
(valor_gera_cupom, valor_recebido etc.) ficam intactas - decisao 10/08:
so os cupons mudam de regua. Contratos sem retorno na apuracao mantem
os valores originais.

Uso:
    python scripts/atualiza_cupons_snapshot.py --apuracao apuracao_v3.xlsx
        [--snapshot painel_milhao_snapshot_20260731.parquet]
        [--saida painel_milhao_snapshot_20260731_regra_nova.parquet]
        [--subir]   # envia ao OneLake sobrescrevendo o snapshot remoto
                    # (PRODUCAO - so rodar com aval do time)
"""

import argparse
import math
import os

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def carrega_apuracao(caminho):
    if caminho.lower().endswith(('.xlsx', '.xlsm')):
        df = pd.read_excel(caminho)
    else:
        df = pd.read_csv(caminho, sep=None, engine='python', encoding='utf-8-sig')
    if 'Valor Recebido Julho' not in df.columns:
        raise SystemExit(
            'Export sem a coluna [Valor Recebido Julho] - rodar a apuracao '
            'v3 (sql/fechamento_julho_2026_elegiveis.sql) e exportar de novo.')
    val = pd.to_numeric(df['Valor Recebido Julho'], errors='coerce').fillna(0)
    cup = pd.to_numeric(df['Cupons Casas Julho'], errors='coerce').fillna(0)
    razao = val.sum() / max(cup.sum() * 100, 1)
    if razao > 1000:
        val = val / 1_000_000
        print(f'Valor Recebido corrigido /1e6 (razao detectada: {razao:,.0f})')
    df['_valor_recebido_julho'] = val
    return df


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apuracao', required=True)
    parser.add_argument(
        '--snapshot',
        default=os.path.join(RAIZ, 'painel_milhao_snapshot_20260731.parquet'))
    parser.add_argument('--saida', default=None)
    parser.add_argument('--subir', action='store_true')
    args = parser.parse_args()

    snap = pd.read_parquet(args.snapshot)
    apur = carrega_apuracao(args.apuracao)

    apur = apur.assign(
        _emp=pd.to_numeric(apur['CodEmpresa']).astype('Int64'),
        _obra=apur['CodObra'].astype(str).str.strip(),
        _venda=pd.to_numeric(apur['Venda']).astype('Int64'),
    ).set_index(['_emp', '_obra', '_venda'])

    chave_snap = pd.MultiIndex.from_arrays([
        pd.to_numeric(snap['codempresa']).astype('Int64'),
        snap['codobra'].astype(str).str.strip(),
        pd.to_numeric(snap['venda']).astype('Int64'),
    ])
    valores = apur['_valor_recebido_julho'].reindex(chave_snap)

    sem_match = valores.isna()
    cupons_novos = valores.map(
        lambda v: 0 if pd.isna(v) or v <= 0 else math.floor(v / 100))

    antes_casas = pd.to_numeric(snap['cupons_casas'], errors='coerce').fillna(0)
    snap = snap.copy()
    snap.loc[~sem_match.values, 'cupons_casas'] = cupons_novos[~sem_match].values
    snap.loc[~sem_match.values, 'cupons_milhao'] = cupons_novos[~sem_match].values

    saida = args.saida or args.snapshot.replace('.parquet', '_regra_nova.parquet')
    snap.to_parquet(saida, index=False)

    depois_casas = pd.to_numeric(snap['cupons_casas'], errors='coerce').fillna(0)
    print()
    print('=== CUPONS: REGRA NOVA (valor recebido integral) ===')
    print(f'Contratos no snapshot:      {len(snap):>8}')
    print(f'Atualizados pela apuracao:  {int((~sem_match).sum()):>8}')
    print(f'Sem retorno (mantidos):     {int(sem_match.sum()):>8}')
    print(f'Cupons Casas antes:         {int(antes_casas.sum()):>8}')
    print(f'Cupons Casas depois:        {int(depois_casas.sum()):>8}')
    print(f'Arquivo gerado: {saida}')

    if args.subir:
        from azure.identity import ClientSecretCredential
        from azure.storage.filedatalake import DataLakeServiceClient
        from dotenv import load_dotenv

        load_dotenv()
        credential = ClientSecretCredential(
            tenant_id=os.getenv('AZURE_TENANT_ID'),
            client_id=os.getenv('AZURE_CLIENT_ID'),
            client_secret=os.getenv('AZURE_CLIENT_SECRET'),
        )
        service_client = DataLakeServiceClient(
            account_url='https://onelake.dfs.fabric.microsoft.com',
            credential=credential,
        )
        fs = service_client.get_file_system_client('FB_Comercial')
        dir_path = ('lh_bronze_campanha_1m.Lakehouse/'
                    'Files/painel_milhao/snapshot/painel_milhao_snapshot')
        parquets = [p.name for p in fs.get_paths(path=dir_path)
                    if p.name.endswith('.parquet')]
        if not parquets:
            raise SystemExit('Snapshot remoto nao encontrado no OneLake.')
        destino = parquets[0]
        print(f'Sobrescrevendo no OneLake: {destino}')
        with open(saida, 'rb') as f:
            fs.get_file_client(destino).upload_data(f, overwrite=True)
        print('Upload concluido.')


if __name__ == '__main__':
    main()
