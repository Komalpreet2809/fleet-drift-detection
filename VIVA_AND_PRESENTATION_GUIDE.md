# INT333: Viva Voce & Live Presentation Master Guide

---

## Part 1: 5-Minute Live Presentation & Demo Script (10 Marks)

### Slide / Speaking Plan (Allotted Time: 3-5 Minutes)

#### Minute 1: The Problem & What You Built
> *"Good morning/afternoon, professors. Today I am presenting our INT333 DevOps Project: **Automated Multi-Tier Infrastructure Provisioning, Configuration Management, and Real-Time Service Monitoring**.*
> 
> *In production environments, manual server setup causes configuration drift and silent service failures. To solve this, we implemented an end-to-end DevOps pipeline using **Terraform** for Infrastructure as Code, **Ansible** for configuration management, and **Nagios Core** for continuous monitoring, augmented by a custom Python plugin and an automated self-healing playbook."*

#### Minute 2: Architecture & Integration
> *"Our architecture integrates all three tools seamlessly:
> 1. **Terraform** provisions the network topology and compute instances, and dynamically outputs the IP addresses directly into an Ansible inventory using a template file.
> 2. **Ansible** executes our modular roles—configuring the base system, deploying our Python web microservice, and configuring Nagios Core.
> 3. **Nagios Core** polls the web server using standard ping/HTTP checks as well as our **custom Python health check plugin**.*
> 
> *Let me now demonstrate the system live in action."*

#### Minute 3-4: Live Demonstration (The Winning Sequence)
Run this command in terminal:
```bash
python scripts/simulate_demo.py
```
Or run the automated test suite:
```bash
python scripts/run_all_tests.py
```
Explain the output on the screen:
1. **Show Terraform output**: Point out that instances are provisioned and `hosts.ini` was created automatically.
2. **Show Ansible tasks**: Point out that roles ran with `changed` and `ok` status idempotently.
3. **Show Nagios baseline (OK - Green)**: Show that Nagios reports exit code `0` (OK).
4. **Trigger failure**: Point out that when a database failure occurs, Nagios catches it immediately and turns `CRITICAL` (Exit code `2`).
5. **Run Self-Healing Playbook**: Show Ansible auto-detecting the issue, restarting the service, and verifying the `/health` endpoint.
6. **Show Nagios Recovery**: Nagios immediately detects that health has been restored to `OK` (Green).

#### Minute 5: Conclusion & Q&A
> *"To conclude, this project satisfies all rubrics of INT333: clean modular code, automated test verification with 100% pass rate, and an innovative self-healing loop. I am now ready for Viva Voce questions."*

---

## Part 2: Viva Voce Top 20 Questions & Exact Answers (20 Marks)

### Category A: Conceptual Understanding (5 Marks)

**Q1: What is Infrastructure as Code (IaC) and what problem does it solve?**
* **Answer**: IaC is the practice of managing and provisioning computing infrastructure through machine-readable definition files rather than manual hardware configuration or interactive configuration tools. It ensures repeatability, version control, prevents human error, and eliminates environment drift.

**Q2: What is Configuration Drift?**
* **Answer**: Configuration drift occurs when modifications are made directly to running servers (e.g. emergency patches or manual tweaks) without updating the IaC or configuration management code. Over time, the server drifts from its documented baseline, causing inconsistent behavior and difficult debugging.

**Q3: How does Ansible differ from Puppet?**
* **Answer**: 
  - **Ansible** is *agentless* (push-based), communicating over standard SSH or WinRM without requiring a persistent daemon on client nodes. It uses YAML playbooks.
  - **Puppet** is *agent-based* (pull-based), requiring a Puppet Master and Puppet Agent daemon on each node with SSL certificate exchange. It uses its own Ruby-like declarative DSL.

**Q4: What is Idempotence in DevOps?**
* **Answer**: Idempotence means that running a configuration task or playbook multiple times produces the exact same end result without unintended side effects. If the target is already in the desired state, Ansible or Puppet makes no changes (`changed=0`).

**Q5: What are Soft States and Hard States in Nagios?**
* **Answer**:
  - **Soft State**: When a service check fails for the first time, it enters a Soft State. Nagios initiates retry checks at the `retry_interval` rather than immediately sending alert notifications.
  - **Hard State**: When a service remains in an error state for `max_check_attempts` consecutive checks, it transitions to a Hard State, and Nagios sends an alert to administrators.

---

### Category B: Technical Implementation Knowledge (5 Marks)

**Q6: What are the standard return codes for a Nagios plugin?**
* **Answer**:
  - `0`: **OK** (Service is functioning normally).
  - `1`: **WARNING** (Service is above warning threshold, e.g., high latency).
  - `2`: **CRITICAL** (Service is down or error condition detected).
  - `3`: **UNKNOWN** (Plugin could not determine status or invalid syntax).

**Q7: How did you implement the custom Nagios plugin in your project?**
* **Answer**: We developed `check_webapp_health.py` in Python. It sends an HTTP GET request to `/health`, measures execution latency with `time.time()`, parses the JSON response for `{"status": "OK"}`, and checks if latency exceeds `-w` (warning) or `-c` (critical) thresholds. It outputs Nagios performance data (`| time=...`) and exits with the standard Nagios exit code.

**Q8: What is Terraform State (`terraform.tfstate`)?**
* **Answer**: The state file is Terraform's single source of truth mapping your declared resource blocks in `.tf` files to real-world resources created in the cloud. It tracks metadata, resource IDs, and dependency graphs.

**Q9: What is the purpose of Ansible Handlers?**
* **Answer**: Handlers are special tasks that only run when notified by another task using the `notify` keyword, and only if that task resulted in a `changed` state. In our project, modifying `app.py` or `app.service.j2` triggers the `Restart webapp` handler once at the end of the play.

**Q10: What are Ansible Group Variables (`group_vars`)?**
* **Answer**: `group_vars` allows separating configuration parameters from task logic. In our project, `webservers.yml` sets application ports and directories, while `monitoring.yml` sets Nagios polling intervals and check commands.

---

### Category C: Project-Specific Understanding (5 Marks)

**Q11: How did you connect Terraform with Ansible in your project?**
* **Answer**: We used Terraform's `local_file` resource along with the `templatefile("inventory.tpl", {...})` function. When Terraform applies, it reads the provisioned IP addresses and automatically generates `ansible/inventory/hosts.ini` with no manual intervention.

**Q12: Explain the directory structure of an Ansible Role.**
* **Answer**: An Ansible role organizes assets into standardized directories:
  - `tasks/main.yml`: The list of tasks to execute.
  - `templates/`: Jinja2 template files (`.j2`) rendered dynamically with variables.
  - `files/`: Static files transferred as-is (like `app.py` and `check_webapp_health.py`).
  - `handlers/main.yml`: Tasks triggered on change.

**Q13: What happens during the self-healing playbook execution?**
* **Answer**: The `self_heal.yml` playbook queries `/health`. If an error is detected, it logs the failure, restarts the `devops-webapp` service daemon, retries `/health` until HTTP 200 is confirmed, and notifies administrators of recovery.

**Q14: Why did you include automated unit tests in your project?**
* **Answer**: In `tests/test_nagios_plugin.py`, we test all 4 Nagios return codes against a mock server, validating normal status (0), warning on latency (1), critical on HTTP 500 (2), and critical on connection refusal (2). This satisfies the rubric's *Testing & Error Handling* requirement.

---

### Category D: Problem Solving & Troubleshooting (5 Marks)

**Q15: If Nagios reports a False Alarm (flap), how do you resolve it?**
* **Answer**: In Nagios configuration, flap detection (`enable_flap_detection=1`) can be enabled, and `max_check_attempts` can be increased from 1 to 3 or 5 to ensure transient blips don't trigger alerts before confirming a hard state.

**Q16: How do you secure sensitive credentials in Ansible and Terraform?**
* **Answer**: In Ansible, we use **Ansible Vault** (`ansible-vault encrypt`) to encrypt sensitive variables. In Terraform, sensitive variables are marked with `sensitive = true`, stored in environment variables (`TF_VAR_...`), or retrieved from secret managers like AWS Secrets Manager or HashiCorp Vault.

**Q17: If a server fails during Ansible playbook execution, how does Ansible handle it?**
* **Answer**: Ansible marks that specific host as `FAILED` and stops executing further tasks on it, but continues running for remaining healthy hosts. The `.retry` file records failed hosts, allowing re-running with `--limit @playbook.retry`.

**Q18: What is your project's unique innovation?**
* **Answer**: Our innovation is two-fold:
  1. A **Custom Python Nagios Plugin** performing deep semantic application health checks and performance telemetry rather than simple ping checks.
  2. An **Automated Self-Healing Loop** using Ansible playbooks to self-remediate outages in real time.
