"""
Integration tests against the running lab (Terraform + Ansible + Nagios).
Skipped automatically when the lab is not running.  Start it with:  .\\run.ps1 up

These tests really change files on the machines and check that the system
detects and fixes the drift.
"""
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from base64 import b64encode

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = "/usr/local/lib/nagios/plugins/check_drift.py"
NAGIOS = "http://localhost:8090"
AUTH = "Basic " + b64encode(b"nagiosadmin:drift123").decode()


def sh(*args, timeout=180):
    return subprocess.run(list(args), capture_output=True, text=True, timeout=timeout)


def lab_running():
    if not shutil.which("docker"):
        return False
    out = sh("docker", "ps", "--format", "{{.Names}}", timeout=20).stdout.split()
    return {"control", "node1", "node2", "node3"} <= set(out)


pytestmark = pytest.mark.skipif(not lab_running(), reason="lab is not running (.\\run.ps1 up)")


def on_control(*cmd, user=None):
    base = ["docker", "exec"] + (["-u", user] if user else []) + ["control"]
    return sh(*(base + list(cmd)))


def on_node(node, script):
    return sh("docker", "exec", node, "bash", "-c", script)


def drift_check(node):
    return on_control(PLUGIN, "--host", node, user="nagios")


def restore(node=None):
    cmd = ["ansible-playbook", "/opt/drift/ansible/baseline.yml"] + (["--limit", node] if node else [])
    r = on_control(*cmd)
    assert r.returncode == 0, r.stdout[-2000:]
    return r


def set_auto(enabled):
    if enabled:
        on_control("bash", "-c", "echo enabled > /var/lib/drift/auto_remediate && chown nagios:nagios /var/lib/drift/auto_remediate")
    else:
        on_control("rm", "-f", "/var/lib/drift/auto_remediate")


def nagios_service(host, service):
    url = (f"{NAGIOS}/cgi-bin/nagios4/statusjson.cgi?query=service&hostname={host}"
           f"&servicedescription={service.replace(' ', '+')}")
    req = urllib.request.Request(url, headers={"Authorization": AUTH})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)["data"]["service"]


@pytest.fixture(autouse=True)
def clean_fleet():
    """Every test starts and ends with the whole fleet on the baseline and auto-fix off."""
    set_auto(False)
    restore()
    yield
    restore()
    set_auto(True)


# ---------------------------------------------------------------- detection
@pytest.mark.parametrize("node", ["node1", "node2", "node3"])
def test_fresh_fleet_has_no_drift(node):
    r = drift_check(node)
    assert r.returncode == 0, r.stdout
    assert r.stdout.startswith("DRIFT OK")


@pytest.mark.parametrize("change, expected_rule", [
    ("sed -i 's/max_connections = 100/max_connections = 5/' /etc/fleet/app.conf", "App config: /etc/fleet/app.conf"),
    ("service nginx stop", "Service: nginx running"),
    ("echo defaced > /var/www/html/index.html", "Website: /var/www/html/index.html"),
    ("chmod 777 /etc/fleet/app.conf", "Permissions:"),
    ("echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config.d/10-baseline.conf", "Security: SSH hardening"),
    ("userdel deploy", "User: service account exists"),
])
def test_each_kind_of_manual_change_is_detected(change, expected_rule):
    on_node("node2", change)
    r = drift_check("node2")
    assert r.returncode == 2, r.stdout
    assert expected_rule in r.stdout
    # the other machines are not affected
    assert drift_check("node1").returncode == 0


def test_only_the_changed_machine_is_reported():
    on_node("node3", "sed -i 's/log_level = info/log_level = debug/' /etc/fleet/app.conf")
    assert drift_check("node1").returncode == 0
    assert drift_check("node2").returncode == 0
    r = drift_check("node3")
    assert r.returncode == 2
    assert "log_level = debug" in r.stdout


def test_check_mode_does_not_change_anything():
    on_node("node1", "sed -i 's/max_connections = 100/max_connections = 7/' /etc/fleet/app.conf")
    drift_check("node1")
    drift_check("node1")
    assert "max_connections = 7" in on_node("node1", "cat /etc/fleet/app.conf").stdout


# ---------------------------------------------------------------- remediation
def test_manual_fix_restores_baseline():
    on_node("node1", "service nginx stop; chmod 777 /etc/fleet/app.conf")
    assert drift_check("node1").returncode == 2
    restore("node1")
    assert drift_check("node1").returncode == 0


def test_baseline_is_idempotent():
    r = restore()
    assert "changed=0" in r.stdout and "changed=1" not in r.stdout


def test_remediation_skipped_when_auto_is_off():
    on_node("node2", "service nginx stop")
    drift_check("node2")                       # writes the CRITICAL report
    on_control("/usr/local/lib/nagios/plugins/remediate_drift.sh", "CRITICAL", "HARD", "node2", user="nagios")
    log = on_control("tail", "-n", "1", "/var/lib/drift/remediation.log").stdout
    assert "Auto-remediation is OFF" in log
    assert drift_check("node2").returncode == 2


def test_event_handler_fixes_drift_when_auto_is_on():
    set_auto(True)
    on_node("node2", "service nginx stop")
    drift_check("node2")
    on_control("/usr/local/lib/nagios/plugins/remediate_drift.sh", "CRITICAL", "HARD", "node2", user="nagios")
    log = on_control("tail", "-n", "3", "/var/lib/drift/remediation.log").stdout
    assert "fixed: Service: nginx running" in log
    assert "Baseline restored successfully" in log
    assert drift_check("node2").returncode == 0


def test_event_handler_ignores_soft_states():
    set_auto(True)
    on_node("node2", "service nginx stop")
    drift_check("node2")
    on_control("/usr/local/lib/nagios/plugins/remediate_drift.sh", "CRITICAL", "SOFT", "node2", user="nagios")
    assert drift_check("node2").returncode == 2, "a SOFT (unconfirmed) state must not trigger a fix"


@pytest.mark.slow
def test_nagios_detects_and_heals_by_itself():
    """Full loop with nobody touching anything: change -> Nagios CRITICAL -> Ansible fix -> OK."""
    set_auto(True)
    on_node("node1", "sed -i 's/debug_mode = off/debug_mode = on/' /etc/fleet/app.conf")
    saw_critical = False
    deadline = time.time() + 240
    while time.time() < deadline:
        svc = nagios_service("node1", "Configuration Drift")
        if svc["status"] == 16:
            saw_critical = True
        elif svc["status"] == 2 and saw_critical:
            break
        time.sleep(5)
    assert saw_critical, "Nagios never reported the drift"
    assert svc["status"] == 2, "Nagios did not return to OK after auto-remediation"
    assert "debug_mode = off" in on_node("node1", "cat /etc/fleet/app.conf").stdout


# ---------------------------------------------------------------- monitoring and infrastructure
def test_nagios_requires_login():
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(f"{NAGIOS}/nagios4/", timeout=10)
    assert err.value.code == 401
    req = urllib.request.Request(f"{NAGIOS}/nagios4/", headers={"Authorization": AUTH})
    assert urllib.request.urlopen(req, timeout=10).status == 200


@pytest.mark.parametrize("port, node", [(8091, "node1"), (8092, "node2"), (8093, "node3")])
def test_node_websites_serve_baseline_page(port, node):
    html = urllib.request.urlopen(f"http://localhost:{port}", timeout=10).read().decode()
    assert f"{node} - baseline configuration" in html


def test_no_infrastructure_drift():
    if not shutil.which("terraform"):
        pytest.skip("terraform not installed")
    r = sh("terraform", f"-chdir={os.path.join(ROOT, 'terraform')}", "plan", "-detailed-exitcode",
           "-input=false", "-no-color", "-lock=false", timeout=300)
    assert r.returncode == 0, "terraform plan found differences:\n" + r.stdout[-3000:]
