#!/usr/bin/env bash
# Install official Docker Engine + Compose on an otherwise clean Ubuntu host.
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo 'Run with sudo bash install-docker-ubuntu.sh' >&2
  exit 1
fi
if command -v docker >/dev/null 2>&1; then
  docker --version
  docker compose version
  echo 'Docker is already installed; left existing installation unchanged.'
  exit 0
fi
. /etc/os-release
if [[ ${ID} != ubuntu || ${VERSION_ID} != 24.04 ]]; then
  echo 'This helper is for Ubuntu 24.04 only. Follow Docker documentation for this OS.' >&2
  exit 1
fi
for task_package in docker.io docker-compose docker-compose-v2 docker-doc podman-docker containerd runc; do
  if [[ "$(dpkg-query -W -f='${Status}' "${task_package}" 2>/dev/null || true)" == 'install ok installed' ]]; then
    echo "Existing package ${task_package} needs review; no packages were removed." >&2
    exit 1
  fi
done
apt-get update
apt-get install -y ca-certificates curl python3
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker --version
docker compose version
