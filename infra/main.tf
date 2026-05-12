# --------------------------------------------------------------------------
# Data sources
# --------------------------------------------------------------------------

# Developer's current public IP — used to restrict SSH inbound to one address.
data "http" "developer_ip" {
  url = "https://api.ipify.org"
}

# Verify the managed domain exists in DO before attempting to create records.
# Fails fast at plan time if the domain is missing, rather than during apply.
data "digitalocean_domain" "davidstitt_net" {
  name = "davidstitt.net"
}

locals {
  developer_ip_cidr = "${chomp(data.http.developer_ip.response_body)}/32"
}

# --------------------------------------------------------------------------
# SSH key
# --------------------------------------------------------------------------

# Register the project SSH key with DO.
resource "digitalocean_ssh_key" "sask" {
  name       = "${var.project_name}-deploy"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

# --------------------------------------------------------------------------
# Droplet
# --------------------------------------------------------------------------

resource "digitalocean_droplet" "sask" {
  name     = "${var.project_name}-prod"
  region   = var.region
  size     = var.droplet_size
  image    = var.droplet_image
  ssh_keys = [digitalocean_ssh_key.sask.fingerprint]

  # No cloud-init; Ansible handles configuration in PR-004.
}

# --------------------------------------------------------------------------
# Networking: reserved IP
# --------------------------------------------------------------------------

resource "digitalocean_reserved_ip" "sask" {
  region = var.region
}

resource "digitalocean_reserved_ip_assignment" "sask" {
  ip_address = digitalocean_reserved_ip.sask.ip_address
  droplet_id = digitalocean_droplet.sask.id
}

# --------------------------------------------------------------------------
# DNS
# --------------------------------------------------------------------------

# A record: sask.davidstitt.net -> reserved IP.
# davidstitt.net is a pre-existing managed domain in the DO account.
resource "digitalocean_record" "sask" {
  domain = data.digitalocean_domain.davidstitt_net.name
  type   = "A"
  name   = "sask"
  value  = digitalocean_reserved_ip.sask.ip_address
  ttl    = 300
}

# --------------------------------------------------------------------------
# Firewall
# --------------------------------------------------------------------------

resource "digitalocean_firewall" "sask" {
  name        = "${var.project_name}-firewall"
  droplet_ids = [digitalocean_droplet.sask.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = [local.developer_ip_cidr]
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
