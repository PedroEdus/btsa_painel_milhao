import os

from azure.identity import ClientSecretCredential
from azure.storage.filedatalake import DataLakeServiceClient
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

WORKSPACE = "FB_Comercial"
LAKEHOUSE = "lh_bronze_campanha_1m"

DIR_PATH = (
    f"{LAKEHOUSE}.Lakehouse/"
    f"Files/painel_milhao/snapshot/painel_milhao_snapshot"
)

credential = ClientSecretCredential(
    tenant_id=TENANT_ID,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)

service_client = DataLakeServiceClient(
    account_url="https://onelake.dfs.fabric.microsoft.com",
    credential=credential,
)

file_system_client = service_client.get_file_system_client(WORKSPACE)

paths = list(file_system_client.get_paths(path=DIR_PATH))

parquet_files = [
    p.name for p in paths
    if p.name.endswith(".parquet")
]

if not parquet_files:
    raise FileNotFoundError("Nenhum arquivo parquet encontrado no snapshot.")

remote_file_path = parquet_files[0]
local_file_path = "painel_milhao_snapshot.parquet"

print("Baixando:")
print(remote_file_path)

file_client = file_system_client.get_file_client(remote_file_path)

download = file_client.download_file()
with open(local_file_path, "wb") as f:
    f.write(download.readall())

print("Arquivo baixado:")
print(local_file_path)

df = pd.read_parquet(local_file_path)

print("Leitura OK")
print(df.shape)
print(df.head())