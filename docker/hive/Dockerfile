# =============================================================================
# Hive Metastore 3.1.3 (só o serviço de catálogo, sem o HiveServer2)
#
# Por que 3.1.3 e não 4.x: o Spark 3.5 conversa com o Metastore usando um
# cliente Hive 2.3.9 embutido. A combinação Spark 3.5 + Metastore 3.1 é a mais
# usada e testada em ambientes como este; o Trino também lê bem esse catálogo.
# =============================================================================
FROM apache/hive:3.1.3

ARG POSTGRES_JDBC_VERSION=42.7.4

USER root

# 1. Conector S3A: já vem na distribuição do Hadoop dentro da imagem, mas fora
#    do classpath. Copiar para a pasta lib do Hive o coloca em uso. Sem ele,
#    o Metastore não consegue criar pastas em s3a:// ao registrar tabelas.
RUN cp /opt/hadoop/share/hadoop/tools/lib/hadoop-aws-*.jar \
       /opt/hadoop/share/hadoop/tools/lib/aws-java-sdk-bundle-*.jar \
       /opt/hive/lib/

# 2. Driver JDBC do PostgreSQL, onde o catálogo fica gravado. O Hive 3.1.3 traz
#    um driver de 2016 que não suporta a autenticação SCRAM-SHA-256, padrão do
#    PostgreSQL desde a versão 14. Ele é removido e trocado por um atual.
RUN rm -f /opt/hive/lib/postgresql-*.jar
ADD https://repo1.maven.org/maven2/org/postgresql/postgresql/${POSTGRES_JDBC_VERSION}/postgresql-${POSTGRES_JDBC_VERSION}.jar \
    /opt/hive/lib/postgresql.jar

# 3. Script de inicialização próprio (cria o schema só na primeira vez).
COPY start-metastore.sh /opt/start-metastore.sh
RUN chmod 644 /opt/hive/lib/postgresql.jar && chmod 755 /opt/start-metastore.sh

USER hive
EXPOSE 9083
ENTRYPOINT ["/opt/start-metastore.sh"]
