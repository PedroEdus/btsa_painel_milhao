# Notebook Fabric (PySpark) - Ajuste dos cupons do snapshot de julho/2026
# Regra nova (decisao conjunta 10/08/2026): cupom = FLOOR(valor recebido
# INTEGRAL / 100), com clamp em zero. So os cupons mudam - colunas de
# valor ficam intactas. Gera COPIA com sufixo _cupons_ajustados (original
# preservado, por via das duvidas).
# ATENCAO: valor_recebido do parquet e a foto de 31/07, sem as baixas
# tardias (resgatados ficam com cupom da foto). Fonte com valor cheio =
# apuracao v3 (sql/fechamento_julho_2026_elegiveis.sql).
# Requisito: lakehouse lh_bronze_campanha_1m anexado como padrao.

# ============================================================
# CELL 1 - Ler, recalcular cupons e gravar a copia
# ============================================================
from pyspark.sql import functions as F

CAMINHO = (
    'Files/painel_milhao/snapshot/'
    'snapshoots_mensais/07_2026/backup_julho.parquet'
)
SAIDA_LAKE = (
    'Files/painel_milhao/snapshot/'
    'snapshoots_mensais/07_2026/backup_julho_cupons_ajustados.parquet'
)

df = spark.read.parquet(CAMINHO)

# valor_recebido vem como texto pt-BR ('R$ 1.947,22') -> 1947.22
# Mantem digitos, virgula e sinal; descarta R$, pontos de milhar e espacos
valor_txt = F.regexp_replace(F.col('valor_recebido'), '[^0-9,\\-]', '')
valor_num = F.coalesce(
    F.regexp_replace(valor_txt, ',', '.').cast('double'),
    F.lit(0.0),
)

# Clamp: estorno liquido (valor negativo) nao gera cupom
cupons_novos = F.when(valor_num > 0, F.floor(valor_num / 100)).otherwise(0)
cupons_novos = cupons_novos.cast('double')

df_ajustado = (
    df
    .withColumn('cupons_casas', cupons_novos)
    # Julho e o 1o mes da campanha: Milhao acumulado = mes
    .withColumn('cupons_milhao', cupons_novos)
)

# Escrita em ARQUIVO unico (Spark write criaria pasta com part-files);
# 97k linhas cabem tranquilo em pandas
pdf = df_ajustado.toPandas()
pdf.to_parquet('/lakehouse/default/' + SAIDA_LAKE, index=False)
print(f'Gravado: {SAIDA_LAKE} ({len(pdf)} linhas)')

# ============================================================
# CELL 2 - Conferencias (rodar antes de usar a copia)
# ============================================================
antes = spark.read.parquet(CAMINHO)
depois = spark.read.parquet(SAIDA_LAKE)

resumo = (
    antes.select(
        F.sum(F.col('cupons_casas').cast('double')).alias('casas_antes'),
        F.sum(F.col('cupons_milhao').cast('double')).alias('milhao_antes'),
    ).crossJoin(
        depois.select(
            F.sum('cupons_casas').alias('casas_depois'),
            F.sum('cupons_milhao').alias('milhao_depois'),
            F.min('cupons_casas').alias('min_cupons'),
        )
    )
)
resumo.show()
# Esperado: depois > antes (multa/juros/taxa agora contam);
# min_cupons = 0 (clamp funcionou, nada negativo)

# Quantos contratos mudaram de quantidade de cupons
a = antes.select('codempresa', 'codobra', 'venda',
                 F.col('cupons_casas').cast('double').alias('antes'))
d = depois.select('codempresa', 'codobra', 'venda',
                  F.col('cupons_casas').alias('depois'))
mudou = a.join(d, ['codempresa', 'codobra', 'venda'])
print('Contratos com cupons alterados:',
      mudou.filter(F.col('antes') != F.col('depois')).count())
mudou.withColumn('delta', F.col('depois') - F.col('antes')) \
     .orderBy(F.desc('delta')).show(10)
