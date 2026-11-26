output "nagios_url" {
  description = "Nagios dashboard (user: nagiosadmin, password: see ansible/group_vars/all.yml)"
  value       = "http://localhost:${var.nagios_port}/nagios4"
}

output "node_websites" {
  description = "Each fleet machine's website"
  value       = { for i, name in local.node_names : name => "http://localhost:${var.node_web_port_start + i}" }
}

output "fleet_ips" {
  description = "Private IP address of every fleet machine"
  value       = local.node_ips
}

output "next_step" {
  value = "Configure everything with:  docker exec control ansible-playbook /opt/drift/ansible/site.yml"
}
