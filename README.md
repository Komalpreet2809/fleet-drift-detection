# Fleet Configuration Drift Detection
### INT333 – DevOps Advance Configuration Management · Terraform + Ansible + Nagios

A small system that keeps several Linux machines configured **identically** and catches
anyone who changes a machine **by hand**.

- **Terraform** creates the machines (a private network, 3 fleet machines, 1 control machine, SSH keys).
- **Ansible** defines the one correct configuration (the *baseline*) and applies it to every machine.
- **Nagios** checks every machine against the baseline once a minute. When a machine differs,
  it turns red and shows exactly what changed. It can then run Ansible to put it back automatically.

```
                ┌──────────────────────── Terraform creates everything below ───────────────────────┐
                │                                                                                    │
   You / an     │   ┌──────────────── control ─────────────────┐        ┌──────── node1 ────────┐    │
   admin edits  │   │  Nagios  ── every minute runs ──▶        │  SSH   │ nginx, app.conf,      │    │
   a file by ───┼──▶│  check_drift.py                          │──────▶ │ users, packages, ...  │    │
   hand         │   │    └─ ansible-playbook --check --diff    │        └───────────────────────┘    │
                │   │  drift found? → event handler            │        ┌──────── node2 ────────┐    │
                │   │    └─ ansible-playbook baseline.yml      │──────▶ │        same           │    │
                │   │       (puts the machine back)            │        └───────────────────────┘    │
                │   │  Web UI :8090                            │        ┌──────── node3 ────────┐    │
                │   └──────────────────────────────────────────┘──────▶ │        same           │    │
                │                                                       └───────────────────────┘    │
                └────────────────────────────────────────────────────────────────────────────────────┘
```

The "machines" are Docker containers that behave like small Ubuntu servers (SSH, packages,
services), so the whole lab runs free on a laptop. Terraform, Ansible and Nagios treat them
exactly like real servers.

---

## What counts as drift

The baseline lives in [`ansible/group_vars/fleet.yml`](ansible/group_vars/fleet.yml) and
[`ansible/roles/baseline/tasks/main.yml`](ansible/roles/baseline/tasks/main.yml). Each task is one rule:

| Rule | Example of drift it catches |
|---|---|
| Packages: nginx and curl installed | someone uninstalls nginx |
| Packages: insecure tools not installed | someone installs `telnet` |
| User: service account exists | the `deploy` user is deleted |
| App config: `/etc/fleet/app.conf` | `max_connections` changed from 100 to 9999 |
| Web server config | nginx config edited |
| Website: `index.html` | page defaced |
| Security: SSH hardening | `PermitRootLogin yes` added |
| Permissions: config files | `chmod 777` on a config file |
| Login banner: `/etc/motd` | banner edited |
| Service: nginx running | nginx stopped |

## How detection works

[`check_drift.py`](ansible/roles/monitoring/files/check_drift.py) is a custom Nagios plugin. It runs

```
ansible-playbook baseline.yml --check --diff --limit <machine>
```

`--check` makes Ansible **report what it would change without changing anything**. Every rule
Ansible would change is drift. The plugin turns that into a Nagios result:

```
DRIFT CRITICAL - node3 has drifted - 2 of 11 rules broken: App config: /etc/fleet/app.conf, Service: nginx running
[DRIFT] App config: /etc/fleet/app.conf
      on server: max_connections = 9999
      baseline:  max_connections = 100
[DRIFT] Service: nginx running
    service is not in the required state
```

| Exit code | Meaning |
|---|---|
| 0 OK | machine matches the baseline |
| 2 CRITICAL | machine has drifted (what + diff shown) |
| 3 UNKNOWN | the check could not run (machine unreachable, Ansible error) – never reported as OK |

When drift is **confirmed** (Nagios HARD CRITICAL state), the event handler
[`remediate_drift.sh`](ansible/roles/monitoring/files/remediate_drift.sh) runs the baseline on
that one machine (if auto-remediation is on), logs what it fixed, and asks Nagios to re-check.

**Infrastructure drift** (a machine deleted or stopped, a port changed) is caught by
`terraform plan -detailed-exitcode` (`.\run.ps1 infra`).

---

## Running it

**Requirements:** Docker Desktop (running), Terraform ≥ 1.5, Python 3 (for the tests), PowerShell.

```powershell
.\run.ps1 up          # Terraform creates the machines, Ansible configures them (~3-5 min first time)
.\run.ps1 open        # opens Nagios and the three machine websites
```

| Link | What |
|---|---|
| http://localhost:8090/nagios4 | Nagios (user `nagiosadmin`, password `drift123`) → *Services* |
| http://localhost:8091 / 8092 / 8093 | websites of node1 / node2 / node3 |

### All commands

| Command | What it does |
|---|---|
| `.\run.ps1 up` | create + configure everything |
| `.\run.ps1 status` | check every machine now and print the fleet report |
| `.\run.ps1 break node2 config` | make a manual change (drift). Also: `service`, `website`, `permissions`, `ssh`, `package`, `all` |
| `.\run.ps1 shell node2` | open a terminal on node2 to change things yourself |
| `.\run.ps1 fix node2` | run Ansible to restore the baseline (omit the name for all machines) |
| `.\run.ps1 auto on` / `off` | Nagios fixes drift automatically / only alerts |
| `.\run.ps1 log` | what auto-remediation has done |
| `.\run.ps1 infra` | infrastructure drift check with `terraform plan` |
| `.\run.ps1 test` | unit tests + `terraform validate` + Ansible syntax check |
| `.\run.ps1 down` | delete everything |

### Live demo (about 3 minutes)

1. `.\run.ps1 status` → all 3 machines **in sync**. Show Nagios: everything green.
2. `.\run.ps1 auto off`
3. `.\run.ps1 break node2 all` (or `.\run.ps1 shell node2` and edit `/etc/fleet/app.conf` with `nano`).
4. Within ~1 minute Nagios turns **node2 / Configuration Drift red**. Click it to show exactly what changed.
   Open http://localhost:8092 to show the defaced page.
5. `.\run.ps1 status` → node2 **DRIFTED**, node1 and node3 **in sync**.
6. `.\run.ps1 fix node2` → Ansible restores it → Nagios turns green.
7. `.\run.ps1 auto on`, then `.\run.ps1 break node1 config` – and don't touch anything:
   Nagios detects it and fixes it by itself. `.\run.ps1 log` shows what was fixed.

---

## Tests

```powershell
python -m pytest tests -v              # all tests (lab tests are skipped if the lab is not running)
python -m pytest tests -v -m "not slow"  # skip the 2-minute "Nagios heals by itself" test
```

- [`tests/test_check_drift.py`](tests/test_check_drift.py) – unit tests for the plugin, using
  **real Ansible output captured from the lab** ([`tests/fixtures/`](tests/fixtures)).
- [`tests/test_lab.py`](tests/test_lab.py) – integration tests on the running lab: every kind of
  manual change is detected, only the changed machine is reported, check mode changes nothing,
  manual and automatic fixes work, SOFT states are ignored, Nagios needs a login,
  and `terraform plan` shows no infrastructure drift.

## Repository layout

```
terraform/                  Infrastructure as Code
  main.tf                   network, machines, SSH key, generated inventory
  variables.tf, outputs.tf
  images/node, images/control   what a "fresh server" looks like (SSH + Python only)
  inventory.tftpl           Ansible inventory template
ansible/
  baseline.yml              apply / check the baseline
  site.yml                  full setup: baseline + monitoring
  group_vars/fleet.yml      THE BASELINE (desired configuration)
  roles/baseline/           rules every fleet machine must follow
  roles/monitoring/         installs Nagios, the drift check and the auto-fix handler
    files/check_drift.py    custom Nagios plugin (+ drift-report command)
    files/remediate_drift.sh  Nagios event handler
    templates/fleet.cfg.j2  Nagios hosts/services generated from the inventory
tests/                      unit + integration tests
run.ps1                     one script to run the whole lab and the demo
PROJECT_REPORT.pdf / .docx  project report (LPU INT333 format)
DEMO_CHEATSHEET.pdf         live demo steps
```
