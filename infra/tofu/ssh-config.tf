# Targets var.ssh_admin_user, not root: that account doesn't exist on a
# freshly created droplet until Ansible's bootstrap play creates it (the
# only account a no-cloud-init droplet starts with is root, and Ansible's
# base role disables root login per REQ-SEC-003 once bootstrap is done).
# This file documents the long-term steady state, which the SPEC-023
# Ansible work is responsible for making true.
resource "local_file" "ssh_config" {
  filename        = pathexpand(var.ssh_config_path)
  file_permission = "0600"
  content         = <<-EOT
    Host ${var.droplet_name}
        HostName ${digitalocean_reserved_ip.sask.ip_address}
        User ${var.ssh_admin_user}
        IdentityFile ~/.ssh/${var.ssh_private_key_name}
        IdentitiesOnly yes
  EOT
}
