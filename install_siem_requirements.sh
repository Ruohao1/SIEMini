#!/bin/bash
# This script installs all the requirements for the SIEM project.

set -e
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -y
sudo apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" upgrade

sudo apt-get install -y \
  git cmake

git clone https://github.com/snort3/snort3.git

cd snort3
snort_path=/usr/local/snort
./configure_cmake.sh --prefix=$snort_path
cd build
make -j $(nproc) install
