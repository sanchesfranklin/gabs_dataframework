#!/bin/bash
# Inicia o Hive Metastore. Na primeira vez, cria as tabelas internas do
# catálogo no banco "metastore" do PostgreSQL. Nas seguintes, só sobe.
set -euo pipefail

# Memória e credenciais do banco chegam por SERVICE_OPTS (docker-compose).
export HADOOP_CLIENT_OPTS="${HADOOP_CLIENT_OPTS:-} ${SERVICE_OPTS:-}"

if /opt/hive/bin/schematool -dbType postgres -info >/dev/null 2>&1; then
  echo ">> Schema do Metastore já existe. Subindo o serviço."
else
  echo ">> Schema do Metastore não encontrado. Criando (só acontece uma vez)..."
  /opt/hive/bin/schematool -dbType postgres -initSchema
fi

exec /opt/hive/bin/hive --skiphadoopversion --skiphbasecp --service metastore
