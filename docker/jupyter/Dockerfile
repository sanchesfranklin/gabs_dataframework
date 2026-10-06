# =============================================================================
# Imagem do Jupyter com PySpark + Delta Lake + acesso a S3 (MinIO)
#
# As quatro versões abaixo PRECISAM combinar entre si. É o ponto que mais dá
# erro em quem monta essa stack:
#
#   PySpark 3.5.x  <->  Delta Lake 3.3.x      (tabela de compatibilidade do Delta)
#   PySpark 3.5.x  já traz o Hadoop 3.3.4  ->  hadoop-aws tem de ser 3.3.4
#   hadoop-aws 3.3.4  foi compilado com    ->  aws-java-sdk-bundle 1.12.262
#   PySpark 3.5.x usa Scala 2.12           ->  o jar do Delta é o "_2.12"
# =============================================================================
FROM python:3.11-slim-bookworm

ARG PYSPARK_VERSION=3.5.6
ARG DELTA_VERSION=3.3.2
ARG HADOOP_AWS_VERSION=3.3.4
ARG AWS_SDK_VERSION=1.12.262

# Java (o Spark roda na JVM), curl (baixar os jars), procps (o Spark usa "ps"),
# tini (repassa sinais corretamente para o Jupyter ao parar o contêiner).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      openjdk-17-jre-headless curl procps tini \
 && rm -rf /var/lib/apt/lists/*

# O pacote pyspark já inclui o Spark inteiro. O delta-spark traz só a parte
# Python do Delta (o módulo "delta"); os jars vêm no passo seguinte.
RUN pip install --no-cache-dir \
      pyspark==${PYSPARK_VERSION} \
      delta-spark==${DELTA_VERSION} \
      "jupyterlab>=4,<5" \
      pandas \
      pyarrow

# Jars colocados direto na pasta de jars do Spark: assim toda sessão já nasce
# com Delta e S3 disponíveis, sem baixar nada na hora de abrir o notebook.
RUN set -eux; \
    JARS="$(python -c 'import os, pyspark; print(os.path.join(os.path.dirname(pyspark.__file__), "jars"))')"; \
    MVN="https://repo1.maven.org/maven2"; \
    cd "$JARS"; \
    curl -fsSLO "$MVN/io/delta/delta-spark_2.12/${DELTA_VERSION}/delta-spark_2.12-${DELTA_VERSION}.jar"; \
    curl -fsSLO "$MVN/io/delta/delta-storage/${DELTA_VERSION}/delta-storage-${DELTA_VERSION}.jar"; \
    curl -fsSLO "$MVN/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar"; \
    curl -fsSLO "$MVN/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar"

# Usuário comum com o MESMO id do seu usuário na máquina hospedeira. Sem isso,
# os notebooks salvos apareceriam como arquivos do root na pasta do projeto.
ARG UID=1000
ARG GID=1000
RUN groupadd -o -g "${GID}" gabs \
 && useradd -l -o -m -u "${UID}" -g "${GID}" -s /bin/bash gabs \
 && mkdir -p /workspace \
 && chown gabs:gabs /workspace

USER gabs
WORKDIR /workspace
EXPOSE 8888 4040

# O token de acesso vem da variável de ambiente JUPYTER_TOKEN.
ENTRYPOINT ["tini", "--"]
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--ServerApp.root_dir=/workspace/notebooks"]
