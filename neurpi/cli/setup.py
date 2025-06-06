#!/usr/bin/env python3

import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def read_requirements_from_toml(group_name):
    """Read requirements from pyproject.toml file."""
    project_root = Path(__file__).parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        print("Error: pyproject.toml not found. Please ensure you're in the NeuRPi project root.")
        return []

    try:
        # Try to import tomllib (Python 3.11+) or tomli
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                print("Error: tomllib/tomli not available. Please install with: pip install tomli")
                return []

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        project_config = config.get("project", {})

        if group_name == "core":
            # Core dependencies are in the main dependencies list
            return project_config.get("dependencies", [])
        else:
            # Optional dependencies
            optional_deps = project_config.get("optional-dependencies", {})
            return optional_deps.get(group_name, [])

    except Exception as e:
        print(f"Error: Failed to read pyproject.toml: {e}")
        return []


def ensure_click_rich():
    """Ensure Click and Rich are available for CLI functionality."""
    missing = []

    try:
        import click
    except ImportError:
        missing.append('click>=8.0.0')

    try:
        from rich.console import Console
    except ImportError:
        missing.append('rich>=13.0.0')

    if missing:
        print(f"Installing CLI dependencies: {', '.join(missing)}")
        for package in missing:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", package],
                             check=True, capture_output=True, text=True)
                print(f"✓ {package} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package}: {e}")
                sys.exit(1)


def install_dependencies(python_exe, group_name, use_uv=False, uv_executable=None):
    """Install dependencies from a dependency group (core, gui, dev, hardware)."""
    requirements = read_requirements_from_toml(group_name)
    if not requirements:
        print(f"No requirements found for group '{group_name}'")
        return True, []

    failed_packages = []
    success = True

    for dep in requirements:
        try:
            print(f"Installing {dep}...")
            if use_uv and uv_executable:
                subprocess.run([uv_executable, "pip", "install", dep, "--python", str(python_exe)],
                             check=True, capture_output=True)
            else:
                subprocess.run([str(python_exe), "-m", "pip", "install", dep],
                             check=True, capture_output=True)
            print(f"✓ {dep} installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"Warning: Failed to install {dep}")
            failed_packages.append(dep)
            if "pandas" in dep:
                success = False

    return success, failed_packages


def setup_neurpi(minimal=False, gui=False, hardware=False, dev=False, full=False, python_version="3.9.13"):
    """Set up NeuRPi development environment with selective dependency installation."""

    # Ensure CLI dependencies
    ensure_click_rich()

    # Now we can safely import
    from rich.console import Console
    console = Console()

    # Determine which dependency groups to install
    dependency_groups = []

    # If no flags specified, default to full installation
    if not any([minimal, gui, hardware, dev, full]):
        full = True

    if minimal:
        dependency_groups = ['core']
        console.print("[bold blue]Setting up NeuRPi with MINIMAL dependencies (core only)...[/bold blue]")
    elif gui:
        dependency_groups = ['core', 'gui']
        console.print("[bold blue]Setting up NeuRPi with GUI dependencies...[/bold blue]")
    elif hardware:
        dependency_groups = ['core', 'hardware']
        console.print("[bold blue]Setting up NeuRPi with HARDWARE dependencies...[/bold blue]")
    elif dev:
        dependency_groups = ['core', 'dev']
        console.print("[bold blue]Setting up NeuRPi with DEVELOPMENT dependencies...[/bold blue]")
    elif full:
        dependency_groups = ['core', 'gui', 'hardware', 'dev']
        console.print("[bold blue]Setting up NeuRPi with FULL dependencies...[/bold blue]")

    console.print(f"[cyan]Installing dependency groups: {', '.join(dependency_groups)}[/cyan]")
    console.print(f"[cyan]Using Python version: {python_version}[/cyan]")

    project_root = Path(__file__).parent.parent.parent
    venv_path = project_root / ".venv"

    try:
        # Step 1: Create virtual environment
        if not venv_path.exists():
            console.print(f"[green]Creating virtual environment with Python {python_version}...[/green]")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            console.print("[green]✓ Virtual environment created[/green]")
        else:
            console.print("[yellow]Virtual environment already exists[/yellow]")

        # Step 2: Determine python executable path
        python_exe = venv_path / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

        # Step 3: Install selected dependency groups
        console.print("[green]Installing selected dependencies...[/green]")

        all_failed_packages = []
        pandas_success = True

        for group in dependency_groups:
            console.print(f"Installing {group} dependencies...")
            success, failed_packages = install_dependencies(python_exe, group)
            all_failed_packages.extend(failed_packages)

            if group == 'core' and not success:
                pandas_success = False

        # Step 4: Install the package in editable mode
        console.print("[green]Installing NeuRPi in editable mode...[/green]")
        try:
            subprocess.run([str(python_exe), "-m", "pip", "install", "-e", str(project_root)], check=True)
            console.print("[green]✓ NeuRPi installed in editable mode[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]Warning: Failed to install NeuRPi in editable mode: {e}[/yellow]")

        # Step 5: Success message
        console.print(f"\n[bold green]✓ Setup completed![/bold green]")
        console.print(f"[green]✓ Installed dependency groups: {', '.join(dependency_groups)}[/green]")

        if all_failed_packages:
            console.print(f"[yellow]Some dependencies failed: {', '.join(set(all_failed_packages))}[/yellow]")

        console.print("\n[bold blue]To activate the virtual environment:[/bold blue]")
        if platform.system() == "Windows":
            console.print("[cyan]  .venv\\Scripts\\activate[/cyan]")
        else:
            console.print("[cyan]  source .venv/bin/activate[/cyan]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Setup failed: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    ensure_click_rich()

    import click

    @click.command()
    @click.option('--minimal', is_flag=True, help='Install only core dependencies')
    @click.option('--gui', is_flag=True, help='Install core + GUI dependencies')
    @click.option('--hardware', is_flag=True, help='Install core + hardware dependencies')
    @click.option('--dev', is_flag=True, help='Install core + development dependencies')
    @click.option('--full', is_flag=True, help='Install all dependencies (default)')
    @click.option('--python-version', default='3.9.13', help='Python version to use (default: 3.9.13)')
    def cli(minimal, gui, hardware, dev, full, python_version):
        """Set up NeuRPi development environment with selective dependency installation."""
        setup_neurpi(minimal, gui, hardware, dev, full, python_version)

    try:
        cli()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
