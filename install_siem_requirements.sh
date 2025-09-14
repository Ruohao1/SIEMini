#!/bin/bash
# This script installs all the requirements for the SIEM project.

set -e
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y
sudo apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade

sudo apt-get install -y \
  build-essential cmake make gcc g++ flex bison pkg-config \
  libpcap-dev libdumbnet-dev libpcre2-dev zlib1g-dev \
  libssl-dev libnghttp2-dev libunwind-dev \
  libhwloc-dev luajit libluajit-5.1-dev \
  libhyperscan-dev libflatbuffers-dev git ethtool

sudo git clone https://github.com/snort3/snort3.git /opt/snort

cd /opt/snort
snort_path=/opt/snort

./configure_cmake.sh --prefix=$snort_path
cd build
make -j $(nproc) install

echo "export PATH=$snort_path/bin:$PATH" >>~/.bashrc
source ~/.bashrc
