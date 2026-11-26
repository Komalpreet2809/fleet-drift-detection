# The control node: runs Ansible (configuration management) and Nagios (monitoring).
# Ansible comes preinstalled; Nagios itself is installed by the Ansible "monitoring" role.
FROM ubuntu:24.04

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ansible openssh-client python3 sudo nano less curl iputils-ping ca-certificates tzdata

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80
ENTRYPOINT ["/entrypoint.sh"]
