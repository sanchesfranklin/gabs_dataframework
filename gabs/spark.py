"""Criação da sessão Spark já configurada para Delta Lake e MinIO.

Sem esta função, todo notebook e todo job repetiria as mesmas dez linhas de
configuração. As credenciais vêm de variáveis de ambiente (definidas no
docker-compose), nunca escritas no código.
"""

import os

from pyspark.sql import SparkSession


def get_spark_session(app_name: str = "gabs") -> SparkSession:
    """Devolve uma SparkSession pronta para ler e gravar Delta em s3a://."""
    endpoint = os.environ["S3_ENDPOINT"]
    access_key = os.environ["S3_ACCESS_KEY"]
    secret_key = os.environ["S3_SECRET_KEY"]

    builder = (
        SparkSession.builder.appName(app_name)
        .master(os.environ.get("SPARK_MASTER", "local[*]"))
        .config("spark.driver.memory", os.environ.get("SPARK_DRIVER_MEMORY", "2g"))

        # --- Delta Lake ------------------------------------------------------
        # Ensina o Spark a entender o formato Delta e os comandos SQL dele
        # (MERGE, DESCRIBE HISTORY, VERSION AS OF...).
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")

        # --- S3A (o conector do Hadoop para S3) apontando para o MinIO -------
        .config("spark.hadoop.fs.s3a.endpoint", endpoint)
        .config("spark.hadoop.fs.s3a.access.key", access_key)
        .config("spark.hadoop.fs.s3a.secret.key", secret_key)
        # O MinIO usa endpoint/bucket/arquivo. A AWS usa bucket.endpoint/arquivo.
        # Sem esta linha, o Spark tentaria resolver "bronze.minio" e falharia.
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", str(endpoint.startswith("https")).lower())
        # Usa só a chave e a senha acima, sem procurar credenciais da AWS.
        .config(
            "spark.hadoop.fs.s3a.aws.credentials.provider",
            "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
        )
    )
    return builder.getOrCreate()
