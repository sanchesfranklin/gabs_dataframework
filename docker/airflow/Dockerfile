# =============================================================================
# Airflow 3 + Spark (modo local) + Delta Lake + conectores S3 e PostgreSQL
#
# Os jobs Spark rodam dentro do próprio contêiner do Airflow, cada tarefa
# abrindo e fechando a sua sessão. As versões chegam do docker-compose
# (âncora x-spark-build-args), as mesmas usadas no Jupyter.
# =============================================================================
FROM apache/airflow:3.3.2-python3.11

ARG PYSPARK_VERSION
ARG DELTA_VERSION
ARG HADOOP_AWS_VERSION
ARG AWS_SDK_VERSION
ARG POSTGRES_JDBC_VERSION

# Java para o Spark (a imagem do Airflow é baseada em Debian bookworm)
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

USER airflow

# Fixar apache-airflow na versão da imagem impede o pip de trocá-la por outra
# ao instalar as dependências do Spark.
RUN pip install --no-cache-dir \
      "apache-airflow==${AIRFLOW_VERSION}" \
      "pyspark==${PYSPARK_VERSION}" \
      "delta-spark==${DELTA_VERSION}"

# Jars na pasta do Spark: Delta, S3A (MinIO) e driver JDBC do PostgreSQL
RUN set -eux; \
    JARS="$(python -c 'import os, pyspark; print(os.path.join(os.path.dirname(pyspark.__file__), "jars"))')"; \
    MVN="https://repo1.maven.org/maven2"; \
    cd "$JARS"; \
    curl -fsSLO "$MVN/io/delta/delta-spark_2.12/${DELTA_VERSION}/delta-spark_2.12-${DELTA_VERSION}.jar"; \
    curl -fsSLO "$MVN/io/delta/delta-storage/${DELTA_VERSION}/delta-storage-${DELTA_VERSION}.jar"; \
    curl -fsSLO "$MVN/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar"; \
    curl -fsSLO "$MVN/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar"; \
    curl -fsSLO "$MVN/org/postgresql/postgresql/${POSTGRES_JDBC_VERSION}/postgresql-${POSTGRES_JDBC_VERSION}.jar"
