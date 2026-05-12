output "droplet_id" {
  value = digitalocean_droplet.sask.id
}

output "reserved_ip" {
  value = digitalocean_reserved_ip.sask.ip_address
}

output "next_steps" {
  value = <<-EOT

    sask droplet provisioned.

    Reserved IP: ${digitalocean_reserved_ip.sask.ip_address}
    DNS:         sask.davidstitt.net (managed by Tofu, will propagate shortly)

    Wait for propagation:
      dig +short sask.davidstitt.net

    Connect:
      ssh sask-droplet
        or
      scripts/connect.sh

    Tear down:
      scripts/destroy.sh
  EOT
}
