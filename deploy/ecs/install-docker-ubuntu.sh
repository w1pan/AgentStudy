#!/usr/bin/env bash
set -euo pipefail
# For a fresh Ubuntu ECS. Existing Docker installations should be inspected first.
case "${1:-aliyun}" in
  aliyun) docker_repo='https://mirrors.aliyun.com/docker-ce/linux/ubuntu' ;;
  official) docker_repo='https://download.docker.com/linux/ubuntu' ;;
  *) echo 'Usage: bash install-docker-ubuntu.sh [aliyun|official]' >&2; exit 2 ;;
esac
sudo apt-get update
sudo apt-get install -y ca-certificates curl openssl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl --connect-timeout 15 --max-time 120 --retry 3 -fsSL "$docker_repo/gpg" -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: $docker_repo
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
