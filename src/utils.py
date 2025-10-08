import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import json
import yaml
import typer

from .consts import INVENTORY_DIR, META_FILE, HOSTS_INI, HOST_VARS_DIR, DEFAULTS


def run_command(cmd, verbose=True):
    print(f"Running command: {cmd}")

    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )

    if verbose:
        print(result.stdout)

    return result


def ensure_dirs():
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
    HOST_VARS_DIR.mkdir(parents=True, exist_ok=True)


def load_meta() -> Dict[str, Any]:
    if META_FILE.exists():
        try:
            return json.loads(META_FILE.read_text())
        except Exception:
            # corrupted meta: back it up and start fresh
            META_FILE.rename(META_FILE.with_suffix(".json.bak"))
    return {}


def save_meta(meta: Dict[str, Any]):
    META_FILE.write_text(json.dumps(meta, indent=2))


def render_hosts_ini(meta: Dict[str, Any]):
    """
    Build a simple hosts.ini grouped by host type (siem/target/attacker).
    Each meta entry: {name: {ip, ansible_user, ssh_key (optional)}}
    """
    lines = []
    # order groups for predictability
    for group in ("siem", "target", "attacker"):
        if group in meta:
            lines.append(f"[{group}]")
            entry = meta[group]
            ip = entry.get("ip")
            if not ip:
                continue
            parts = [ip]
            user = entry.get("ansible_user")
            if user:
                parts.append(f"ansible_user={user}")
            ssh_key = entry.get("ssh_key")
            if ssh_key:
                parts.append(f"ansible_ssh_private_key_file={ssh_key}")
            # if using password-only (no key), don't write password in hosts.ini
            lines.append(" ".join(parts))
            lines.append("")
    HOSTS_INI.write_text("\n".join(lines).strip() + "\n")


def write_host_vars(group: str, name: str, data: Dict[str, Any]):
    merged = {}
    merged.update(DEFAULTS.get(group, {}))
    merged.update(data)
    # remove None
    merged = {k: v for k, v in merged.items() if v is not None}
    fname = f"{group}_{name}.yml"
    with open(HOST_VARS_DIR / fname, "w") as f:
        yaml.safe_dump(merged, f, sort_keys=False)


def validate_key_path(p: Optional[str]) -> Optional[str]:
    if not p:
        return None
    p_path = Path(p).expanduser()
    if p_path.exists() and p_path.is_file():
        return str(p_path.resolve())
    typer.secho(
        f"⚠️ SSH key path '{p}' not found — ignoring the key.", fg=typer.colors.YELLOW
    )
    return None


def require_either_key_or_pass(
    ssh_key: Optional[str], root_user: Optional[str], root_user_pass: Optional[str]
):
    if ssh_key and (root_user or root_user_pass):
        typer.secho(
            "❌ Provide either --ssh-key OR --root-user/--root-user-pass, not both.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)
    if not ssh_key and not (root_user and root_user_pass):
        typer.secho(
            "❌ You must provide either --ssh-key or both --root-user and --root-user-pass.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)
