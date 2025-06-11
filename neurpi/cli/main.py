#!/usr/bin/env python3

import subprocess
import sys
from pathlib import Path

import click
import yaml
from rich.console import Console

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import and configure prefs
from neurpi.prefs import configure_prefs

console = Console()


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
    # Configure prefs for the specific mode
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

    # Load config to get VENVDIR
    config = load_config(config_file)
    venv_dir = config.get("VENVDIR", "venv/")  # Construct python executable path
    if venv_dir.startswith(("./", "../", ".")):
        # Relative path - resolve relative to project root
        python_exe = project_root / venv_dir / "Scripts" / "python.exe"
    else:
        # Absolute path
        python_exe = Path(venv_dir) / "Scripts" / "python.exe"

    console.print(f"[green]Starting {mode} agent...[/green]")
    console.print(f"[blue]Python: {python_exe}[/blue]")
    console.print(f"[blue]Script: {agent_script}[/blue]")

    try:
        # Validate that files exist before running
        if not python_exe.exists():
            console.print(f"[red]Python executable not found: {python_exe}[/red]")
            console.print(
                "[yellow]Make sure the virtual environment is set up correctly[/yellow]",
            )
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


def run_agent_direct(mode, no_gui=False, name=None):
    """Run the specified agent directly by importing and executing it."""
    # Configure prefs for the specific mode
    configure_prefs(mode)

    if mode == "controller":
        try:
            # Import and run the controller agent
            from neurpi.agents.controller import main as controller_main

            controller_main()
        except ImportError as e:
            console.print(f"[red]Failed to import controller agent: {e}[/red]")
            sys.exit(1)
    elif mode == "rig":
        try:
            # Import and run the rig agent
            from neurpi.agents.rig import main as rig_main

            rig_main()
        except ImportError as e:
            console.print(f"[red]Failed to import rig agent: {e}[/red]")
            sys.exit(1)
    else:
        console.print(f"[red]Unknown agent type: {mode}[/red]")
        sys.exit(1)


@click.group()
def cli():
    """NeuRPi CLI - Run agents with specified configuration."""


@cli.command()
@click.option("--no-gui", is_flag=True, help="Run without GUI")
def controller(no_gui):
    """Run as Controller (controller/interface)."""
    mode = "controller"
    configure_prefs(mode)
    console.print(
        f"[green]Starting controller agent{'(no GUI)' if no_gui else '(with GUI)'}...[/green]",
    )

    try:
        run_agent_direct(mode, no_gui)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)


@cli.command()
@click.option("--name", help="Rig name")
def rig(name):
    """Run as Rig (experiment execution)."""
    mode = "rig"
    configure_prefs(mode)
    console.print(f"[green]Starting rig agent{f' ({name})' if name else ''}...[/green]")

    try:
        run_agent_direct(mode, False, name)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)


@cli.command()
def status():
    """Show system status."""
    # For now, just show that the CLI is working
    console.print("[green]NeuRPi CLI is operational[/green]")
    console.print(
        "[blue]Use 'neurpi controller' or 'neurpi rig' to start agents[/blue]",
    )


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
