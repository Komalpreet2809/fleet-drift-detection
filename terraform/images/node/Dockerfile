# A minimal Ubuntu "server" for the managed fleet.
# It only has SSH and Python, like a freshly created cloud VM.
# Everything else (nginx, config files, users...) is installed by Ansible.
FROM ubuntu:24.04

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      openssh-server sudo python3 python3-apt nano vim-tiny less iputils-ping ca-certificates \
 && useradd -m -s /bin/bash ansible \
 && echo 'ansible ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ansible \
 && chmod 440 /etc/sudoers.d/ansible \
 && mkdir -p /run/sshd

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22 80
ENTRYPOINT ["/entrypoint.sh"]
