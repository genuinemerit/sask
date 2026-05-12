# Fetch the developer's current public IP so the firewall allows SSH only from here.
data "http" "developer_ip" {
  url = "https://api.ipify.org"
}

locals {
  developer_ip_cidr = "${chomp(data.http.developer_ip.response_body)}/32"
}

# Register the project SSH key with DO.
resource "digitalocean_ssh_key" "sask" {
  name       = "${var.project_name}-deploy"
  public_key = file(pathexpand(var.ssh_public_key_path))
}

# The droplet itself.
resource "digitalocean_droplet" "sask" {
  name     = "${var.project_name}-prod"
  region   = var.region
  size     = var.droplet_size
  image    = var.droplet_image
  ssh_keys = [digitalocean_ssh_key.sask.fingerprint]

  # No cloud-init; Ansible handles configuration in PR-004.
}

# Floating IP, attached to the droplet.
resource "digitalocean_floating_ip" "sask" {
  region = var.region
}

resource "digitalocean_floating_ip_assignment" "sask" {
  ip_address = digitalocean_floating_ip.sask.ip_address
  droplet_id = digitalocean_droplet.sask.id
}

# Cloud firewall.
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
