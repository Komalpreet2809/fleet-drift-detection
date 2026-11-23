# ==============================================================================
# INT333: DevOps Advance Configuration Management
# Terraform Infrastructure Configuration
# Integrates with Ansible by dynamically generating the inventory file.
# ==============================================================================

terraform {
  required_version = ">= 1.0.0"
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.4.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Provider configuration for AWS
provider "aws" {
  region = var.aws_region
}

# --- Network: VPC & Subnet ---
resource "aws_vpc" "devops_vpc" {
  count                = var.enable_aws ? 1 : 0
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "${var.project_name}-vpc"
    Environment = var.environment
    Course      = "INT333"
  }
}

resource "aws_internet_gateway" "devops_igw" {
  count  = var.enable_aws ? 1 : 0
  vpc_id = aws_vpc.devops_vpc[0].id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_subnet" "public_subnet" {
  count                   = var.enable_aws ? 1 : 0
  vpc_id                  = aws_vpc.devops_vpc[0].id
  cidr_block              = var.subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"

  tags = {
    Name = "${var.project_name}-public-subnet"
  }
}

resource "aws_route_table" "public_rt" {
  count  = var.enable_aws ? 1 : 0
  vpc_id = aws_vpc.devops_vpc[0].id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.devops_igw[0].id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public_assoc" {
  count          = var.enable_aws ? 1 : 0
  subnet_id      = aws_subnet.public_subnet[0].id
  route_table_id = aws_route_table.public_rt[0].id
}

# --- Security Groups ---
resource "aws_security_group" "web_sg" {
  count       = var.enable_aws ? 1 : 0
  name        = "${var.project_name}-web-sg"
  description = "Security group for Web Server (HTTP, SSH, App port)"
  vpc_id      = aws_vpc.devops_vpc[0].id

  ingress {
    description = "SSH from anywhere"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP Traffic"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "App Port (Flask / Web API)"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-web-sg"
  }
}

resource "aws_security_group" "nagios_sg" {
  count       = var.enable_aws ? 1 : 0
  name        = "${var.project_name}-nagios-sg"
  description = "Security group for Nagios Monitoring Server"
  vpc_id      = aws_vpc.devops_vpc[0].id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Nagios Web UI"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-nagios-sg"
  }
}

# --- EC2 Compute Instances ---
resource "aws_instance" "web_server" {
  count                  = var.enable_aws ? 1 : 0
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public_subnet[0].id
  vpc_security_group_ids = [aws_security_group.web_sg[0].id]
  key_name               = var.key_pair_name

  tags = {
    Name = "${var.project_name}-web-server"
    Role = "webserver"
  }
}

resource "aws_instance" "nagios_server" {
  count                  = var.enable_aws ? 1 : 0
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public_subnet[0].id
  vpc_security_group_ids = [aws_security_group.nagios_sg[0].id]
  key_name               = var.key_pair_name

  tags = {
    Name = "${var.project_name}-nagios-server"
    Role = "monitoring"
  }
}

# ==============================================================================
# Dynamic Integration: Generate Ansible Inventory
# Automatically populates IPs provisioned by Terraform into Ansible hosts.ini
# ==============================================================================
resource "local_file" "ansible_inventory" {
  filename = "${path.module}/../ansible/inventory/hosts.ini"
  content  = templatefile("${path.module}/inventory.tpl", {
    web_ip    = var.enable_aws ? (length(aws_instance.web_server) > 0 ? aws_instance.web_server[0].public_ip : "127.0.0.1") : var.simulated_web_ip
    nagios_ip = var.enable_aws ? (length(aws_instance.nagios_server) > 0 ? aws_instance.nagios_server[0].public_ip : "127.0.0.1") : var.simulated_nagios_ip
    ssh_user  = var.ssh_user
  })
}
