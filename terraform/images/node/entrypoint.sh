#!/bin/sh
# Boot script for a fleet node: install the Ansible SSH key, then run sshd.
set -e

mkdir -p /home/ansible/.ssh
printf '%s\n' "$SSH_PUBLIC_KEY" > /home/ansible/.ssh/authorized_keys
chown -R ansible:ansible /home/ansible/.ssh
chmod 700 /home/ansible/.ssh
chmod 600 /home/ansible/.ssh/authorized_keys

ssh-keygen -A >/dev/null

# Services that Ansible installed come back after a reboot (container restart).
[ -x /etc/init.d/nginx ] && service nginx start >/dev/null 2>&1 || true

exec /usr/sbin/sshd -D -e
