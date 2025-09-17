#!/bin/bash

OPTS=$(getopt -o h: --long host: -- "$@")
eval set -- "$OPTS"

while true; do
  case "$1" in
  -h | --host)
    FILE="$2"
    shift 2
    ;;
  --)
    shift
    break
    ;;
  *) break ;;
  esac
done

case "$HOST" in
web)
  echo "Running web server setup..."
  ./setup_web.sh
  ;;
siem)
  echo "Running SIEM setup..."
  ./setup_siem.sh
  ;;
attacker)
  echo "Running attacker VM setup..."
  ./setup_attacker.sh
  ;;
*)
  echo "Unknown host: $HOST"
  echo "Valid options are: web, siem, attacker"
  exit 1
  ;;
esac
