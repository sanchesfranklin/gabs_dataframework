"""Criação da sessão Spark já configurada para Delta Lake, MinIO e o catálogo.

Sem esta função, todo notebook e todo job repetiria as mesmas configurações.
Tudo o que muda entre ambientes vem de variáveis de ambiente, definidas no
docker-compose, nunca escritas no código.
"""

import os

from pyspark.sql import SparkSession


def get_spark_session(app_name: str = "gabs") -> SparkSession:
    """Devolve uma SparkSession pronta para ler e gravar Delta em s3a://.

    Se HIVE_METASTORE_URI estiver definida, a sessão também usa o Hive
    Metastore como catálogo: tabelas gravadas com saveAsTable ficam
    registradas e visíveis para o Trino.
    """
    endpoint = os.environ["S3_ENDPOINT"]
    access_key = os.environ["S3_ACCESS_KEY"]
    secret_key = os.environ["S3_SECRET_KEY"]
    metastore_uri = os.environ.get("HIVE_METASTORE_URI")

    builder = (
        SparkSession.builder.appName(app_name)
        # REVIEW Quando tiver o cluster Spark, a variável SPARK_MASTER vai apontar para ele.
        # por enquanto está rodando localmente.
        .master(os.environ.get("SPARK_MASTER", "local[*]"))
        .config("spark.driver.memory", os.environ.get("SPARK_DRIVER_MEMORY", "1g"))
        # Número de partições depois de joins e agregações. O padrão (200) é
        # pensado para clusters; com dados pequenos e poucos núcleos, gera
        # centenas de tarefas minúsculas e deixa tudo lento.
        .config("spark.sql.shuffle.partitions", os.environ.get("SPARK_SHUFFLE_PARTITIONS", "4"))

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
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", str(endpoint.startswith("https")).lower())
        # Usa só a chave e a senha acima, sem procurar credenciais da AWS.
        .config(
            "spark.hadoop.fs.s3a.aws.credentials.provider",
            "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider",
        )
    )

    # --- Catálogo (Hive Metastore) -------------------------------------------
    # enableHiveSupport troca o catálogo em memória do Spark pelo Metastore.
    # Sem isso, as tabelas criadas existiriam só enquanto a sessão estivesse
    # aberta, e nenhuma outra ferramenta as enxergaria.
    if metastore_uri:
        builder = builder.enableHiveSupport().config(
            "spark.hadoop.hive.metastore.uris", metastore_uri
        )

    return builder.getOrCreate()
