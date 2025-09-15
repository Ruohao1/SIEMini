#!/usr/bin/env bash
# This script installs the necessary SIEM requirements on Ubuntu 22.04

set -Eeuo pipefail
IFS=$'\n\t'

log() { echo -e "\033[1;34m[*]\033[0m $*"; }

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
sudo mkdir -p /etc/needrestart || true
echo '$nrconf{restart} = "a";' | sudo tee /etc/needrestart/needrestart.conf >/dev/null

KEYRING=/etc/apt/keyrings/syslog-ng-ose.gpg
LIST=/etc/apt/sources.list.d/syslog-ng-ose.list
if [ ! -f "$KEYRING" ]; then
  sudo mkdir -p /etc/apt/keyrings
  curl -fsSL https://ose-repo.syslog-ng.com/apt/syslog-ng-ose-pub.asc |
    sudo gpg --dearmor -o "$KEYRING"
fi
if [ ! -f "$LIST" ] || ! grep -q "ubuntu-jammy" "$LIST"; then
  echo "deb [signed-by=$KEYRING] https://ose-repo.syslog-ng.com/apt/ stable ubuntu-jammy" |
    sudo tee "$LIST" >/dev/null
fi

sudo apt-get -y update
sudo apt-get -y -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold" upgrade

sudo apt-get install -y \
  build-essential cmake make gcc g++ flex bison pkg-config git ethtool \
  libpcap-dev libdumbnet-dev libpcre2-dev zlib1g-dev libssl-dev \
  libnghttp2-dev libunwind-dev libhwloc-dev luajit libluajit-5.1-dev \
  libhyperscan-dev libflatbuffers-dev autoconf automake libtool \
  syslog-ng syslog-ng-core syslog-ng-scl

SNORT_BASE=/opt/snort3
SNORT_PREFIX=$SNORT_BASE/snort
LIBDAQ_PREFIX=/usr/local
sudo mkdir -p "$SNORT_BASE"

if ! grep -qs "^/usr/local/lib$" /etc/ld.so.conf.d/00-usr-local-lib.conf 2>/dev/null; then
  echo /usr/local/lib | sudo tee /etc/ld.so.conf.d/00-usr-local-lib.conf >/dev/null
  sudo ldconfig
fi

if ! pkg-config --exists daq 2>/dev/null; then
  log "Building libdaq (missing)"
  if [ ! -d "$SNORT_BASE/libdaq" ]; then
    sudo git clone https://github.com/snort3/libdaq.git "$SNORT_BASE/libdaq"
  else
    sudo git -C "$SNORT_BASE/libdaq" pull --ff-only
  fi
  pushd "$SNORT_BASE/libdaq" >/dev/null
  sudo ./bootstrap
  sudo ./configure --prefix="$LIBDAQ_PREFIX"
  sudo make -j"$(nproc)"
  sudo make install
  sudo ldconfig
  popd >/dev/null
else
  log "libdaq already present (version $(pkg-config --modversion daq))"
fi

if [ ! -x "$SNORT_PREFIX/bin/snort" ]; then
  log "Building Snort3"
  if [ ! -d "$SNORT_PREFIX" ]; then
    sudo git clone https://github.com/snort3/snort3.git "$SNORT_PREFIX"
  else
    sudo git -C "$SNORT_PREFIX" pull --ff-only || true
  fi
  pushd "$SNORT_PREFIX" >/dev/null
  export PKG_CONFIG_PATH="$LIBDAQ_PREFIX/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
  export CMAKE_PREFIX_PATH="$LIBDAQ_PREFIX:${CMAKE_PREFIX_PATH:-}"
  sudo ./configure_cmake.sh --prefix="$SNORT_PREFIX"
  cd build
  sudo make -j"$(nproc)" install
  sudo ldconfig
  popd >/dev/null
else
  log "Snort3 already installed at $SNORT_PREFIX"
fi

if ! grep -qs "$SNORT_PREFIX/bin" /etc/profile.d/snort.sh 2>/dev/null; then
  echo "export PATH=$SNORT_PREFIX/bin:\$PATH" | sudo tee /etc/profile.d/snort.sh >/dev/null
fi
export PATH="$SNORT_PREFIX/bin:$PATH"

sudo systemctl disable --now rsyslog 2>/dev/null || true
sudo systemctl enable --now syslog-ng

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com/ | sh
fi
if ! id -nG "$USER" | grep -qw docker; then
  sudo usermod -aG docker "$USER"
  newgrp docker
fi

ELASTIC_DIR="/opt/elastic-start-local"
ES_NAME="es-local-dev"
KB_NAME="kibana-local-dev"

if docker ps --format '{{.Names}}' | grep -Eq "^($ES_NAME|$KB_NAME)$"; then
  echo "[*] Elastic local already running."
else
  # 2) Exists but stopped? start.
  if docker ps -a --format '{{.Names}}' | grep -Eq "^($ES_NAME|$KB_NAME)$"; then
    docker start "$ES_NAME" 2>/dev/null || true
    docker start "$KB_NAME" 2>/dev/null || true
  else
    # 3) No containers yet → ensure compose files exist
    if [ ! -f "$ELASTIC_DIR/docker-compose.yml" ]; then
      # The script creates ./elastic-local under the current dir
      (cd /opt && curl -fsSL https://elastic.co/start-local | sh)
      # If it created /opt/elastic-local and you want /opt/elastic-start-local, rename once
      if [ -d /opt/elastic-local ] && [ "$ELASTIC_DIR" != "/opt/elastic-local" ]; then
        mv /opt/elastic-local "$ELASTIC_DIR"
      fi
    fi

    if grep -q '127\.0\.0\.1:' "$ELASTIC_DIR/docker-compose.yml"; then
      sed -i 's/127\.0\.0\.1:/0.0.0.0:/g' "$ELASTIC_DIR/docker-compose.yml"
    fi

    if docker compose version >/dev/null 2>&1; then
      (cd "$ELASTIC_DIR" && docker compose up -d)
    else
      (cd "$ELASTIC_DIR" && docker-compose up -d)
    fi
  fi
fi

log "Versions:"
snort -V || true
syslog-ng --version || true
curl -fsS http://127.0.0.1:9200 >/dev/null && echo "[*] Elasticsearch responding on 9200"
curl -fsS http://127.0.0.1:5601 >/dev/null && echo "[*] Kibana responding on 5601"
