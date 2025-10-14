from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional
import getpass
import json
import typer

from .consts import DEFAULTS, INVENTORY_DIR, HOSTS_INI, HOST_VARS_DIR, META_FILE
from .utils import (
    ensure_dirs,
    load_meta,
    validate_key_path,
    save_meta,
    render_hosts_ini,
    write_host_vars,
)

SSH_KEY_CANDIDATES = [
    "~/.ssh/id_ed25519",
    "~/.ssh/id_rsa",
    "~/.ssh/id_ecdsa",
    "~/.ssh/id_ed25519_sk",
    "~/.ssh/id_rsa_sk",
]


# ---------- small utils ----------
def ask(prompt: str, default: Optional[str] = None) -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or (default or "")


def yesno(prompt: str, default: bool = True) -> bool:
    d = "Y/n" if default else "y/N"
    val = input(f"{prompt} ({d}): ").strip().lower()
    if not val:
        return default
    return val in {"y", "yes"}


def detect_ssh_key() -> Optional[str]:
    for cand in SSH_KEY_CANDIDATES:
        p = Path(cand).expanduser()
        if p.exists() and p.is_file():
            return str(p.resolve())
    return None


def choose_auth(ip: str, default_user: str) -> Dict[str, Any]:
    """Ask user to choose SSH key or password auth and collect details."""
    use_key = yesno("Use SSH private key authentication?", True)
    result: Dict[str, Any] = {"ansible_user": default_user}

    if use_key:
        auto = detect_ssh_key()
        key = ask("Path to private key", auto or "")
        key_path = validate_key_path(key)
        if not key_path:
            typer.secho(
                "No valid key selected. Falling back to password.",
                fg=typer.colors.YELLOW,
            )
            use_key = False
        else:
            result["ssh_key"] = key_path

    if not use_key:
        root_user = ask("Root/admin user (for password auth)", "root")
        # prompt safely without echo
        pwd = getpass.getpass(f"Password for {root_user}@{ip}: ")
        if not pwd:
            typer.secho(
                "Empty password provided; continuing but this will likely fail later.",
                fg=typer.colors.YELLOW,
            )
        result["root_user"] = root_user
        result["root_user_pass"] = pwd
        typer.secho(
            "⚠️ Storing plaintext passwords locally. Prefer Ansible Vault in real setups.",
            fg=typer.colors.YELLOW,
        )

    return result


# ---------- wizard steps ----------
def add_many(
    group: str, default_name: str, default_user: str, meta: Dict[str, Dict[str, Any]]
):
    typer.secho(f"\n=== Configure {group.upper()} hosts ===", fg=typer.colors.CYAN)

    while True:
        name = ask(f"{group} name", default_name)
        ip = ask(f"IP/hostname for {name}")
        user = ask(f"Default user for {name}", default_user)
        auth = choose_auth(ip, user)

        entry = {"ip": ip, **auth}

        # allow a few group-specific extra questions
        if group == "targets":
            siem_ip = ask("SIEM IP address", str(DEFAULTS["target"]["siem_ip"]))
            web_port = ask("Target web port", str(DEFAULTS["target"]["web_port"]))
            ssh_port = ask("Target SSH port", str(DEFAULTS["target"]["ssh_port"]))
            entry["web_port"] = int(web_port)
            entry["ssh_port"] = int(ssh_port)
            entry["siem_ip"] = siem_ip

        if group == "siems":
            entry["syslog_ng_port"] = DEFAULTS["siem"]["syslog_ng_port"]
            entry["elasticsearch_port"] = DEFAULTS["siem"]["elasticsearch_port"]
            entry["kibana_port"] = DEFAULTS["siem"]["kibana_port"]
            entry["ids_tool"] = DEFAULTS["siem"]["ids_tool"]

        meta.setdefault(group, {})
        meta[group][name] = entry

        if not yesno(f"Add another {group} host?", False):
            break
        # bump default_name if user keeps adding
        if default_name.rstrip("0123456789").startswith(group):
            # crude increment
            digits = "".join(ch for ch in default_name if ch.isdigit())
            n = int(digits or "1") + 1
            default_name = f"{group}{n}"


def setup_wizard():
    ensure_dirs()
    meta = load_meta()

    typer.secho(
        "SIEM Lab – Interactive Inventory Setup", fg=typer.colors.GREEN, bold=True
    )

    # SIEM(s)
    if yesno("Configure SIEM hosts?", True):
        add_many("siems", "siem01", DEFAULTS["siem"]["ansible_user"], meta)

    # Target(s)
    if yesno("Configure TARGET hosts?", True):
        add_many("targets", "web01", DEFAULTS["target"]["ansible_user"], meta)

    # Attacker(s)
    if yesno("Configure ATTACKER hosts?", True):
        add_many("attackers", "kali01", DEFAULTS["attacker"]["ansible_user"], meta)

    # Final confirmation
    typer.secho("\nSummary to be written:", fg=typer.colors.MAGENTA)
    typer.echo(json.dumps(meta, indent=2))
    if not yesno("Write inventory to disk now?", True):
        typer.secho("Aborted. No files changed.", fg=typer.colors.YELLOW)
        return

    # Save + render
    save_meta(meta)
    render_hosts_ini(meta)
    # write all host_vars
    for group, hosts in meta.items():
        for name, entry in hosts.items():
            write_host_vars(group, name, entry)

    typer.secho(f"\n✅ Inventory written to {INVENTORY_DIR}/", fg=typer.colors.GREEN)
    typer.secho(f"   - {HOSTS_INI}", fg=typer.colors.GREEN)
    typer.secho(f"   - {HOST_VARS_DIR}/*.yml", fg=typer.colors.GREEN)
    typer.secho(f"   - {META_FILE}", fg=typer.colors.GREEN)
