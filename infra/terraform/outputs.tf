output "vm_name" {
  value = google_compute_instance.vm.name
}

output "zone" {
  value = google_compute_instance.vm.zone
}

output "external_ip" {
  description = "IP externo atual (muda a cada stop/start)"
  value       = google_compute_instance.vm.network_interface[0].access_config[0].nat_ip
}

output "ssh_command" {
  value = "gcloud compute ssh ${google_compute_instance.vm.name} --zone ${google_compute_instance.vm.zone} --tunnel-through-iap"
}

output "stop_command" {
  value = "gcloud compute instances stop ${google_compute_instance.vm.name} --zone ${google_compute_instance.vm.zone}"
}

output "start_command" {
  value = "gcloud compute instances start ${google_compute_instance.vm.name} --zone ${google_compute_instance.vm.zone}"
}
