import typer

from src.setter import setter
from src.consts import HOSTS_INI
from src.utils import ensure_dirs, load_meta

app = typer.Typer()
app.add_typer(setter, name="set", help="Set or update a host entry")


@app.command("list-inventory")
def show_inventory():
    """Print current inventory meta and hosts.ini for debugging."""
    ensure_dirs()
    meta = load_meta()
    typer.echo("---- meta (.meta.json) ----")
    for group, hosts in meta.items():
        typer.secho(f"== {group} ==", fg=typer.colors.CYAN)
        if not hosts:
            typer.echo("  (none)")
            continue
        for name, entry in hosts.items():
            user = entry.get("ansible_user", "")
            ip = entry.get("ip", "")
            auth = (
                "key"
                if entry.get("ssh_key")
                else ("pass" if entry.get("root_user") else "unknown")
            )
            typer.echo(f"  {name}: {ip} user={user} auth={auth}")
    typer.echo("\n---- hosts.ini ----")
    if HOSTS_INI.exists():
        typer.echo(HOSTS_INI.read_text())
    else:
        typer.echo("(hosts.ini not yet generated)")


if __name__ == "__main__":
    app()
