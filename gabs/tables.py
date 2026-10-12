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
) -> None:
    """Grava o DataFrame como tabela Delta e a registra no catálogo.

    mode="overwrite" substitui o conteúdo (cria uma nova versão no Delta, a
    anterior continua acessível por time travel). Rodar duas vezes com os
    mesmos dados dá o mesmo resultado: o job é idempotente.
    """
    name = table_name(layer, product, table)
    ensure_schema(df.sparkSession, layer)

    writer = (
        df.write.format("delta")
        .mode(mode)
        # "path" torna a tabela EXTERNA: os arquivos ficam no caminho da
        # convenção, e o catálogo só guarda o endereço.
        .option("path", storage.path(layer, product, table))
    )
    if mode == "overwrite":
        # Permite que uma nova versão mude colunas (útil enquanto se desenvolve).
        writer = writer.option("overwriteSchema", "true")

    writer.saveAsTable(name)


def read_table(spark: SparkSession, layer: str, product: str, table: str) -> DataFrame:
    """Lê uma tabela pelo nome no catálogo."""
    return spark.read.table(table_name(layer, product, table))
