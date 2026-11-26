# Infrastructure for the Configuration Drift Detection lab:
#   - a private network
#   - N fleet machines (node1..nodeN) that must all stay identically configured
#   - 1 control machine that runs Ansible + Nagios
#   - an SSH key pair so Ansible can log in to the fleet
#   - the Ansible inventory, generated from what was actually created

locals {
  node_names = [for i in range(var.node_count) : "node${i + 1}"]
  # .10 = control, .11, .12, ... = fleet nodes
  control_ip = cidrhost(var.subnet, 10)
  node_ips   = { for i, name in local.node_names : name => cidrhost(var.subnet, 11 + i) }

  ansible_dir = abspath("${path.module}/../ansible")
}

# ---------------------------------------------------------------- SSH access
resource "tls_private_key" "ansible" {
  algorithm = "ED25519"
}

# ---------------------------------------------------------------- network
resource "docker_network" "lab" {
  name = "${var.project}-net"

  ipam_config {
    subnet  = var.subnet
    gateway = cidrhost(var.subnet, 1) # stated explicitly so Docker's default doesn't show up as drift
  }
}

# ---------------------------------------------------------------- machine images
resource "docker_image" "node" {
  name         = "${var.project}-node:latest"
  keep_locally = true

  build {
    context = "${path.module}/images/node"
  }

  triggers = {
    source = sha1(join("", [for f in fileset("${path.module}/images/node", "*") : filesha1("${path.module}/images/node/${f}")]))
  }
}

resource "docker_image" "control" {
  name         = "${var.project}-control:latest"
  keep_locally = true

  build {
    context = "${path.module}/images/control"
  }

  triggers = {
    source = sha1(join("", [for f in fileset("${path.module}/images/control", "*") : filesha1("${path.module}/images/control/${f}")]))
  }
}

# ---------------------------------------------------------------- fleet machines
resource "docker_container" "node" {
  for_each = local.node_ips

  name     = each.key
  hostname = each.key
  image    = docker_image.node.image_id
  init     = true
  restart  = "unless-stopped"

  env = ["SSH_PUBLIC_KEY=${trimspace(tls_private_key.ansible.public_key_openssh)}"]

  networks_advanced {
    name         = docker_network.lab.id
    ipv4_address = each.value
  }

  # Each node's website, so you can see the effect of drift in a browser
  ports {
    internal = 80
    external = var.node_web_port_start + index(local.node_names, each.key)
  }

  labels {
    label = "project"
    value = var.project
  }
  labels {
    label = "role"
    value = "fleet"
  }
}

# ---------------------------------------------------------------- control machine
resource "docker_container" "control" {
  name     = "control"
  hostname = "control"
  image    = docker_image.control.image_id
  init     = true
  restart  = "unless-stopped"

  env = ["ANSIBLE_CONFIG=/opt/drift/ansible/ansible.cfg"]

  networks_advanced {
    name         = docker_network.lab.id
    ipv4_address = local.control_ip
  }

  ports {
    internal = 80
    external = var.nagios_port
  }

  # The Ansible project (the "desired state") is shared read-only from this repository
  volumes {
    host_path      = local.ansible_dir
    container_path = "/opt/drift/ansible"
    read_only      = true
  }

  upload {
    content = tls_private_key.ansible.private_key_openssh
    file    = "/opt/drift/keys/id_ed25519"
  }

  labels {
    label = "project"
    value = var.project
  }
  labels {
    label = "role"
    value = "control"
  }

  depends_on = [docker_container.node]
}

# ---------------------------------------------------------------- Ansible inventory
resource "local_file" "inventory" {
  filename        = "${local.ansible_dir}/inventory/hosts.ini"
  file_permission = "0644"
  content = templatefile("${path.module}/inventory.tftpl", {
    nodes      = local.node_ips
    control_ip = local.control_ip
  })
}
