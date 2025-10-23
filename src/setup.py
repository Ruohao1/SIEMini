from typing import List
import typer

from src.consts import ANSIBLE_DIR, HOSTS_INI, META_FILE
from src.inventory import inventory

from src.utils import run_command
from src.wizard import setup_wizard

setter = typer.Typer()

setter.add_typer(inventory, name="inventory", help="Set or update a host entry")


@setter.command("up")
def setup(
    tags: List[str] = typer.Option(None, help="Run playbook for specific tags"),
    limit: List[str] = typer.Option(None, help="Run playbook for specific hosts"),
):
    """
    Run the ansible playbook using the current inventory. If the inventory is not yet set, it will be created interactively.
    """
    if not (HOSTS_INI.exists() and META_FILE.exists()):
        typer.secho("❌ Inventory not yet set.", fg=typer.colors.RED)
        yes = typer.confirm("Would you like to set it up now?")
        if yes:
            setup_wizard()
        else:
            typer.secho("Aborted.", fg=typer.colors.YELLOW)

    tags = ["--tags", ",".join(tags)] if tags else []
    limit = ["--limit", ",".join(limit)] if limit else []
    hosts = ["--inventory", str(HOSTS_INI)]

    run_command(
        ["ansible-playbook", str(ANSIBLE_DIR / "main.yml"), *hosts, *tags, *limit]
    )
