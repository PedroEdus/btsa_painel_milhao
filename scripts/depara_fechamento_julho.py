"""De-para do fechamento de julho/2026: snapshot x apuracao retroativa.

Compara a foto da base batida no fechamento (parquet do OneLake) com o
resultado da apuracao retroativa (sql/fechamento_julho_2026_elegiveis.sql,
exportado do SSMS como CSV) e lista quem mudou por causa das baixas
processadas depois de 31/07.

Uso:
    python scripts/depara_fechamento_julho.py --apuracao resultado.csv
        [--snapshot painel_milhao_snapshot.parquet] [--baixar] [--forcar]

    --apuracao   CSV exportado do SSMS (obrigatorio)
    --snapshot   parquet local da foto (padrao: painel_milhao_snapshot.parquet)
    --baixar     baixa o snapshot atual do OneLake antes de comparar
                 (requer .env; o snapshot no lake SOBREPOE a cada fechamento,
                 por isso uma copia datada e arquivada automaticamente)
    --forcar     prossegue mesmo se a foto nao for do fechamento (31/07-02/08)

Saidas em saidas/ (CONTEM CPF: pasta fora do git, nao compartilhar fora de
canal seguro): resgatados, perderam_aptidao, ganharam_cupons, novos, sumidos.
"""

import argparse
import os
import shutil
import sys
import unicodedata

import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JANELA_FECHAMENTO = (pd.Timestamp("2026-07-31"), pd.Timestamp("2026-08-02 23:59:59"))


def baixar_snapshot(destino):
    """Baixa o parquet do snapshot do OneLake (mesma origem do
    scripts/baixar_snapshot.py)."""
    from azure.identity import ClientSecretCredential
    from azure.storage.filedatalake import DataLakeServiceClient
    from dotenv import load_dotenv

    load_dotenv()
    credential = ClientSecretCredential(
        tenant_id=os.getenv("AZURE_TENANT_ID"),
        client_id=os.getenv("AZURE_CLIENT_ID"),
        client_secret=os.getenv("AZURE_CLIENT_SECRET"),
    )
    service_client = DataLakeServiceClient(
        account_url="https://onelake.dfs.fabric.microsoft.com",
        credential=credential,
    )
    fs = service_client.get_file_system_client("FB_Comercial")
    dir_path = (
        "lh_bronze_campanha_1m.Lakehouse/"
        "Files/painel_milhao/snapshot/painel_milhao_snapshot"
    )
    parquets = [
        p.name for p in fs.get_paths(path=dir_path) if p.name.endswith(".parquet")
    ]
    if not parquets:
        raise FileNotFoundError("Nenhum parquet encontrado no snapshot do OneLake.")
    print(f"Baixando: {parquets[0]}")
    download = fs.get_file_client(parquets[0]).download_file()
    with open(destino, "wb") as f:
        f.write(download.readall())
    print(f"Snapshot salvo em: {destino}")


def sem_acento(texto):
    nfd = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in nfd if not unicodedata.combining(c))


def para_numero(valor):
    """Converte '1.234,56', 'R$ 1.234,56' ou numero puro em float."""
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    t = str(valor).replace("R$", "").replace("\xa0", "").strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return 0.0


def normaliza_status(valor):
    if pd.isna(valor):
        return ""
    return sem_acento(valor).upper().strip()


def carrega_apuracao(caminho):
    """CSV do SSMS: separador e encoding variam conforme a exportacao."""
    ultimo_erro = None
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(caminho, sep=None, engine="python", encoding=enc, dtype=str)
            if df.shape[1] > 1:
                return df
        except (UnicodeDecodeError, pd.errors.ParserError) as e:
            ultimo_erro = e
    raise SystemExit(f"Nao consegui ler o CSV da apuracao: {ultimo_erro}")


def acha_coluna(df, nome_alvo):
    alvo = sem_acento(nome_alvo).lower().replace(" ", "").replace(".", "")
    for c in df.columns:
        if sem_acento(c).lower().replace(" ", "").replace(".", "") == alvo:
            return c
    raise SystemExit(
        f"Coluna '{nome_alvo}' nao encontrada no CSV. Colunas: {list(df.columns)}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apuracao", required=True)
    parser.add_argument(
        "--snapshot", default=os.path.join(RAIZ, "painel_milhao_snapshot.parquet")
    )
    parser.add_argument("--baixar", action="store_true")
    parser.add_argument("--forcar", action="store_true")
    args = parser.parse_args()

    if args.baixar:
        baixar_snapshot(args.snapshot)

    snap = pd.read_parquet(args.snapshot)

    # Valida que a foto e mesmo a do fechamento e arquiva copia datada
    # (o snapshot do OneLake sobrepoe a cada fechamento)
    gerado_em = pd.to_datetime(snap["snapshot_gerado_em"].iloc[0]).tz_localize(None)
    print(f"Snapshot gerado em: {gerado_em}")
    copia = os.path.join(RAIZ, f"painel_milhao_snapshot_{gerado_em:%Y%m%d}.parquet")
    if not os.path.exists(copia):
        shutil.copy2(args.snapshot, copia)
        print(f"Copia arquivada: {copia}")
    if not (JANELA_FECHAMENTO[0] <= gerado_em <= JANELA_FECHAMENTO[1]):
        msg = (
            f"ATENCAO: a foto NAO e do fechamento de julho "
            f"(esperado entre {JANELA_FECHAMENTO[0]:%d/%m} e "
            f"{JANELA_FECHAMENTO[1]:%d/%m}). O de-para ficaria sem sentido."
        )
        if args.forcar:
            print(msg + " Prosseguindo por --forcar.")
        else:
            raise SystemExit(msg + " Use --baixar para pegar a foto atual do "
                             "OneLake ou --forcar para prosseguir assim mesmo.")

    apur = carrega_apuracao(args.apuracao)

    # Normalizacao dos dois lados
    s = pd.DataFrame({
        "empresa": pd.to_numeric(snap["codempresa"], errors="coerce").astype("Int64"),
        "obra": snap["codobra"].astype(str).str.strip(),
        "venda": pd.to_numeric(snap["venda"], errors="coerce").astype("Int64"),
        "nome_snap": snap["nomecliente"],
        "cpf_snap": snap["cpf_pes"],
        "status_snap": snap["status_sorteio"].map(normaliza_status),
        "cupons_snap": snap["cupons_casas"].map(para_numero),
    })

    col = {campo: acha_coluna(apur, campo) for campo in (
        "CodEmpresa", "CodObra", "Venda", "NomeCliente", "CPF",
        "Status Fechamento Julho", "Cupons Casas Julho",
        "Valor Gera Cupom Julho", "Pgto 30-31/07",
    )}
    a = pd.DataFrame({
        "empresa": pd.to_numeric(apur[col["CodEmpresa"]], errors="coerce").astype("Int64"),
        "obra": apur[col["CodObra"]].astype(str).str.strip(),
        "venda": pd.to_numeric(apur[col["Venda"]], errors="coerce").astype("Int64"),
        "nome_apur": apur[col["NomeCliente"]],
        "cpf_apur": apur[col["CPF"]],
        "status_apur": apur[col["Status Fechamento Julho"]].map(normaliza_status),
        "cupons_apur": apur[col["Cupons Casas Julho"]].map(para_numero),
        "valor_cupom_apur": apur[col["Valor Gera Cupom Julho"]].map(para_numero),
        "pgto_3031": apur[col["Pgto 30-31/07"]].map(para_numero),
    })

    chave = ["empresa", "obra", "venda"]
    for lado, df in (("snapshot", s), ("apuracao", a)):
        dups = df.duplicated(subset=chave).sum()
        if dups:
            print(f"ATENCAO: {dups} chaves duplicadas no lado {lado}.")

    m = s.merge(a, on=chave, how="outer", indicator=True)

    resgatados = m[
        (m["status_snap"] == "NAO APTO") & (m["status_apur"] == "APTO")
    ]
    perderam = m[
        (m["status_snap"] == "APTO") & (m["status_apur"] == "NAO APTO")
    ]
    ganharam_cupons = m[
        (m["_merge"] == "both") & (m["cupons_apur"] > m["cupons_snap"])
    ]
    novos = m[m["_merge"] == "right_only"]
    sumidos = m[m["_merge"] == "left_only"]

    print()
    print("=== RESUMO DO DE-PARA ===")
    print(f"Vendas no snapshot:  {len(s):>8}")
    print(f"Vendas na apuracao:  {len(a):>8}")
    print(f"Cupons Casas snap:   {s['cupons_snap'].sum():>12,.0f}")
    print(f"Cupons Casas apur:   {a['cupons_apur'].sum():>12,.0f}")
    print(f"Aptos snap:          {(s['status_snap'] == 'APTO').sum():>8}")
    print(f"Aptos apur:          {(a['status_apur'] == 'APTO').sum():>8}")
    print()
    print(f"Resgatados (NAO APTO -> APTO):      {len(resgatados):>6}")
    print(f"Perderam aptidao (APTO -> NAO APTO):{len(perderam):>6}")
    print(f"Ganharam cupons (apur > snap):      {len(ganharam_cupons):>6}")
    print(f"  ... com pagamento em 30-31/07:    {int((ganharam_cupons['pgto_3031'] > 0).sum()):>6}")
    print(f"So na apuracao (novos):             {len(novos):>6}")
    print(f"So no snapshot (sumidos):           {len(sumidos):>6}")

    pasta = os.path.join(RAIZ, "saidas")
    os.makedirs(pasta, exist_ok=True)
    saidas = {
        "resgatados": resgatados,
        "perderam_aptidao": perderam,
        "ganharam_cupons": ganharam_cupons,
        "novos": novos,
        "sumidos": sumidos,
    }
    for nome, df in saidas.items():
        caminho = os.path.join(pasta, f"depara_julho_{nome}.csv")
        df.drop(columns=["_merge"]).to_csv(
            caminho, index=False, sep=";", encoding="utf-8-sig"
        )
        print(f"Gravado: {caminho} ({len(df)} linhas)")
    print()
    print("Arquivos contem CPF - pasta saidas/ fica fora do git; "
          "compartilhar somente por canal seguro.")


if __name__ == "__main__":
    main()
