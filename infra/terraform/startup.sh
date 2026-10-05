#!/bin/bash
# Roda como root a CADA boot da VM, por isso cada etapa é idempotente
# (verifica antes de fazer). Log em /var/log/lakehouse-startup.log
set -euo pipefail
exec >>/var/log/lakehouse-startup.log 2>&1
echo "===== startup $(date -Is) ====="

DATA_DEV=/dev/disk/by-id/google-data
DATA_DIR=/data

# --- 1. Disco de dados: formata só na primeira vez e monta em /data --------
if ! blkid "$DATA_DEV" >/dev/null 2>&1; then
  echo "Formatando disco de dados..."
  mkfs.ext4 -m 0 -E lazy_itable_init=0,lazy_journal_init=0,discard "$DATA_DEV"
fi

mkdir -p "$DATA_DIR"
if ! mountpoint -q "$DATA_DIR"; then
  mount -o discard,defaults "$DATA_DEV" "$DATA_DIR"
fi

DATA_UUID=$(blkid -s UUID -o value "$DATA_DEV")
if ! grep -q "$DATA_UUID" /etc/fstab; then
  echo "UUID=$DATA_UUID $DATA_DIR ext4 discard,defaults,nofail 0 2" >> /etc/fstab
fi

mkdir -p "$DATA_DIR/docker" "$DATA_DIR/lakehouse"
chmod 777 "$DATA_DIR/lakehouse"

# --- 2. Ajustes do sistema ---------------------------------------------------
timedatectl set-timezone America/Sao_Paulo || true

# OpenSearch/Elasticsearch (usados pelo OpenMetadata na fase 6) exigem isso.
if [ ! -f /etc/sysctl.d/99-lakehouse.conf ]; then
  echo "vm.max_map_count=262144" > /etc/sysctl.d/99-lakehouse.conf
  sysctl --system
fi

# --- 3. Docker Engine + Docker Compose (repositório oficial) ----------------
if ! command -v docker >/dev/null 2>&1; then
  echo "Instalando Docker..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y ca-certificates curl git htop unzip jq

  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list

  # Imagens e volumes do Docker ficam no disco de dados, não no disco do sistema.
  mkdir -p /etc/docker
  cat > /etc/docker/daemon.json <<'EOF'
{
  "data-root": "/data/docker",
  "log-driver": "json-file",
  "log-opts": { "max-size": "50m", "max-file": "3" }
}
EOF

  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi

echo "OK: $(docker --version) | $(docker compose version)"
echo "===== fim do startup $(date -Is) ====="
