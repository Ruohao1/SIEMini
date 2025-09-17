#!/bin/bash

set -Eeuo pipefail
IFS=$'\n\t'

log() { echo -e "\033[1;34m[*]\033[0m $*"; }

sudo apt-get update
sudo apt-get -y -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold" upgrade

sudo apt-get install -y \
  ca-certificates curl gnupg lsb-release

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com/ | sh
fi
if ! id -nG "$USER" | grep -qw docker; then
  sudo usermod -aG docker "$USER"
  newgrp docker
fi

docker compose up --build -d
