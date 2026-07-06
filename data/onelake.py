"""Carregamento de dados via OneLake (Parquet snapshot).

Substitui conexão SQL direta (pyodbc/SQL endpoint). Autentica com service
principal, lista pasta snapshot, localiza o .parquet automaticamente e retorna
DataFrame. Nome do arquivo Spark varia a cada geração — nunca assumir nome fixo.
"""

from __future__ import annotations

import io
import os

import pandas as pd
import streamlit as st

_ACCOUNT_URL = "https://onelake.dfs.fabric.microsoft.com"
_WORKSPACE = "FB_Comercial"
_SNAPSHOT_DIR = (
    "lh_bronze_campanha_1m.Lakehouse/"
    "Files/painel_milhao/snapshot/painel_milhao_snapshot"
)


def _secret(key: str) -> str:
    """Lê secret: st.secrets primeiro, fallback para os.getenv (testes locais)."""
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError, AttributeError):
        val = os.getenv(key, "")
        if not val:
            raise RuntimeError(
                f"Secret '{key}' não encontrado em st.secrets nem em .env"
            )
        return val


def load_painel_milhao_data() -> pd.DataFrame:
    """Autentica no OneLake, localiza snapshot .parquet e retorna DataFrame.

    Sem cache próprio — o cache (keyado pela janela 8h/15h) fica em
    data.repository, único ponto de entrada do painel.
    """
    from azure.identity import ClientSecretCredential
    from azure.storage.filedatalake import DataLakeServiceClient

    # 1. Autenticação
    try:
        credential = ClientSecretCredential(
            tenant_id=_secret("AZURE_TENANT_ID"),
            client_id=_secret("AZURE_CLIENT_ID"),
            client_secret=_secret("AZURE_CLIENT_SECRET"),
        )
    except RuntimeError as exc:
        st.error(f"Falha de autenticação: {exc}")
        st.stop()

    # 2. Conexão ao OneLake
    try:
        service = DataLakeServiceClient(
            account_url=_ACCOUNT_URL, credential=credential
        )
        fs = service.get_file_system_client(_WORKSPACE)
    except Exception as exc:
        st.error(f"Falha ao conectar ao OneLake ({_ACCOUNT_URL}): {exc}")
        st.stop()

    # 3. Listar pasta snapshot
    try:
        paths = list(fs.get_paths(path=_SNAPSHOT_DIR))
    except Exception as exc:
        st.error(f"Pasta não encontrada: '{_SNAPSHOT_DIR}' — {exc}")
        st.stop()

    # 4. Localizar .parquet (ignora _SUCCESS e outros metadados Spark)
    parquet_paths = [p.name for p in paths if p.name.endswith(".parquet")]
    if not parquet_paths:
        st.error(
            f"Nenhum arquivo .parquet encontrado em: {_SNAPSHOT_DIR}\n"
            f"Arquivos presentes: {[p.name for p in paths]}"
        )
        st.stop()

    # 5/6. Download + leitura de TODOS os parts (Spark pode particionar o
    # snapshot em vários part-*.parquet; ler só o primeiro perderia linhas).
    partes = []
    for parquet_path in parquet_paths:
        try:
            data = fs.get_file_client(parquet_path).download_file().readall()
            partes.append(pd.read_parquet(io.BytesIO(data)))
        except Exception as exc:
            st.error(f"Falha ao baixar/ler '{parquet_path}': {exc}")
            st.stop()
    raw = partes[0] if len(partes) == 1 else pd.concat(partes, ignore_index=True)

    from data.adapter import adaptar
    return adaptar(raw)
