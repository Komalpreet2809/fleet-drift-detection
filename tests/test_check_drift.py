"""
Unit tests for the Nagios drift plugin (ansible/roles/monitoring/files/check_drift.py).

The fixtures in tests/fixtures/ are REAL outputs captured from the lab with
`ansible-playbook baseline.yml --check --diff` (ansible.posix.json callback):
  clean.json        node2 matching the baseline
  drifted.json      node2 after manual changes (config edited, permissions, nginx stopped,
                    telnet installed, service account deleted)
  unreachable.json  node3 while its machine was stopped
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "ansible", "roles", "monitoring", "files"))

import check_drift as cd  # noqa: E402

FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def fixture(name):
    with open(os.path.join(FIXTURES, name + ".json"), encoding="utf-8") as fh:
        return json.load(fh)


def task(name, outcome):
    return {"task": {"name": name}, "hosts": {"node1": outcome}}


def result(*tasks, unreachable=0):
    return {"plays": [{"tasks": list(tasks)}],
            "stats": {"node1": {"unreachable": unreachable, "failures": 0}}}


# ---------------------------------------------------------------- real lab output
def test_clean_host_is_ok():
    status, summary, report = cd.parse_host(fixture("clean"), "node2")
    assert status == cd.OK
    assert "matches the baseline" in summary
    assert report["drifted"] == []
    assert report["rules_checked"] == 11


def test_drifted_host_is_critical():
    status, summary, report = cd.parse_host(fixture("drifted"), "node2")
    assert status == cd.CRITICAL
    rules = [d["rule"] for d in report["drifted"]]
    assert "App config: /etc/fleet/app.conf" in rules
    assert "Service: nginx running" in rules
    assert "User: service account exists" in rules
    assert any(r.startswith("Packages: insecure tools") for r in rules)
    assert any(r.startswith("Permissions:") for r in rules)


def test_drift_details_show_old_and_new_values():
    _, _, report = cd.parse_host(fixture("drifted"), "node2")
    by_rule = {d["rule"]: d["details"] for d in report["drifted"]}
    config = by_rule["App config: /etc/fleet/app.conf"]
    assert any("on server" in l and "log_level = debug" in l for l in config)
    assert any("baseline" in l and "log_level = info" in l for l in config)
    perms = next(v for k, v in by_rule.items() if k.startswith("Permissions:"))
    assert any("is '0666', should be '0644'" in l for l in perms)
    packages = next(v for k, v in by_rule.items() if k.startswith("Packages: insecure"))
    assert any("telnet" in l and "should not be" in l for l in packages)


def test_role_prefix_is_removed():
    _, _, report = cd.parse_host(fixture("drifted"), "node2")
    assert not any(" : " in d["rule"] for d in report["drifted"])


def test_unreachable_host_is_unknown_not_ok():
    status, summary, _ = cd.parse_host(fixture("unreachable"), "node3")
    assert status == cd.UNKNOWN
    assert "unreachable" in summary


def test_host_missing_from_inventory():
    status, summary, _ = cd.parse_host(fixture("clean"), "node9")
    assert status == cd.UNKNOWN
    assert "not in the Ansible inventory" in summary


# ---------------------------------------------------------------- Nagios output format
def test_nagios_output_has_status_line_and_perfdata():
    status, summary, report = cd.parse_host(fixture("drifted"), "node2")
    out = cd.nagios_output(status, summary, report)
    first = out.splitlines()[0]
    assert first.startswith("DRIFT CRITICAL - ")
    assert first.count("|") == 1, "exactly one '|' separating text from perfdata"
    assert "drifted_rules=6" in first
    assert "[DRIFT] Service: nginx running" in out


def test_ok_output():
    status, summary, report = cd.parse_host(fixture("clean"), "node2")
    out = cd.nagios_output(status, summary, report)
    assert out.startswith("DRIFT OK - node2 matches the baseline")
    assert "drifted_rules=0" in out


def test_pipe_characters_cannot_break_perfdata():
    r = result(task("Config: a|b", {"changed": True, "diff": [{"before": "x|y\n", "after": "z\n"}]}))
    status, summary, report = cd.parse_host(r, "node1")
    out = cd.nagios_output(status, summary, report)
    assert out.splitlines()[0].count("|") == 1
    assert all("|" not in line for line in out.splitlines()[1:])


# ---------------------------------------------------------------- rule handling
def test_failed_task_makes_check_unknown():
    r = result(task("App config", {"failed": True, "msg": "permission denied"}))
    status, summary, _ = cd.parse_host(r, "node1")
    assert status == cd.UNKNOWN
    assert "permission denied" in summary


def test_skipped_tasks_are_not_counted():
    r = result(task("A", {"changed": False}), task("B", {"skipped": True}))
    _, _, report = cd.parse_host(r, "node1")
    assert report["rules_checked"] == 1


def test_loop_reports_only_changed_items():
    r = result(task("Permissions", {"changed": True, "results": [
        {"changed": False, "item": "/etc/a"},
        {"changed": True, "item": "/etc/b", "diff": {"before": {"mode": "0777"}, "after": {"mode": "0644"}}},
    ]}))
    _, _, report = cd.parse_host(r, "node1")
    details = report["drifted"][0]["details"]
    assert "item '/etc/b' differs" in details
    assert not any("/etc/a" in d for d in details)


def test_service_without_diff_gets_explanation():
    r = result(task("Service: nginx running", {"changed": True}))
    _, _, report = cd.parse_host(r, "node1")
    assert report["drifted"][0]["details"] == ["service is not in the required state"]


# ---------------------------------------------------------------- diff descriptions
def test_text_diff_shows_only_changed_lines():
    lines = cd.describe_diff([{"before": "a = 1\nb = 2\n", "after": "a = 1\nb = 3\n"}])
    assert lines == ["  on server: b = 2", "  baseline:  b = 3"]


def test_attribute_diff():
    lines = cd.describe_diff({"before": {"path": "/x", "owner": "bob"}, "after": {"path": "/x", "owner": "root"}})
    assert lines == ["owner: is 'bob', should be 'root'"]


def test_long_diffs_are_shortened():
    before = "\n".join(f"line {i}" for i in range(50))
    lines = cd.describe_diff([{"before": before, "after": ""}])
    assert len(lines) == cd.MAX_DIFF_LINES + 1
    assert "more line(s)" in lines[-1]


@pytest.mark.parametrize("text, expected", [
    ("The following packages will be REMOVED:\n  telnet*\n0 upgraded", ["installed but should not be: telnet"]),
    ("The following NEW packages will be installed:\n  nginx curl\n0 upgraded", ["missing, should be installed: nginx curl"]),
    ("something unexpected", ["package state differs"]),
])
def test_apt_summary(text, expected):
    assert cd.describe_apt(text) == expected


# ---------------------------------------------------------------- plugin entry point
def test_main_exit_codes(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cd, "REPORT_DIR", str(tmp_path))
    monkeypatch.setattr(cd, "run_baseline_check", lambda limit=None: fixture("drifted"))
    assert cd.main(["--host", "node2"]) == cd.CRITICAL
    assert "DRIFT CRITICAL" in capsys.readouterr().out
    saved = json.loads((tmp_path / "node2.json").read_text())
    assert saved["status"] == "CRITICAL"

    monkeypatch.setattr(cd, "run_baseline_check", lambda limit=None: fixture("clean"))
    assert cd.main(["--host", "node2"]) == cd.OK


def test_ansible_crash_is_unknown(monkeypatch, tmp_path, capsys):
    def boom(limit=None):
        raise RuntimeError("Ansible did not return results: boom")
    monkeypatch.setattr(cd, "REPORT_DIR", str(tmp_path))
    monkeypatch.setattr(cd, "run_baseline_check", boom)
    assert cd.main(["--host", "node1"]) == cd.UNKNOWN
    assert "DRIFT UNKNOWN" in capsys.readouterr().out


def test_missing_host_argument(capsys):
    assert cd.main([]) == cd.UNKNOWN


def test_fleet_report(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cd, "REPORT_DIR", str(tmp_path))
    for name, host in [("clean", "node1"), ("drifted", "node2")]:
        data = fixture(name)
        data["stats"] = {host: list(data["stats"].values())[0]}
        for play in data["plays"]:
            for t in play["tasks"]:
                t["hosts"] = {host: list(t["hosts"].values())[0]} if t["hosts"] else {}
        cd.save_report(host, *cd.parse_host(data, host))
    code = cd.main(["--report"])
    out = capsys.readouterr().out
    assert code == cd.CRITICAL
    assert "node1    in sync" in out
    assert "node2    DRIFTED" in out
    assert "1 of 2 machines match the baseline" in out


def test_blank_machine_counts_as_drifted_not_unknown():
    """A brand-new machine: nginx missing, so later rules fail - it must still be CRITICAL (and get fixed)."""
    r = result(task("Packages: nginx installed", {"changed": True}),
               task("Service: nginx running", {"failed": True, "msg": "Could not find the requested service nginx"}))
    status, _, report = cd.parse_host(r, "node1")
    assert status == cd.CRITICAL
    assert [d["rule"] for d in report["drifted"]] == ["Packages: nginx installed", "Service: nginx running"]
