#!/usr/bin/env python3
"""
check_drift.py - Nagios plugin that detects configuration drift.

How it works:
  1. Runs the Ansible baseline playbook in CHECK mode (--check --diff) against one host.
     Check mode changes nothing; it only reports which rules the host no longer matches.
  2. Every task Ansible says it "would change" is a piece of drift.
  3. Prints a Nagios status line and exits with the Nagios code:
        0 OK        host matches the baseline
        2 CRITICAL  host has drifted (lists what and shows the diff)
        3 UNKNOWN   the check itself could not run (host unreachable, Ansible error)
  4. Saves a JSON report per host, which `drift-report` turns into a fleet overview.

Usage:
  check_drift.py --host node1        Nagios check for one host
  drift-report                       overview of the last result for every host
  drift-report --live                check every host right now, then show the overview
"""
import argparse
import difflib
import json
import os
import subprocess
import sys
import time
from datetime import datetime

OK, WARNING, CRITICAL, UNKNOWN = 0, 1, 2, 3
STATUS_NAME = {OK: "OK", WARNING: "WARNING", CRITICAL: "CRITICAL", UNKNOWN: "UNKNOWN"}

DRIFT_HOME = os.environ.get("DRIFT_HOME", "/var/lib/drift")
ANSIBLE_DIR = os.environ.get("DRIFT_ANSIBLE_DIR", "/opt/drift/ansible")
PLAYBOOK = os.path.join(ANSIBLE_DIR, "baseline.yml")
REPORT_DIR = os.path.join(DRIFT_HOME, "reports")
MAX_DIFF_LINES = 6
TIMEOUT_S = 80


# ---------------------------------------------------------------- running Ansible
def ansible_env():
    env = dict(os.environ)
    env.update({
        "ANSIBLE_CONFIG": os.path.join(ANSIBLE_DIR, "ansible.cfg"),
        "ANSIBLE_STDOUT_CALLBACK": "ansible.posix.json",
        "ANSIBLE_NOCOLOR": "1",
        "ANSIBLE_DEPRECATION_WARNINGS": "False",
        "ANSIBLE_LOCAL_TEMP": os.path.join(DRIFT_HOME, "tmp"),
        "ANSIBLE_SSH_CONTROL_PATH_DIR": os.path.join(DRIFT_HOME, "tmp", "cp-%d" % os.getuid()),
    })
    if os.getuid() != 0:
        # Running as the nagios user: use the workspace as home and Nagios' copy of the key
        env["HOME"] = DRIFT_HOME
        env["ANSIBLE_PRIVATE_KEY_FILE"] = os.path.join(DRIFT_HOME, ".ssh", "id_ed25519")
    return env


def run_baseline_check(limit=None):
    """Runs the baseline in check mode. Returns the parsed JSON from Ansible."""
    cmd = ["ansible-playbook", PLAYBOOK, "--check", "--diff"]
    if limit:
        cmd += ["--limit", limit]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT_S, env=ansible_env())
    try:
        return json.loads(proc.stdout)
    except ValueError:
        err = (proc.stderr or proc.stdout or "no output").strip().splitlines()
        raise RuntimeError("Ansible did not return results: " + (err[-1] if err else "?"))


# ---------------------------------------------------------------- understanding the results
def clean(text):
    # '|' would split the Nagios output into perfdata
    return str(text).replace("|", "/")


def describe_diff(diff):
    """Turns one Ansible diff into short human-readable lines."""
    lines = []
    for d in diff if isinstance(diff, list) else [diff]:
        if not isinstance(d, dict):
            continue
        before, after = d.get("before"), d.get("after")
        if isinstance(before, dict) or isinstance(after, dict):
            before, after = before or {}, after or {}
            for key in sorted(set(before) | set(after)):
                if key == "path" or before.get(key) == after.get(key):
                    continue
                lines.append(f"{key}: is '{before.get(key, '-')}', should be '{after.get(key, '-')}'")
        elif isinstance(before, str) or isinstance(after, str):
            for line in difflib.unified_diff((before or "").splitlines(), (after or "").splitlines(),
                                             "server", "baseline", lineterm="", n=0):
                if line.startswith(("---", "+++", "@@")):
                    continue
                prefix = "  on server: " if line.startswith("-") else "  baseline:  "
                lines.append(prefix + line[1:].strip())
        if d.get("prepared"):
            lines += describe_apt(str(d["prepared"]))
    if len(lines) > MAX_DIFF_LINES:
        lines = lines[:MAX_DIFF_LINES] + [f"  ... {len(lines) - MAX_DIFF_LINES} more line(s)"]
    return [clean(l) for l in lines]


def describe_apt(prepared):
    """Summarises apt's 'prepared' text, e.g. 'installed but should not be: telnet'."""
    out, section = [], None
    for line in prepared.splitlines():
        if "will be REMOVED" in line:
            section = "installed but should not be"
        elif "NEW packages will be installed" in line:
            section = "missing, should be installed"
        elif line.startswith(" ") and section:
            out.append(f"{section}: {' '.join(line.split()).replace('*', '')}")
        else:
            section = None
    return out or ["package state differs"]


def parse_host(result, host):
    """
    Reads ansible.posix.json output for one host.
    Returns (status, summary, report_dict).
    """
    stats = result.get("stats", {}).get(host)
    if stats is None:
        return UNKNOWN, f"{host} is not in the Ansible inventory", {}
    if stats.get("unreachable"):
        return UNKNOWN, f"{host} is unreachable over SSH - cannot verify its configuration", {}

    checked, drifted, failed = 0, [], []          # failed = (rule, error message)
    for play in result.get("plays", []):
        for task in play.get("tasks", []):
            outcome = task.get("hosts", {}).get(host)
            if outcome is None:
                continue
            name = task.get("task", {}).get("name", "unnamed task")
            name = name.split(" : ", 1)[-1]               # drop the "rolename : " prefix
            if outcome.get("skipped") and not outcome.get("results"):
                continue
            checked += 1
            if outcome.get("failed"):
                failed.append((clean(name), clean(outcome.get("msg", "failed"))))
                continue
            if not outcome.get("changed"):
                continue
            details = []
            if outcome.get("results"):                      # a loop: report each item that drifted
                for item in outcome["results"]:
                    if item.get("changed"):
                        label = item.get("_ansible_item_label", item.get("item", ""))
                        if isinstance(label, dict):
                            label = label.get("name", label)
                        details.append(f"item '{label}' differs")
                        details += describe_diff(item.get("diff", []))
            else:
                details = describe_diff(outcome.get("diff", []))
            if not details and "Service" in name:
                details = ["service is not in the required state"]
            drifted.append({"rule": clean(name), "details": details or ["differs from baseline"]})

    report = {"host": host, "checked_at": time.time(), "rules_checked": checked,
              "drifted": drifted, "errors": [f"{n}: {m}" for n, m in failed]}
    if failed and not drifted:
        return UNKNOWN, f"{host}: drift check could not finish - {report['errors'][0]}", report
    if drifted:
        # Errors after drift are usually caused by it (e.g. a file can't be checked because
        # the package that creates it is missing), so the machine counts as drifted.
        for name, _ in failed:
            drifted.append({"rule": name, "details": ["cannot be checked until earlier drift is fixed"]})
        report["errors"] = []
        names = ", ".join(d["rule"] for d in drifted)
        return CRITICAL, f"{host} has drifted - {len(drifted)} of {checked} rules broken: {names}", report
    return OK, f"{host} matches the baseline ({checked} rules checked)", report


# ---------------------------------------------------------------- reports
def save_report(host, status, summary, report):
    os.makedirs(REPORT_DIR, exist_ok=True)
    report = dict(report, host=host, status=STATUS_NAME[status], summary=summary,
                  checked_at=report.get("checked_at", time.time()))
    path = os.path.join(REPORT_DIR, f"{host}.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(report, fh, indent=2)
    os.replace(tmp, path)
    if getattr(os, "getuid", lambda: -1)() == 0:   # keep the file writable for the nagios user
        try:
            import pwd                   # Linux-only module, so imported here
            nagios = pwd.getpwnam("nagios")
            os.chown(path, nagios.pw_uid, nagios.pw_gid)
        except (KeyError, OSError):
            pass


def nagios_output(status, summary, report):
    drifted = len(report.get("drifted", []))
    checked = report.get("rules_checked", 0)
    lines = [f"DRIFT {STATUS_NAME[status]} - {summary} | drifted_rules={drifted};;1;0 rules_checked={checked};;;0"]
    for d in report.get("drifted", []):
        lines.append(f"[DRIFT] {d['rule']}")
        lines += [f"    {l}" for l in d["details"]]
    for e in report.get("errors", []):
        lines.append(f"[ERROR] {clean(e)}")
    return "\n".join(lines)


def ago(ts):
    s = int(time.time() - ts)
    return f"{s}s ago" if s < 120 else f"{s // 60}m ago"


def print_fleet_report():
    files = sorted(f for f in os.listdir(REPORT_DIR) if f.endswith(".json")) if os.path.isdir(REPORT_DIR) else []
    if not files:
        print("No drift checks have run yet. Try: drift-report --live")
        return 1
    reports = []
    for f in files:
        with open(os.path.join(REPORT_DIR, f)) as fh:
            reports.append(json.load(fh))
    print()
    print("  FLEET CONFIGURATION DRIFT REPORT   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  " + "-" * 78)
    print(f"  {'MACHINE':<9}{'STATUS':<11}{'CHECKED':<10}WHAT IS DIFFERENT FROM THE BASELINE")
    print("  " + "-" * 78)
    worst = OK
    for r in reports:
        status = r.get("status", "UNKNOWN")
        code = {"OK": OK, "CRITICAL": CRITICAL}.get(status, UNKNOWN)
        worst = max(worst, code)
        label = {"OK": "in sync", "CRITICAL": "DRIFTED"}.get(status, "UNKNOWN")
        drifted = r.get("drifted", [])
        first = drifted[0]["rule"] if drifted else ("-" if status == "OK" else r.get("summary", ""))
        print(f"  {r['host']:<9}{label:<11}{ago(r.get('checked_at', 0)):<10}{first}")
        for d in drifted[1:]:
            print(f"  {'':<30}{d['rule']}")
    print("  " + "-" * 78)
    in_sync = sum(1 for r in reports if r.get("status") == "OK")
    print(f"  {in_sync} of {len(reports)} machines match the baseline")
    print()
    return worst


# ---------------------------------------------------------------- main
def check_host(host):
    try:
        result = run_baseline_check(host)
        status, summary, report = parse_host(result, host)
    except subprocess.TimeoutExpired:
        status, summary, report = UNKNOWN, f"drift check on {host} timed out after {TIMEOUT_S}s", {}
    except (RuntimeError, OSError) as exc:
        status, summary, report = UNKNOWN, clean(exc), {}
    save_report(host, status, summary, report)
    return status, summary, report


def main(argv=None):
    report_mode = os.path.basename(sys.argv[0]).startswith("drift-report")
    ap = argparse.ArgumentParser(description="Configuration drift check (Nagios plugin)")
    ap.add_argument("--host", help="inventory name of the host to check")
    ap.add_argument("--report", action="store_true", help="show the fleet overview")
    ap.add_argument("--live", action="store_true", help="with --report: check every host first")
    args = ap.parse_args(argv)

    if report_mode or args.report:
        if args.live:
            result = run_baseline_check()
            for host in result.get("stats", {}):
                status, summary, report = parse_host(result, host)
                save_report(host, status, summary, report)
        return print_fleet_report()

    if not args.host:
        print("DRIFT UNKNOWN - no --host given")
        return UNKNOWN
    status, summary, report = check_host(args.host)
    print(nagios_output(status, summary, report))
    return status


if __name__ == "__main__":
    sys.exit(main())
