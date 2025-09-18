#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

log() { echo -e "\033[1;34m[*]\033[0m $*"; }
err() { echo -e "\033[1;31m[!]\033[0m $*" >&2; }

# --- Load args ---
SIEM_USER="${1:-}"
if [[ -z "${SIEM_USER}" ]]; then
  err "Missing SIEM user. Usage: $0 <SIEM_USER>"
  exit 1
fi

# --- Load .env and auto-export ---
if [[ -f "../.env" ]]; then
  set -a
  source ../.env
  set +a
else
  err "Missing ../.env file (expected next to this script)."
  exit 1
fi

: "${SIEM_HOST:?SIEM_HOST is required in .env (e.g., 192.168.50.20)}"
OS_CODENAME="${OS_CODENAME:-$(. /etc/os-release && echo "${VERSION_CODENAME:-jammy}")}"

KEYRING="/etc/apt/keyrings/syslog-ng-ose.gpg"
LIST="/etc/apt/sources.list.d/syslog-ng-ose.list"

log "Preparing syslog-ng OSE APT repo for ${OS_CODENAME}…"
if [[ ! -f "$KEYRING" ]]; then
  sudo mkdir -p /etc/apt/keyrings
  curl -fsSL https://ose-repo.syslog-ng.com/apt/syslog-ng-ose-pub.asc | sudo gpg --dearmor -o "$KEYRING"
fi

if [[ ! -f "$LIST" ]] || ! grep -q "$OS_CODENAME" "$LIST"; then
  echo "deb [signed-by=$KEYRING] https://ose-repo.syslog-ng.com/apt/ stable ubuntu-${OS_CODENAME}" |
    sudo tee "$LIST" >/dev/null
fi

log "Updating and upgrading packages…"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get -y \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold" upgrade

log "Installing dependencies and syslog-ng…"
sudo apt-get install -y \
  ca-certificates curl gnupg lsb-release \
  syslog-ng syslog-ng-core syslog-ng-scl

sudo tee /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg >/dev/null <<'EOF'
network: {config: disabled}
EOF
export HOST_IP="$WEB_HOST"
envsubst <../netplan.template.yml | sudo tee /etc/netplan/01-network-manager-all.yaml >/dev/null
sudo netplan apply

if ! command -v docker >/dev/null 2>&1; then
  log "Installing Docker (engine + compose plugin)…"
  curl -fsSL https://get.docker.com/ | sh
fi

if ! id -nG "$USER" | grep -qw docker; then
  log "Adding $USER to docker group…"
  sudo usermod -aG docker "$USER"
  newgrp docker <<'EOF'
true
EOF
fi

REMOTE="${SIEM_USER}@${SIEM_HOST}"
LOCAL_CA="/etc/syslog-ng/ca/ca.crt"
REMOTE_CA="/etc/syslog-ng/certs/ca.crt"
LOCAL_DIR="/etc/syslog-ng/ca"

sudo mkdir -p "$LOCAL_DIR"

# 2. Copy only if missing or different
if [[ ! -f "$LOCAL_CA" ]] || ! cmp -s <(ssh "$REMOTE" "cat '$REMOTE_CA'") "$LOCAL_CA"; then
  echo "[*] Updating CA cert from $REMOTE..."
  ssh "$REMOTE" "test -f '$REMOTE_CA'" || {
    echo "Remote cert not found: $REMOTE_CA" >&2
    exit 1
  }
  scp "$REMOTE:$REMOTE_CA" "$LOCAL_CA"
else
  echo "[*] Local CA cert already up-to-date."
fi

if [[ "$(stat -c %a "$LOCAL_CA")" != "644" ]]; then
  sudo chmod 644 "$LOCAL_CA"
fi

docker compose up --build -d
