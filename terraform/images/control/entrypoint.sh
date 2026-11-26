#!/bin/sh
# Boot script for the control node: install the SSH key Terraform generated,
# restart Nagios/Apache if Ansible already installed them, then stay running.
set -e

mkdir -p /root/.ssh
cp /opt/drift/keys/id_ed25519 /root/.ssh/id_ed25519
chmod 700 /root/.ssh
chmod 600 /root/.ssh/id_ed25519

[ -x /etc/init.d/apache2 ] && service apache2 start >/dev/null 2>&1 || true
[ -x /etc/init.d/nagios4 ] && service nagios4 start >/dev/null 2>&1 || true

exec sleep infinity
