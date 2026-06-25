output "reserved_ip" {
  description = "The stable IP that survives destroy/recreate; DNS and the SSH alias both target this."
  value       = digitalocean_reserved_ip.sask.ip_address
}

output "droplet_id" {
  description = "The current droplet's ID (changes every destroy/recreate, unlike the reserved IP)."
  value       = digitalocean_droplet.sask.id
}

output "droplet_size" {
  description = "DigitalOcean size slug (e.g. s-1vcpu-1gb) — host identity stamp for SPEC-025 perf results."
  value       = digitalocean_droplet.sask.size
}

output "droplet_region" {
  description = "DigitalOcean region slug (e.g. fra1) — host identity stamp for SPEC-025 perf results."
  value       = digitalocean_droplet.sask.region
}

output "droplet_vcpus" {
  description = "Provider-reported vCPU count — host identity stamp for SPEC-025 perf results."
  value       = digitalocean_droplet.sask.vcpus
}

output "fqdn" {
  description = "The public domain name pointed at the reserved IP."
  value       = local.fqdn
}

output "next_steps" {
  description = "Reminder of what still needs to happen after `tofu apply`."
  value       = <<-EOT
    Droplet created. Next:
      1. ssh -o User=root ${var.droplet_name}   # only account that exists so far
      2. Run the SPEC-023 Ansible bootstrap + site.yml play (tools/ops/deploy.sh) to
         create ${var.ssh_admin_user}, configure the host, and disable root login.
         After that, the plain alias (`ssh ${var.droplet_name}`) connects as
         ${var.ssh_admin_user}.
      3. DNS for ${local.fqdn} may take a few minutes to propagate.
  EOT
}
