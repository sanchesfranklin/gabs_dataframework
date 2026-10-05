variable "project_id" {
  description = "ID do projeto no GCP (ex.: lakehouse-lab-123456)"
  type        = string
}

variable "my_ip_cidr" {
  description = "Seu IP público com /32 no final (ex.: 187.10.20.30/32). Pegue no navegador do SEU computador, não no Cloud Shell."
  type        = string
}

variable "prefix" {
  description = "Prefixo usado no nome de todos os recursos"
  type        = string
  default     = "lakehouse"
}

variable "region" {
  description = "Região (us-central1 é das mais baratas)"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zona dentro da região"
  type        = string
  default     = "us-central1-a"
}

variable "machine_type" {
  description = "Tipo da VM. e2-standard-8 = 8 vCPU / 32 GB (o trial permite no máximo 8 vCPUs ao mesmo tempo)"
  type        = string
  default     = "e2-standard-8"
}

variable "boot_disk_gb" {
  description = "Tamanho do disco do sistema (GB)"
  type        = number
  default     = 30
}

variable "data_disk_gb" {
  description = "Tamanho do disco de dados /data, onde ficam imagens Docker e volumes (GB)"
  type        = number
  default     = 100
}

variable "use_spot" {
  description = "true = VM Spot (cerca de metade do preço, mas o Google pode desligá-la a qualquer momento)"
  type        = bool
  default     = false
}

variable "auto_stop_cron" {
  description = "Cron do desligamento automático diário (no fuso de var.timezone)"
  type        = string
  default     = "0 23 * * *"
}

variable "timezone" {
  description = "Fuso horário do agendamento"
  type        = string
  default     = "America/Sao_Paulo"
}

variable "ui_ports" {
  description = "Portas das interfaces web a liberar para o seu IP (ex.: [\"9001\", \"8080\"]). Vazio = nenhuma; acesse por túnel SSH."
  type        = list(string)
  default     = []
}
