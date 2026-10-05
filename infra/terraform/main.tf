###############################################################################
# Lakehouse Lab - Fase 0: infraestrutura base no GCP
#
# O que este arquivo cria:
#   1. Rede própria (VPC + sub-rede), em vez de usar a rede "default"
#   2. Firewall: SSH liberado só para o seu IP (e para o IAP do Google)
#   3. Service account dedicada para a VM (princípio do menor privilégio)
#   4. Disco de dados separado (/data), que sobrevive se a VM for recriada
#   5. Política de desligamento automático (rede de segurança contra esquecer
#      a VM ligada)
#   6. A VM em si, com Ubuntu 24.04 + Docker instalado pelo startup.sh
###############################################################################

terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# Usado para descobrir o número do projeto (necessário para o agendamento).
data "google_project" "this" {}

# -----------------------------------------------------------------------------
# 1. Rede
# -----------------------------------------------------------------------------
resource "google_compute_network" "vpc" {
  name                    = "${var.prefix}-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet" {
  name          = "${var.prefix}-subnet"
  region        = var.region
  network       = google_compute_network.vpc.id
  ip_cidr_range = "10.10.0.0/24"
}

# -----------------------------------------------------------------------------
# 2. Firewall
# -----------------------------------------------------------------------------
# SSH: seu IP + faixa do IAP (35.235.240.0/20), que é o que permite o botão
# "SSH" do console e o "gcloud compute ssh --tunnel-through-iap" funcionarem
# mesmo se o seu IP residencial mudar.
resource "google_compute_firewall" "ssh" {
  name      = "${var.prefix}-allow-ssh"
  network   = google_compute_network.vpc.name
  direction = "INGRESS"

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = [var.my_ip_cidr, "35.235.240.0/20"]
  target_tags   = ["lakehouse"]
}

# Portas das interfaces web (MinIO, Airflow, Jupyter...). Só é criada se você
# preencher ui_ports. Atenção: no GCP, uma regra sem lista de portas libera
# TODAS as portas, por isso o "count" evita criar a regra vazia.
resource "google_compute_firewall" "ui" {
  count = length(var.ui_ports) > 0 ? 1 : 0

  name      = "${var.prefix}-allow-ui"
  network   = google_compute_network.vpc.name
  direction = "INGRESS"

  allow {
    protocol = "tcp"
    ports    = var.ui_ports
  }

  source_ranges = [var.my_ip_cidr]
  target_tags   = ["lakehouse"]
}

# -----------------------------------------------------------------------------
# 3. Service account da VM
# -----------------------------------------------------------------------------
resource "google_service_account" "vm" {
  account_id   = "${var.prefix}-vm"
  display_name = "Service account da VM do Lakehouse Lab"
}

resource "google_project_iam_member" "vm_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.vm.email}"
}

resource "google_project_iam_member" "vm_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.vm.email}"
}

# -----------------------------------------------------------------------------
# 4. Disco de dados (montado em /data pelo startup.sh)
# -----------------------------------------------------------------------------
resource "google_compute_disk" "data" {
  name = "${var.prefix}-data"
  type = "pd-balanced"
  zone = var.zone
  size = var.data_disk_gb
}

# -----------------------------------------------------------------------------
# 5. Desligamento automático diário
# -----------------------------------------------------------------------------
resource "google_compute_resource_policy" "auto_stop" {
  name   = "${var.prefix}-auto-stop"
  region = var.region

  instance_schedule_policy {
    time_zone = var.timezone

    vm_stop_schedule {
      schedule = var.auto_stop_cron
    }
  }
}

# O agendador roda como o "Compute Engine Service Agent" do projeto, que
# precisa de permissão para parar a VM.
resource "google_project_iam_member" "scheduler_can_stop" {
  project = var.project_id
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:service-${data.google_project.this.number}@compute-system.iam.gserviceaccount.com"
}

# -----------------------------------------------------------------------------
# 6. A VM
# -----------------------------------------------------------------------------
resource "google_compute_instance" "vm" {
  name         = "${var.prefix}-vm"
  machine_type = var.machine_type
  zone         = var.zone
  tags         = ["lakehouse"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = var.boot_disk_gb
      type  = "pd-balanced"
    }
  }

  attached_disk {
    source      = google_compute_disk.data.id
    device_name = "data" # aparece na VM como /dev/disk/by-id/google-data
  }

  network_interface {
    subnetwork = google_compute_subnetwork.subnet.id

    # IP externo efêmero (gratuito). Muda a cada stop/start, o que não
    # atrapalha: você conecta pelo nome da VM com o gcloud.
    access_config {}
  }

  metadata = {
    enable-oslogin = "TRUE"
    # Usar a chave "startup-script" (e não metadata_startup_script) permite
    # alterar o script sem recriar a VM.
    startup-script = file("${path.module}/startup.sh")
  }

  service_account {
    email  = google_service_account.vm.email
    scopes = ["cloud-platform"]
  }

  scheduling {
    provisioning_model          = var.use_spot ? "SPOT" : "STANDARD"
    preemptible                 = var.use_spot
    automatic_restart           = var.use_spot ? false : true
    on_host_maintenance         = var.use_spot ? "TERMINATE" : "MIGRATE"
    instance_termination_action = var.use_spot ? "STOP" : null
  }

  resource_policies         = [google_compute_resource_policy.auto_stop.id]
  allow_stopping_for_update = true

  depends_on = [
    google_project_iam_member.scheduler_can_stop,
    google_compute_firewall.ssh,
  ]
}
