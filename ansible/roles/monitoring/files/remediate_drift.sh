#!/bin/bash
# Nagios event handler for the "Configuration Drift" service.
# When drift is confirmed (CRITICAL, HARD state) and auto-remediation is switched on,
# it runs the Ansible baseline against that one host to put everything back.
#
# Arguments (from Nagios): $SERVICESTATE$ $SERVICESTATETYPE$ $HOSTNAME$

STATE="$1"
STATE_TYPE="$2"
HOST="$3"

DRIFT_HOME=/var/lib/drift
ANSIBLE_DIR=/opt/drift/ansible
LOG="$DRIFT_HOME/remediation.log"
NAGIOS_CMD=/var/lib/nagios4/rw/nagios.cmd

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [$HOST] $*" >> "$LOG"; }

# Only act on confirmed drift
[ "$STATE" = "CRITICAL" ] && [ "$STATE_TYPE" = "HARD" ] || exit 0

# Safety: only fix when the drift check really reported drift (not a crashed/timed-out check)
REPORT="$DRIFT_HOME/reports/$HOST.json"
if ! grep -q '"status": "CRITICAL"' "$REPORT" 2>/dev/null; then
    log "CRITICAL state but the drift report does not confirm drift - not touching the machine."
    exit 0
fi

if [ ! -f "$DRIFT_HOME/auto_remediate" ]; then
    log "Drift confirmed. Auto-remediation is OFF - waiting for an operator to fix it."
    exit 0
fi

log "Drift confirmed. Running Ansible to restore the baseline..."

export HOME="$DRIFT_HOME"
export ANSIBLE_CONFIG="$ANSIBLE_DIR/ansible.cfg"
export ANSIBLE_PRIVATE_KEY_FILE="$DRIFT_HOME/.ssh/id_ed25519"
export ANSIBLE_LOCAL_TEMP="$DRIFT_HOME/tmp"
export ANSIBLE_SSH_CONTROL_PATH_DIR="$DRIFT_HOME/tmp/cp-$(id -u)"
export ANSIBLE_NOCOLOR=1

OUTPUT=$(ansible-playbook "$ANSIBLE_DIR/baseline.yml" --limit "$HOST" 2>&1)
RC=$?

# Log which rules Ansible had to fix
echo "$OUTPUT" | awk '/^TASK \[/ { task = $0; sub(/^TASK \[([a-z_]+ : )?/, "", task); sub(/\] \**$/, "", task) }
                      /^changed:/ { if (task != last) print "    fixed: " task; last = task }' >> "$LOG"
if [ $RC -eq 0 ]; then
    log "Baseline restored successfully."
else
    log "Remediation FAILED (exit code $RC):"
    echo "$OUTPUT" | tail -5 | sed "s/^/    /" >> "$LOG"
fi

# Ask Nagios to re-check straight away so the dashboard turns green quickly
NOW=$(date +%s)
printf "[%s] SCHEDULE_FORCED_SVC_CHECK;%s;Configuration Drift;%s\n" "$NOW" "$HOST" "$NOW" > "$NAGIOS_CMD" 2>/dev/null
printf "[%s] SCHEDULE_FORCED_SVC_CHECK;%s;Website;%s\n" "$NOW" "$HOST" "$NOW" > "$NAGIOS_CMD" 2>/dev/null
exit 0
