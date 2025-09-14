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

sudo mkdir /opt/snort3
snort3_path=/opt/snort3

sudo git clone https://github.com/snort3/libdaq.git $snort3_path/libdaq
cd $snort3_path/libdaq
sudo ./bootstrap
sudo ./configure
sudo make
sudo make install
sudo ldconfig

snort_path=$snort3_path/snort

sudo git clone https://github.com/snort3/snort3.git $snort_path
cd $snort_path

sudo ./configure_cmake.sh --prefix=$snort_path
cd build
sudo make -j $(nproc) install

echo "export PATH=$snort_path/bin:$PATH" >>~/.bashrc
source ~/.bashrc
