locals {
  fqdn = "${var.subdomain}.${var.domain}"
}

# Used to scope the firewall's SSH rule to the developer's current IP only.
data "http" "developer_ip" {
  url = "https://api.ipify.org"
}

# Fails fast at plan time if var.domain isn't already DO-nameservered.
data "digitalocean_domain" "parent_zone" {
  name = var.domain
}

resource "digitalocean_ssh_key" "sask" {
  name       = "sask"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

# No cloud-init — Ansible owns all droplet configuration from a clean image.
resource "digitalocean_droplet" "sask" {
  name     = var.droplet_name
  region   = var.region
  size     = var.droplet_size
  image    = var.droplet_image
  ssh_keys = [digitalocean_ssh_key.sask.id]
}

# Reserved IP survives destroy/recreate — DNS and the SSH alias target this,
# not the droplet, so neither changes across a destroy/reprovision cycle.
resource "digitalocean_reserved_ip" "sask" {
  region = var.region
}

resource "digitalocean_reserved_ip_assignment" "sask" {
  ip_address = digitalocean_reserved_ip.sask.ip_address
  droplet_id = digitalocean_droplet.sask.id
}

resource "digitalocean_record" "sask" {
  domain = data.digitalocean_domain.parent_zone.name
  type   = "A"
  name   = var.subdomain
  value  = digitalocean_reserved_ip.sask.ip_address
  ttl    = 300
}

resource "digitalocean_firewall" "sask" {
  name        = "sask-firewall"
  droplet_ids = [digitalocean_droplet.sask.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["${chomp(data.http.developer_ip.response_body)}/32"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}
