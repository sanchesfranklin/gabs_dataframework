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
    """Grava o DataFrame como tabela Delta e a registra no catálogo.

    replace_where: condição que delimita a fatia a substituir, por exemplo
        "DT_REFERENCIA = '2026-09-10'". Só essa fatia é trocada; o resto da
        tabela fica intacto. É o que torna uma carga incremental idempotente:
        repetir o mesmo dia substitui o mesmo dia, sem duplicar.
    partition_by: colunas de partição. Usar a mesma coluna do replace_where
        faz o Delta trocar só os arquivos daquela partição.
    """
    name = table_name(layer, product, table)
    path = storage.path(layer, product, table)
    spark = df.sparkSession
    ensure_schema(spark, layer)

    writer = df.write.format("delta").mode(mode)
    if partition_by:
        writer = writer.partitionBy(*partition_by)

    if replace_where and spark.catalog.tableExists(name):
        # Tabela já existe: grava pelo caminho, trocando só a fatia indicada.
        # O registro no catálogo continua o mesmo (ele só guarda o endereço).
        writer.option("replaceWhere", replace_where).save(path)
        return

    if mode == "overwrite" and not replace_where:
        # Permite que uma nova versão mude colunas (útil enquanto se desenvolve).
        writer = writer.option("overwriteSchema", "true")

    # Primeira gravação (ou substituição completa): cria a tabela EXTERNA no
    # caminho da convenção e a registra no catálogo.
    writer.option("path", path).saveAsTable(name)


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
