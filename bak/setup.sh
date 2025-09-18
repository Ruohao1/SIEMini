#!/usr/bin/env bash
set -euo pipefail

# Default env file (optional)
ENVFILE=".env"

usage() {
  cat <<EOF
Usage: $0 --host <web|siem|attacker> [--user <user>] [--env <envfile>]
Examples:
  $0 --host web --user alice
  $0 --host siem
  $0 --host attacker --env .env.siem
EOF
  exit 1
}

# Simple arg parsing
HOST=""
USER=""
while [[ $# -gt 0 ]]; do
  case "$1" in
  --host)
    HOST="$2"
    shift 2
    ;;
  --user)
    USER="$2"
    shift 2
    ;;
  --env)
    ENVFILE="$2"
    shift 2
    ;;
  -h | --help) usage ;;
  *)
    echo "Unknown argument: $1"
    usage
    ;;
  esac
done

# Load env file if it exists
if [[ -n "${ENVFILE:-}" && -f "$ENVFILE" ]]; then
  set -a
  source "$ENVFILE"
  set +a
fi

# Basic validation
if [[ -z "${HOST:-}" ]]; then
  echo "Missing --host option."
  usage
fi

case "$HOST" in
web)
  # user is required for web
  if [[ -z "${USER:-}" ]]; then
    echo "Missing --user for host 'web'. Use: --user <user>"
    exit 1
  fi
  echo "Running web server setup..."
  (cd web && ./setup.sh "$USER")
  ;;
siem)
  echo "Running SIEM setup..."
  (cd siem && ./setup.sh)
  ;;
attacker)
  echo "Running attacker VM setup..."
  # optionally you might want to cd into attacker/ if setup script is inside that dir:
  (cd attacker && ./setup.sh)
  ;;
*)
  echo "Unknown host: $HOST"
  echo "Valid options are: web, siem, attacker"
  exit 1
  ;;
esac
