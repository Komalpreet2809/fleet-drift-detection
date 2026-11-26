variable "docker_host" {
  description = "Docker engine to create the lab on. Windows/Docker Desktop default; use unix:///var/run/docker.sock on Linux/macOS."
  type        = string
  default     = "npipe:////./pipe/docker_engine"
}

variable "project" {
  description = "Prefix for every resource Terraform creates"
  type        = string
  default     = "drift"
}

variable "node_count" {
  description = "How many fleet machines to create (node1, node2, ...)"
  type        = number
  default     = 3

  validation {
    condition     = var.node_count >= 1 && var.node_count <= 9
    error_message = "node_count must be between 1 and 9."
  }
}

variable "subnet" {
  description = "Private network the machines live on"
  type        = string
  default     = "10.77.0.0/24"
}

variable "nagios_port" {
  description = "Port on your computer for the Nagios web UI"
  type        = number
  default     = 8090
}

variable "node_web_port_start" {
  description = "node1's website is published on this port, node2 on the next one, and so on"
  type        = number
  default     = 8091
}
