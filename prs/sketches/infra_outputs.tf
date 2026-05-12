output "droplet_id" {
  value = digitalocean_droplet.sask.id
}

output "floating_ip" {
  value = digitalocean_floating_ip.sask.ip_address
}

output "next_steps" {
  value = <<-EOT

    ╭─ sask droplet provisioned ──────────────────────────────────────╮
    │                                                                 │
    │  Floating IP: ${digitalocean_floating_ip.sask.ip_address}
    │                                                                 │
    │  Next steps:                                                    │
    │  1. At GoDaddy, set A record:                                   │
    │       sask.davidstitt.net → ${digitalocean_floating_ip.sask.ip_address}
    │  2. Wait for DNS propagation:                                   │
    │       dig +short sask.davidstitt.net                            │
    │  3. Test SSH:                                                   │
    │       ssh sask-droplet                                          │
    │     or                                                          │
    │       scripts/connect.sh                                        │
    │                                                                 │
    │  To tear down:                                                  │
    │       scripts/destroy.sh                                        │
    │                                                                 │
    ╰─────────────────────────────────────────────────────────────────╯
  EOT
}

