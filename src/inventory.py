from typing import Optional
import typer
import getpass

from .consts import DEFAULTS, INVENTORY_DIR
from .utils import (
    ensure_dirs,
    load_meta,
    validate_key_path,
    require_either_key_or_pass,
    save_meta,
    render_hosts_ini,
    write_host_vars,
)

inventory = typer.Typer()


def set_host(
    group: str,
    name: str,
    ip: str,
    ssh_key: Optional[str],
    root_user: Optional[str],
    root_user_pass: Optional[str],
    ansible_user: Optional[str],
):
    ensure_dirs()
    if root_user and not root_user_pass:
        root_user_pass = getpass.getpass(f"Password for {root_user}@{ip}: ")

    ssh_key_valid = validate_key_path(ssh_key)
    require_either_key_or_pass(ssh_key_valid, root_user, root_user_pass)

    meta = load_meta()
    entry = meta.get(group, {}).get(name, {})
    entry["ip"] = ip
    if ansible_user:
        entry["ansible_user"] = ansible_user
    elif "ansible_user" not in entry:
        entry["ansible_user"] = DEFAULTS[group]["ansible_user"]

    if ssh_key_valid:
        entry["ssh_key"] = ssh_key_valid
        entry.pop("root_user", None)
        entry.pop("root_user_pass", None)
    else:
        entry["root_user"] = root_user
        entry["root_user_pass"] = root_user_pass
        typer.secho(
            "⚠️ Warning: storing plaintext passwords in inventory is insecure.",
            fg=typer.colors.YELLOW,
        )

    # ensure group exists
    if group not in meta:
        meta[group] = {}
    meta[group][name] = entry
    save_meta(meta)
    render_hosts_ini(meta)
    write_host_vars(group, name, entry)
    typer.secho(
        f"✅ {group}/{name} written: {INVENTORY_DIR}/hosts.ini + host_vars/{group}_{name}.yml",
        fg=typer.colors.GREEN,
    )


@inventory.command("target")
def set_target(
    name: str = typer.Argument(..., help="Name for this target (e.g. web01)"),
    ip: str = typer.Option(..., help="IP or hostname"),
    ssh_key: Optional[str] = typer.Option(None, help="Path to private SSH key"),
    root_user: Optional[str] = typer.Option(
        None, help="Root/admin user (password authentication)"
    ),
    root_user_pass: Optional[str] = typer.Option(
        None, help="Password for root_user (unsafe on CLI!)"
    ),
    ansible_user: Optional[str] = typer.Option(None, help="Override ansible_user"),
):
    """Add or update a TARGET host (supports multiple targets)."""
    set_host("target", name, ip, ssh_key, root_user, root_user_pass, ansible_user)


@inventory.command("siem")
def set_siem(
    name: str = typer.Argument(..., help="Name for this SIEM host (e.g. siem01)"),
    ip: str = typer.Option(..., help="IP or hostname"),
    ssh_key: Optional[str] = typer.Option(None, help="Path to private SSH key"),
    root_user: Optional[str] = typer.Option(
        None, help="Root/admin user (password authentication)"
    ),
    root_user_pass: Optional[str] = typer.Option(
        None, help="Password for root_user (unsafe on CLI!)"
    ),
    ansible_user: Optional[str] = typer.Option(None, help="Override ansible_user"),
):
    set_host("siem", name, ip, ssh_key, root_user, root_user_pass, ansible_user)


@inventory.command("attacker")
def set_attacker(
    name: str = typer.Argument(..., help="Name for this attacker host (e.g. kali01)"),
    ip: str = typer.Option(..., help="IP or hostname"),
    ssh_key: Optional[str] = typer.Option(None, help="Path to private SSH key"),
    root_user: Optional[str] = typer.Option(
        None, help="Root/admin user (password authentication)"
    ),
    root_user_pass: Optional[str] = typer.Option(
        None, help="Password for root_user (unsafe on CLI!)"
    ),
    ansible_user: Optional[str] = typer.Option(None, help="Override ansible_user"),
):
    set_host("attacker", name, ip, ssh_key, root_user, root_user_pass, ansible_user)


if __name__ == "__main__":
    inventory()
