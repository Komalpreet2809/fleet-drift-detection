output "web_server_ip" {
  description = "Public IP address of the provisioned Web Server"
  value       = var.enable_aws ? (length(aws_instance.web_server) > 0 ? aws_instance.web_server[0].public_ip : "N/A") : var.simulated_web_ip
}

output "nagios_server_ip" {
  description = "Public IP address of the provisioned Nagios Server"
  value       = var.enable_aws ? (length(aws_instance.nagios_server) > 0 ? aws_instance.nagios_server[0].public_ip : "N/A") : var.simulated_nagios_ip
}

output "nagios_web_url" {
  description = "Direct URL to access the Nagios Core monitoring dashboard"
  value       = "http://${var.enable_aws ? (length(aws_instance.nagios_server) > 0 ? aws_instance.nagios_server[0].public_ip : "localhost") : "localhost:8080"}/nagios"
}

output "web_application_url" {
  description = "Direct URL to access the deployed Web Application"
  value       = "http://${var.enable_aws ? (length(aws_instance.web_server) > 0 ? aws_instance.web_server[0].public_ip : "localhost") : "localhost:5000"}"
}
