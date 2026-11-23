variable "aws_region" {
  description = "AWS region for provisioning"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix identifier for all resources"
  type        = string
  default     = "int333-devops"
}

variable "environment" {
  description = "Deployment environment (dev/staging/prod)"
  type        = string
  default     = "dev"
}

variable "enable_aws" {
  description = "Set to true to provision on real AWS, or false for local/simulated configuration"
  type        = bool
  default     = false
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "Public Subnet CIDR block"
  type        = string
  default     = "10.0.1.0/24"
}

variable "ami_id" {
  description = "Ubuntu 22.04 LTS AMI ID"
  type        = string
  default     = "ami-0c7217cdde317cfec" # Canonical Ubuntu 22.04 LTS (us-east-1)
}

variable "instance_type" {
  description = "EC2 instance size"
  type        = string
  default     = "t2.micro"
}

variable "key_pair_name" {
  description = "SSH Key pair name for EC2 instances"
  type        = string
  default     = "devops-key"
}

variable "ssh_user" {
  description = "Default SSH user for configuration management"
  type        = string
  default     = "ubuntu"
}

variable "simulated_web_ip" {
  description = "IP address used when running locally / simulated"
  type        = string
  default     = "192.168.56.10"
}

variable "simulated_nagios_ip" {
  description = "IP address for Nagios server when simulated"
  type        = string
  default     = "192.168.56.20"
}
