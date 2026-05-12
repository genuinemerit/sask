output "droplet_id" {
  value = digitalocean_droplet.sask.id
}

output "reserved_ip" {
  value = digitalocean_reserved_ip.sask.ip_address
}

output "next_steps" {
  value = <<-EOT

    sask droplet provisioned
    ========================
    Reserved IP : ${digitalocean_reserved_ip.sask.ip_address}
    Droplet ID  : ${digitalocean_droplet.sask.id}

    Next steps:
      1. At GoDaddy, set A record:
           sask.davidstitt.net -> ${digitalocean_reserved_ip.sask.ip_address}
      2. Wait for DNS propagation:
           dig +short sask.davidstitt.net
      3. Test SSH:
           ssh sask-droplet
         or
           scripts/connect.sh

    To tear down:
      scripts/destroy.sh

  EOT
}
