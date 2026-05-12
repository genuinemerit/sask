variable "project_name" {
  description = "Project name used as prefix for cloud resources."
  type        = string
  default     = "sask"
}

variable "region" {
  description = "DO region slug."
  type        = string
  default     = "fra1"
}

variable "droplet_size" {
  description = "DO droplet size slug."
  type        = string
  default     = "s-1vcpu-1gb"
}

variable "droplet_image" {
  description = "DO droplet image slug. Pinned for reproducibility."
  type        = string
  default     = "ubuntu-24-04-x64"
}

variable "ssh_public_key_path" {
  description = "Path to the SSH public key to register with DO."
  type        = string
  default     = "~/.ssh/sask_ed25519.pub"
}

variable "ssh_private_key_path" {
  description = "Path to the SSH private key (written into ssh-config snippet)."
  type        = string
  default     = "~/.ssh/sask_ed25519"
}

variable "ssh_config_snippet_path" {
  description = "Where to write the generated SSH config snippet."
  type        = string
  default     = "~/.ssh/config.d/sask"
}
