#!/usr/bin/env python3

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
import yaml
from rich.console import Console
from typing_extensions import Annotated

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import and configure prefs
from neurpi.prefs import configure_prefs

console = Console()
app = typer.Typer(
    name="neurpi",
    help="NeuRPi CLI - Run agents with specified configuration.",
    rich_markup_mode="rich",
)


def load_config(config_file):
    """Load configuration from YAML file."""
    try:
        with config_file.open() as f:
            return yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError) as e:
        console.print(f"[red]Error loading config {config_file}: {e}[/red]")
        sys.exit(1)


def run_agent(mode):
    """Run the specified agent with python from VENVDIR."""
    configure_prefs(mode)
    if mode == "controller":
        config_file = project_root / "neurpi" / "config" / "controller.yaml"
        agent_script = project_root / "neurpi" / "agents" / "controller.py"
    elif mode == "rig":
        config_file = project_root / "neurpi" / "config" / "rig.yaml"
        agent_script = project_root / "neurpi" / "agents" / "rig.py"
    else:
        console.print(f"[red]Unknown agent type: {mode}[/red]")
        sys.exit(1)
    config = load_config(config_file)
    venv_dir = config.get("VENVDIR", "venv/")
    python_exe = project_root / venv_dir / "Scripts" / "python.exe" if venv_dir.startswith(("./", "../", ".")) else Path(venv_dir) / "Scripts" / "python.exe"
    console.print(f"[green]Starting {mode} agent...[/green]")
    console.print(f"[blue]Python: {python_exe}[/blue]")
    console.print(f"[blue]Script: {agent_script}[/blue]")
    try:
        if not python_exe.exists():
            console.print(f"[red]Python executable not found: {python_exe}[/red]")
            console.print("[yellow]Make sure the virtual environment is set up correctly[/yellow]")
            sys.exit(1)
        if not agent_script.exists():
            console.print(f"[red]Agent script not found: {agent_script}[/red]")
            sys.exit(1)
        subprocess.run([str(python_exe), str(agent_script)], check=True)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Agent failed with exit code {e.returncode}[/red]")
        sys.exit(e.returncode)
    except FileNotFoundError as e:
        console.print(f"[red]File error: {e}[/red]")
        sys.exit(1)


def run_agent_direct(mode: str, *, no_gui: bool = False, name: str | None = None):
    """Run the specified agent directly by importing and executing it."""
    configure_prefs(mode)
    if mode == "controller":
        try:
            from neurpi.agents.controller import main as controller_main

            controller_main()
        except ImportError as e:
            console.print(f"[red]Failed to import controller agent: {e}[/red]")
            sys.exit(1)
    elif mode == "rig":
        try:
            from neurpi.agents.rig import main as rig_main

            rig_main()
        except ImportError as e:
            console.print(f"[red]Failed to import rig agent: {e}[/red]")
            sys.exit(1)
    else:
        console.print(f"[red]Unknown agent type: {mode}[/red]")
        sys.exit(1)


@app.command()
def controller(
    no_gui: Annotated[bool, typer.Option("--no-gui", help="Run without GUI")] = False,
):
    """Run as Controller (controller/interface)."""
    mode = "controller"
    configure_prefs(mode)
    console.print(f"[green]Starting controller agent{' (no GUI)' if no_gui else ' (with GUI)'}...[/green]")
    try:
        run_agent_direct(mode, no_gui=no_gui)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(130) from None


@app.command()
def rig(
    name: Annotated[str | None, typer.Option("--name", help="Rig name")] = None,
):
    """Run as Rig (experiment execution)."""
    mode = "rig"
    configure_prefs(mode)
    console.print(f"[green]Starting rig agent{f' ({name})' if name else ''}...[/green]")
    try:
        run_agent_direct(mode, name=name)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(130) from None


@app.command()
def status():
    """Show system status."""
    console.print("[green]NeuRPi CLI is operational[/green]")
    console.print("[blue]Use 'neurpi controller' or 'neurpi rig' to start agents[/blue]")


def main():
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        raise typer.Exit(130) from None


if __name__ == "__main__":
    main()
