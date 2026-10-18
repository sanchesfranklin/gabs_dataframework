"""Leitura e gravação de tabelas Delta registradas no catálogo.

Convenção do framework:

    camada  -> schema (banco) no catálogo      bronze, silver, gold
    tabela  -> <produto>_<tabela>               vendas_pedidos
    arquivos-> s3a://<camada>/<produto>/<tabela>

Assim a mesma tabela é encontrada pelo nome em qualquer ferramenta:

    Spark:  spark.read.table("silver.vendas_pedidos")
    Trino:  SELECT * FROM delta.silver.vendas_pedidos

A camada landing não entra aqui: ela guarda arquivos brutos, não tabelas.
"""

from delta.tables import DeltaTable
from pyspark.sql import DataFrame, SparkSession

from gabs import storage

TABLE_LAYERS = ("bronze", "silver", "gold")


def table_name(layer: str, product: str, table: str) -> str:
    """Nome completo da tabela no catálogo.

    >>> table_name("silver", "vendas", "pedidos")
    'silver.vendas_pedidos'
    """
    if layer not in TABLE_LAYERS:
        raise ValueError(
            f"Camada {layer!r} não guarda tabelas. Use uma de {TABLE_LAYERS}; "
            "a landing guarda arquivos brutos (use gabs.storage.path)."
        )
    storage.path(layer, product, table)  # reaproveita a validação dos nomes
    return f"{layer}.{product}_{table}"


def ensure_schema(spark: SparkSession, layer: str) -> None:
    """Cria o schema da camada no catálogo, apontando para o bucket dela."""
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {layer} LOCATION 's3a://{layer}/'")


def write_table(
    df: DataFrame,
    layer: str,
    product: str,
    table: str,
    mode: str = "overwrite",
    replace_where: str | None = None,
    partition_by: list[str] | None = None,
) -> None:
    """Grava o DataFrame como tabela Delta e garante o registro no catálogo.

    replace_where: condição que delimita a fatia a substituir, por exemplo
        "DT_REFERENCIA = '2026-09-10'". Só essa fatia é trocada; o resto da
        tabela fica intacto. É o que torna uma carga incremental idempotente:
        repetir o mesmo dia substitui o mesmo dia, sem duplicar.
    partition_by: colunas de partição. Usar a mesma coluna do replace_where
        faz o Delta trocar só os arquivos daquela partição.
    """
    path = storage.path(layer, product, table)
    spark = df.sparkSession

    writer = df.write.format("delta").mode(mode)
    if partition_by:
        writer = writer.partitionBy(*partition_by)

    if replace_where and DeltaTable.isDeltaTable(spark, path):
        # A tabela já existe: troca só a fatia indicada.
        writer = writer.option("replaceWhere", replace_where)
    elif mode == "overwrite":
        # Primeira gravação, ou substituição completa: aceita mudança de colunas.
        writer = writer.option("overwriteSchema", "true")

    writer.save(path)
    register_table(spark, layer, product, table)


def register_table(spark: SparkSession, layer: str, product: str, table: str) -> None:
    """Registra no catálogo a tabela Delta que está no caminho da convenção.

    Se já estiver registrada, não faz nada. A tabela é EXTERNA: apagar o
    registro não apaga os arquivos.
    """
    ensure_schema(spark, layer)
    spark.sql(
        f"CREATE TABLE IF NOT EXISTS {table_name(layer, product, table)} "
        f"USING DELTA LOCATION '{storage.path(layer, product, table)}'"
    )


def read_table(spark: SparkSession, layer: str, product: str, table: str) -> DataFrame:
    """Lê uma tabela pelo nome no catálogo."""
    return spark.read.table(table_name(layer, product, table))


def drop_table(spark: SparkSession, layer: str, product: str, table: str) -> None:
    """Remove a tabela do catálogo E apaga os arquivos dela no storage.

    Uso pontual, para recomeçar uma tabela do zero (por exemplo, ao mudar a
    estrutura). Não existe desfazer.
    """
    spark.sql(f"DROP TABLE IF EXISTS {table_name(layer, product, table)}")
    delete_path(spark, storage.path(layer, product, table))


def delete_path(spark: SparkSession, path: str) -> None:
    """Apaga uma pasta inteira no storage, pelo sistema de arquivos do Hadoop."""
    jvm_path = spark._jvm.org.apache.hadoop.fs.Path(path)
    fs = jvm_path.getFileSystem(spark._jsc.hadoopConfiguration())
    if fs.exists(jvm_path):
        fs.delete(jvm_path, True)
