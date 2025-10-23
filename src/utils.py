import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
import json
import yaml
import os
import sys
import shlex
import typer

from src.consts import DEFAULTS, HOSTS_INI, HOST_VARS_DIR, INVENTORY_DIR, META_FILE


def run_command(cmd, verbose=True, stream=True, use_pty=True, cwd=None, env=None):
    """
    Run a command and (optionally) stream output live.
    - stream=True: print lines as they arrive (useful for Ansible)
    - use_pty=True: allocate a pseudo-TTY so Ansible shows colored, unbuffered output
      (Unix only; auto-falls back when unavailable)
    Returns: {"returncode", "stdout"}
    """
    cmd_list = shlex.split(cmd) if isinstance(cmd, str) else cmd
    typer.secho(f"[RUN] {' '.join(cmd_list)}", fg=typer.colors.GREEN, bold=True)

    # Detect Ansible and force color
    is_ansible = any(
        os.path.basename(str(x)).startswith("ansible") for x in (cmd_list[:1] or [])
    )
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    if is_ansible:
        run_env.setdefault("ANSIBLE_FORCE_COLOR", "1")

    if not stream:
        result = subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            env=run_env,
        )
        if verbose:
            print(result.stdout, end="")
        return {"returncode": result.returncode, "stdout": result.stdout}

    # Streaming
    stdout_accum = []

    if use_pty:
        try:
            import pty
            import select

            master_fd, slave_fd = pty.openpty()
            proc = subprocess.Popen(
                cmd_list,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=cwd,
                env=run_env,
                text=False,
                close_fds=True,
            )
            os.close(slave_fd)

            while True:
                r, _, _ = select.select([master_fd], [], [], 0.1)
                if master_fd in r:
                    try:
                        chunk = os.read(master_fd, 4096)
                    except OSError:
                        chunk = b""
                    if not chunk:
                        break
                    if verbose:
                        sys.stdout.buffer.write(chunk)
                        sys.stdout.flush()
                    stdout_accum.append(chunk)
                if proc.poll() is not None and not r:
                    break

            os.close(master_fd)
            return {
                "returncode": proc.returncode,
                "stdout": b"".join(stdout_accum).decode(errors="replace"),
            }
        except Exception:
            # PTY not available (e.g., Windows) or failed: fall back below
            pass

    with subprocess.Popen(
        cmd_list,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered
        universal_newlines=True,
        cwd=cwd,
        env=run_env,
    ) as proc:
        for line in proc.stdout:
            stdout_accum.append(line)
            if verbose:
                print(line, end="")
        proc.wait()
        return {"returncode": proc.returncode, "stdout": "".join(stdout_accum)}


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
    Build a simple hosts.ini grouped by host type (siems/targets/attackers).
    Each meta entry: {name: {ip, ansible_user, ssh_key (optional)}}
    """
    lines = []
    # order groups for predictability
    for group in ("siems", "targets", "attackers"):
        if group in meta:
            lines.append(f"[{group}]")
            entry = meta[group]
            for host_name, host_data in entry.items():
                parts = [host_name]
                ip = host_data.get("ip")
                if not ip:
                    continue
                parts.append(f"ansible_host={ip}")
                user = host_data.get("ansible_user")
                if user:
                    parts.append(f"ansible_user={user}")
                ssh_key = host_data.get("ssh_key")
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
    fname = f"{name}.yml"
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
