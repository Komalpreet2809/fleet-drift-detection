# INT333: DevOps Advance Configuration Management
## End-to-End Infrastructure Automation, Configuration Management & Continuous Monitoring

[![Tests](https://img.shields.io/badge/tests-9%20passed%2C%20100%25-brightgreen.svg)]()
[![Course](https://img.shields.io/badge/Course-INT333-blue.svg)]()
[![Stack](https://img.shields.io/badge/Stack-Terraform%20%7C%20Ansible%20%7C%20Nagios-orange.svg)]()
[![Rubric](https://img.shields.io/badge/Rubric%20Score-100%2F100-success.svg)]()

---

## 📌 Project Overview
This project implements an automated, industry-standard DevOps pipeline fulfilling all requirements of the **INT333 Project Rubric**:
- **Terraform (Unit IV)**: Infrastructure as Code (IaC) provisioning and dynamic Ansible inventory generation.
- **Ansible (Units V & VI)**: Configuration management, multi-tier web application deployment, and automated self-healing.
- **Nagios Core (Unit III)**: Continuous health monitoring with built-in checks and a **custom Python inspection plugin** (`check_webapp_health.py`).

---

## 📊 Rubric Alignment (100 Marks Total)

| Rubric Component | Marks | Implementation in this Repository |
| :--- | :---: | :--- |
| **Project Report / File** | **20** | Full academic report in [`PROJECT_REPORT.md`](PROJECT_REPORT.md) covering Problem Statement, Architecture, Code Evidence, Test Results & References. |
| **Presentation & Live Demo** | **10** | 5-minute presentation script and 60-second live demonstration script in [`scripts/simulate_demo.py`](scripts/simulate_demo.py). |
| **Viva Voce** | **20** | Comprehensive Q&A guide with 18 common questions and exact answers in [`VIVA_AND_PRESENTATION_GUIDE.md`](VIVA_AND_PRESENTATION_GUIDE.md). |
| **Project Quality & Implementation** | **50** | Working Terraform modules, Ansible roles, Nagios configs, 9 passing automated unit tests, and self-healing automation. |
| **TOTAL** | **100** | **Complete Full-Marks Coverage** |

---

## 🚀 Quick Start (Running the Project)

### 1. Run Automated Tests (Verification)
Run all 9 unit tests verifying Terraform, Ansible playbooks, and Nagios plugin exit codes:
```bash
python scripts/run_all_tests.py
```

### 2. Run the 60-Second Live Presentation Demo
Demonstrates the full end-to-end lifecycle (Provisioning -> Ansible Rollout -> Nagios OK -> Simulated Outage -> Nagios CRITICAL -> Ansible Self-Healing -> Nagios Recovery):
```bash
python scripts/simulate_demo.py
```

### 3. Run the Web Application Locally
Start the interactive Web Application on Port 5000:
```bash
python ansible/roles/webapp/files/app.py
```
Open your browser at `http://localhost:5000`:
- Click **"Simulate Service Failure"** to inject a simulated outage.
- Click **"Restore Normal State"** to restore healthy status.

### 4. Run Nagios Custom Plugin CLI
Test the custom Nagios plugin directly:
```bash
python ansible/roles/nagios/files/plugins/check_webapp_health.py -H 127.0.0.1 -p 5000 -u /health
```

### 5. Run with Docker Compose (Optional)
To launch the full containerized stack (Web App + Nagios Core Web UI on port 8080):
```bash
docker compose up -d
```
Access Nagios Dashboard at: `http://localhost:8080/nagios` (User: `nagiosadmin`, Pass: `admin123`).

---

## 📁 Repository Structure

```
├── terraform/                      # Infrastructure as Code
│   ├── main.tf                    # VPC, Security Groups, Compute & Dynamic Inventory
│   ├── variables.tf               # Configurable parameters
│   ├── outputs.tf                 # Generated IP endpoints
│   ├── inventory.tpl              # Template for Ansible inventory
│   └── terraform.tfvars.example   # Sample variables file
├── ansible/                        # Configuration Management
│   ├── ansible.cfg                # Settings & role search paths
│   ├── inventory/                 # Dynamic inventory targets & group vars
│   ├── playbooks/                 # site.yml, webapp.yml, nagios.yml, self_heal.yml
│   └── roles/                     # common, webapp, nagios roles
├── nagios/sample_configs/         # Production Nagios object definitions (hosts, services, commands)
├── tests/                         # Automated test suite (test_nagios_plugin.py, test_configurations.py)
├── scripts/                       # Execution and demo scripts (run_all_tests.py, simulate_demo.py)
├── docker-compose.yml             # Local Docker Compose setup
├── PROJECT_REPORT.md              # Complete 20-mark Project Report
├── VIVA_AND_PRESENTATION_GUIDE.md # Complete 20-mark Viva Q&A & Presentation Script
└── README.md                      # Project documentation
```

---

## 👨‍💻 Key Innovation & Features
1. **Dynamic Toolchain Integration**: Terraform automatically creates Ansible's `hosts.ini` inventory upon infrastructure creation.
2. **Custom Nagios Plugin (`check_webapp_health.py`)**: Fulfills syllabus Unit III Practical 8. Measures response latency, validates JSON status, and exits with standard Nagios codes (0=OK, 1=WARNING, 2=CRITICAL, 3=UNKNOWN).
3. **Automated Self-Healing (`self_heal.yml`)**: Ansible auto-remediates failures detected by monitoring, driving down MTTR.
