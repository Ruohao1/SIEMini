#!/bin/bash
set -euo pipefail

# Parse options
OPTS=$(getopt -o h: --long host: -- "$@") || {
  echo "Error parsing options"
  exit 2
}
eval set -- "$OPTS"

HOST=""
while true; do
  case "$1" in
  -h | --host)
    HOST="$2"
    shift 2
    ;;
  --)
    shift
    break
    ;;
  *)
    echo "Parse error"
    exit 3
    ;;
  esac
done

# Dispatch
case "$HOST" in
web)
  echo "Running web server setup..."
  cd web && ./setup.sh
  ;;
siem)
  echo "Running SIEM setup..."
  cd siem && ./setup.sh
  ;;
attacker)
  echo "Running attacker VM setup..."
  ./setup_attacker.sh
  ;;
"")
  echo "Missing --host option. Usage: $0 --host <web|siem|attacker>"
  exit 1
  ;;
*)
  echo "Unknown host: $HOST"
  echo "Valid options are: web, siem, attacker"
  exit 1
  ;;
esac
