# Lakehouse Lab

Arquitetura de dados open source (MinIO, Spark, Delta Lake, Hive Metastore, Trino,
Airflow, Superset, OpenMetadata) montada do zero numa VM do Google Cloud.

## Estrutura

```
infra/terraform/   Fase 0: rede, firewall, VM, disco de dados e desligamento automático
```

## Comandos do dia a dia (no Cloud Shell)

```bash
# Ligar e desligar a VM (desligada, você paga só os discos)
gcloud compute instances start lakehouse-vm --zone us-central1-a
gcloud compute instances stop  lakehouse-vm --zone us-central1-a

# Entrar na VM
gcloud compute ssh lakehouse-vm --zone us-central1-a --tunnel-through-iap

# Ver o log da instalação inicial (dentro da VM)
sudo tail -f /var/log/lakehouse-startup.log
```

A VM também é desligada automaticamente todo dia às 23h (horário de Brasília).

## Aplicar mudanças na infraestrutura

```bash
cd infra/terraform
terraform plan    # mostra o que vai mudar
terraform apply   # aplica
```

## Destruir tudo (encerra os custos por completo)

```bash
cd infra/terraform
terraform destroy
```

Atenção: isso apaga também o disco `/data`, com tudo o que estiver nele.


© 2026 Sanches Franklin. Todos os direitos reservados.
Projeto de estudo. O código está disponível para consulta, sem licença de uso.
