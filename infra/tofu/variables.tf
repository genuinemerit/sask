variable "region" {
  description = "DigitalOcean region for the droplet and reserved IP."
  type        = string
  default     = "fra1"
}

variable "droplet_size" {
  description = "DigitalOcean droplet size slug."
  type        = string
  default     = "s-1vcpu-1gb"
}

variable "droplet_image" {
  description = "DigitalOcean base image slug."
  type        = string
  default     = "ubuntu-24-04-x64"
}

variable "droplet_name" {
  description = "DigitalOcean-visible droplet name; also the SSH alias provision.sh writes."
  type        = string
  default     = "sask-droplet"
}

variable "ssh_public_key_path" {
  description = "Path to the public key registered with DigitalOcean and the droplet."
  type        = string
  default     = "~/.ssh/sask_ed25519.pub"
}

variable "ssh_private_key_name" {
  description = "Filename, under ~/.ssh/, of the private key matching ssh_public_key_path."
  type        = string
  default     = "sask_ed25519"
}

variable "ssh_admin_user" {
  description = "Non-root SSH/admin login account Ansible bootstraps on first connection (distinct from the no-shell `sask` service user)."
  type        = string
  default     = "dave"
}

variable "ssh_config_path" {
  description = "Path to the generated SSH config snippet for the droplet alias."
  type        = string
  default     = "~/.ssh/config.d/sask"
}

variable "domain" {
  description = "Parent DNS zone already managed by DigitalOcean (must be DO-nameservered)."
  type        = string
  default     = "davidstitt.net"
}

variable "subdomain" {
  description = "Subdomain the app is served on, under var.domain."
  type        = string
  default     = "sask"
}
