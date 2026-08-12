# -*- coding: utf-8 -*-
"""Classificador v2 — base completa julho/2026 (aba 'Query Julho').

Classes (prioridade): DISTRATADO > CESSAO > QUITADO > INADIMPLENTE > ADIMPLENTE.
DISTRATADO forca Aptidao Casas/Sorteio = NAO APTO na saida.
Coluna Diagnostico resume evento + data. Resumo por classe impresso no
final (saida em arquivo unico). CPF nunca impresso em log — somente no
arquivo.
"""
import re
import unicodedata
from datetime import datetime

import pandas as pd

XLSX = r"C:\Users\pedro.moura\Downloads\Querys Atualizadas.xlsx"
SHEET = "Query Julho"
OUT = r"C:\Users\pedro.moura\Documents\Projetos\Painel do Milhao\saidas\base_completa_julho_2026.csv"

JUL_INI = pd.Timestamp(2026, 7, 1)
JUL_FIM = pd.Timestamp(2026, 7, 31)


def norm_txt(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    s = unicodedata.normalize("NFKD", str(v))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", s).strip().upper()


def find_col(cols, canonical):
    """Casa nome de coluna tolerando encoding quebrado: compara sem acento e
    tratando qualquer char nao-ASCII do header como curinga de 1 char."""
    cn = norm_txt(canonical)
    for c in cols:
        pattern = "".join(
            "." if (ord(ch) > 127 or ch == "\ufffd") else re.escape(ch) for ch in str(c)
        )
        if re.fullmatch(pattern, canonical, flags=re.IGNORECASE) or norm_txt(c) == cn:
            return c
    raise KeyError(f"Coluna nao encontrada: {canonical}")


money_fail = 0


def parse_money(v):
    global money_fail
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).replace("R$", "").replace("\xa0", "").strip()
    if t in ("", "-"):
        return 0.0
    neg = t.startswith("-") or (t.startswith("(") and t.endswith(")"))
    t = t.strip("()").lstrip("-").strip()
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", t):
        t = t.replace(".", "")
    try:
        x = float(t)
    except ValueError:
        money_fail += 1
        return 0.0
    return -x if neg else x


def parse_date(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return pd.NaT
    if isinstance(v, (pd.Timestamp, datetime)):
        return pd.Timestamp(v)
    if isinstance(v, (int, float)):
        s = str(int(v))
        return pd.to_datetime(s, format="%Y%m%d", errors="coerce") if len(s) == 8 else pd.NaT
    s = str(v).strip()
    if s == "":
        return pd.NaT
    if re.fullmatch(r"\d{8}", s):
        return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    return pd.to_datetime(s, dayfirst=True, errors="coerce")


def clean_id(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def fmt_cpf(v):
    s = clean_id(v)
    if re.fullmatch(r"\d+", s) and len(s) <= 11:
        s = s.zfill(11)
    return s


def fmt_d(d):
    return d.strftime("%d/%m/%Y") if pd.notna(d) else ""


print("Lendo planilha...", flush=True)
df = pd.read_excel(XLSX, sheet_name=SHEET, dtype={"cpf_pes": str}).dropna(how="all")
print(f"Linhas: {len(df)}", flush=True)

cols = list(df.columns)
c_emp = find_col(cols, "CodEmpresa")
c_obra = find_col(cols, "CodObra")
c_venda = find_col(cols, "Venda")
c_nome = find_col(cols, "NomeCliente")
c_cpf = find_col(cols, "cpf_pes")
c_apt_casas = find_col(cols, "Aptidão Casas")
c_apt_sorteio = find_col(cols, "Aptidão Sorteio")
c_vlr_rec = find_col(cols, "Valor Recebido")
c_dt_venda = find_col(cols, "Dt.Venda")
c_dt_cedida = find_col(cols, "Data Cedida")
c_dt_cessao = find_col(cols, "Data Cessão")
c_quitado = find_col(cols, "Contrato Quitado")
c_distrato = find_col(cols, "Distrato Após Fechamento")
c_cup_milhao = find_col(cols, "Cupons Milhão")
c_cup_casas = find_col(cols, "Cupons Casas")
c_motivo = find_col(cols, "Motivo")
c_ult_rec = find_col(cols, "Data Último Recebimento")

dt_cedida = df[c_dt_cedida].map(parse_date)
dt_cessao = df[c_dt_cessao].map(parse_date)
dt_venda = df[c_dt_venda].map(parse_date)
dt_ult = df[c_ult_rec].map(parse_date)

cedida_jul = dt_cedida.between(JUL_INI, JUL_FIM)
cessao_jul = dt_cessao.between(JUL_INI, JUL_FIM)
quitado = df[c_quitado].map(norm_txt) == "SIM"
apto_sorteio = df[c_apt_sorteio].map(norm_txt) == "APTO"
distratado = pd.to_numeric(df[c_distrato], errors="coerce").fillna(0).astype(int) == 1

classif = pd.Series("ADIMPLENTE", index=df.index)
classif[~apto_sorteio] = "INADIMPLENTE"
classif[quitado] = "QUITADO"
classif[cedida_jul | cessao_jul] = "CESSAO"
classif[distratado] = "DISTRATADO"

apt_casas_out = df[c_apt_casas].fillna("").astype(str).str.strip()
apt_sorteio_out = df[c_apt_sorteio].fillna("").astype(str).str.strip()
apt_casas_out[distratado] = "NÃO APTO"
apt_sorteio_out[distratado] = "NÃO APTO"

motivo = df[c_motivo].fillna("").astype(str).str.strip()


def diagnostico(i):
    c = classif.at[i]
    ult = fmt_d(dt_ult.at[i])
    suf_ult = f" — último recebimento {ult}" if ult else " — sem recebimento na janela"
    if c == "DISTRATADO":
        return "Distrato após fechamento — marcado NÃO APTO"
    if c == "CESSAO":
        partes = []
        if cedida_jul.at[i]:
            partes.append(f"contrato cedido em {fmt_d(dt_cedida.at[i])}")
        if cessao_jul.at[i]:
            partes.append(f"venda nova por cessão em {fmt_d(dt_cessao.at[i])}")
        return ("Cessão no mês: " + " e ".join(partes)).capitalize()
    if c == "QUITADO":
        return f"Contrato quitado{suf_ult}"
    if c == "INADIMPLENTE":
        m = motivo.at[i]
        base = m.capitalize() if m and norm_txt(m) != "ADIMPLENTE" else "Não apto no sorteio"
        return f"{base}{suf_ult}"
    return f"Em dia{suf_ult}"


diag = pd.Series([diagnostico(i) for i in df.index], index=df.index)

out = pd.DataFrame({
    "CodEmpresa": df[c_emp].map(clean_id),
    "CodObra": df[c_obra].map(clean_id),
    "Venda": df[c_venda].map(clean_id),
    "NomeCliente": df[c_nome].fillna("").astype(str).str.strip(),
    "CPF": df[c_cpf].map(fmt_cpf),
    "Aptidao Casas": apt_casas_out,
    "Aptidao Sorteio": apt_sorteio_out,
    "Valor Recebido": df[c_vlr_rec].map(parse_money),
    "Cupons Milhao": df[c_cup_milhao].map(parse_money).round(0).astype(int),
    "Cupons Casas": df[c_cup_casas].map(parse_money).round(0).astype(int),
    "Data Venda": dt_venda.dt.strftime("%d/%m/%Y").fillna(""),
    "Classificacao": classif,
    "Diagnostico": diag,
})

print(f"Falhas parse monetario: {money_fail}")
out.to_csv(OUT, sep=";", index=False, encoding="utf-8-sig", decimal=",")

ordem = ["DISTRATADO", "CESSAO", "QUITADO", "INADIMPLENTE", "ADIMPLENTE"]
resumo = (
    out.groupby("Classificacao")
    .agg(Contratos=("Venda", "size"), Valor_Recebido=("Valor Recebido", "sum"),
         Cupons_Milhao=("Cupons Milhao", "sum"), Cupons_Casas=("Cupons Casas", "sum"))
    .reindex(ordem)
    .fillna(0)
)
for _c in ("Contratos", "Cupons_Milhao", "Cupons_Casas"):
    resumo[_c] = resumo[_c].astype(int)
resumo["Pct"] = (100 * resumo["Contratos"] / len(out)).round(2)

print("\nRESUMO:")
print(resumo.to_string())
partes = " ".join(f"{k}={int(v)}" for k, v in resumo["Contratos"].items())
print(f"\nDIAG: {len(out)} linhas gravadas | {partes} | {OUT}")
