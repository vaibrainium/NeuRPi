#!/usr/bin/env python3

import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def check_uv_available():
    """Check if uv is available and return the executable path."""
    uv_path = shutil.which("uv")
    if uv_path:
        # Test if uv is working
        try:
            result = subprocess.run([uv_path, "--version"],
                                  capture_output=True, text=True, timeout=10, check=False)
            if result.returncode == 0:
                return uv_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            print("uv found but not working properly.")

    print("uv not found or not working. Installing uv...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "uv"],
                      check=True, capture_output=True, text=True)
        uv_path = shutil.which("uv")
        if uv_path:
            # Test the newly installed uv
            try:
                result = subprocess.run([uv_path, "--version"],
                                      capture_output=True, text=True, timeout=10, check=False)
                if result.returncode == 0:
                    print("✓ uv installed and working")
                    return uv_path
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass
        print("uv installation completed but may not be working properly.")
        return uv_path
    except subprocess.CalledProcessError as e:
        print(f"Failed to install uv: {e}")
        print("Falling back to pip for dependency management.")
        return None


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
            return project_config.get("dependencies", [])
        else:
            optional_deps = project_config.get("optional-dependencies", {})
            return optional_deps.get(group_name, [])

    except (OSError, IOError, TypeError, KeyError) as e:
        print(f"Error: Failed to read pyproject.toml: {e}")
        return []

def create_executable_script(project_root, venv_path):
    """Create platform-specific executable script (neurpi.sh or neurpi.bat)."""
    from rich.console import Console
    console = Console()

    if platform.system() == "Windows":
        script_name = "start.bat"
        script_content = f"""@echo off
REM NeuRPi executable script for Windows
cd /d "{project_root}"
call "{venv_path}\\Scripts\\activate.bat"
python -m neurpi %*
"""
    else:
        script_name = "start.sh"
        script_content = f"""#!/bin/bash
# NeuRPi executable script for Unix/Linux
cd "{project_root}"
source "{venv_path}/bin/activate"
python -m neurpi "$@"
"""

    script_path = project_root / script_name

    try:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)

        # Make the script executable on Unix/Linux
        if platform.system() != "Windows":
            script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

        console.print(f"[green]✓ Created executable script: {script_name}[/green]")
        console.print(f"[blue]You can now run NeuRPi using: ./{script_name} [command] [options][/blue]")

    except OSError as e:
        console.print(f"[red]Warning: Failed to create executable script: {e}[/red]")


def ensure_essential_dependencies():
    """Ensure essential dependencies (tomli, click, rich) are available before any operations."""
    missing = []

    # Check for tomli availability (needed for TOML parsing)
    try:
        import tomli  # noqa: F401
    except ImportError:
        missing.append('tomli>=1.2.0')

    # Check for click availability
    try:
        import click  # noqa: F401
    except ImportError:
        missing.append('click>=8.0.0')

    # Check for rich availability
    try:
        import rich  # noqa: F401
    except ImportError:
        missing.append('rich>=13.0.0')

    if missing:
        print(f"Installing essential dependencies: {', '.join(missing)}")
        uv_executable = check_uv_available()

        for package in missing:
            try:
                # First try with regular pip
                subprocess.run([sys.executable, "-m", "pip", "install", package],
                             check=True, capture_output=True, text=True)
                print(f"✓ {package} installed successfully with pip")
            except subprocess.CalledProcessError as e:
                if uv_executable:
                    print(f"pip failed for {package}, trying with uv...")
                    try:
                        subprocess.run([uv_executable, "pip", "install", package],
                                     check=True, capture_output=True, text=True)
                        print(f"✓ {package} installed successfully with uv")
                    except subprocess.CalledProcessError as uv_e:
                        print(f"Failed to install {package} with both pip and uv: pip={e}, uv={uv_e}")
                        sys.exit(1)
                else:
                    print(f"Failed to install {package} with pip and uv not available: {e}")
                    sys.exit(1)

def install_dependencies(python_exe, group_name, use_uv=True, uv_executable=None):
    """Install dependencies from a dependency group (core, gui, dev, hardware)."""
    requirements = read_requirements_from_toml(group_name)
    if not requirements:
        print(f"No requirements found for group '{group_name}'")
        return True, []

    failed_packages = []
    success = True

    for dep in requirements:
        installed = False
        print(f"Installing {dep}...")

        # Try with uv first if available
        if use_uv and uv_executable:
            try:
                subprocess.run([uv_executable, "pip", "install", dep, "--python", str(python_exe)],
                             check=True, capture_output=True, text=True, timeout=300)
                print(f"✓ {dep} installed with uv")
                installed = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                print(f"uv failed for {dep}, trying with pip...")

        # Fallback to regular pip if uv failed or not available
        if not installed:
            try:
                subprocess.run([str(python_exe), "-m", "pip", "install", dep],
                             check=True, capture_output=True, text=True, timeout=300)
                print(f"✓ {dep} installed with pip")
                installed = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # If both methods failed, try uv one more time with different flags
                if uv_executable and use_uv:
                    try:
                        print(f"Retrying {dep} with uv and force-reinstall...")
                        subprocess.run([uv_executable, "pip", "install", dep, "--python", str(python_exe),
                                      "--force-reinstall", "--no-deps"],
                                     check=True, capture_output=True, text=True, timeout=300)
                        print(f"✓ {dep} installed with uv (force-reinstall)")
                        installed = True
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                        pass

        if not installed:
            print(f"⚠️  Failed to install {dep} with all methods")
            failed_packages.append(dep)
            if "pandas" in dep or "numpy" in dep or "torch" in dep:
                success = False

    return success, failed_packages



def setup_neurpi(server=False, rig=False, dev=False, full=False, python_version="3.9.13"):
    """Set up NeuRPi development environment with selective dependency installation."""

    # First, ensure essential dependencies are installed
    ensure_essential_dependencies()

    # Now we can safely import
    from rich.console import Console
    console = Console()

    # Check for uv availability
    uv_executable = check_uv_available()
    use_uv = uv_executable is not None

    if use_uv:
        console.print("[green]✓ Using uv package manager[/green]")
    else:
        console.print("[yellow]Using pip package manager[/yellow]")

    # Determine which dependency groups to install
    dependency_groups = []

    # If no flags specified, default to full installation
    if not any([server, rig, dev, full]):
        full = True

    if server:
        dependency_groups = ['core', 'gui']
        console.print("[bold blue]Setting up NeuRPi with GUI dependencies...[/bold blue]")
    elif rig:
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
            if use_uv:
                subprocess.run([uv_executable, "venv", str(venv_path), "--python", python_version], check=True)
            else:
                subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            console.print("[green]✓ Virtual environment created[/green]")
        else:
            console.print("[yellow]Virtual environment already exists[/yellow]")

        # Step 2: Determine python executable path
        python_exe = venv_path / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

        # Step 2.5: Ensure pip is available in the virtual environment
        if not use_uv:
            console.print("[green]Ensuring pip is available in virtual environment...[/green]")
            try:
                subprocess.run([str(python_exe), "-m", "ensurepip", "--upgrade"],
                             check=True, capture_output=True, text=True)
                console.print("[green]✓ pip is available[/green]")
            except subprocess.CalledProcessError:
                console.print("[yellow]Warning: Could not ensure pip availability[/yellow]")

        # Step 3: Install selected dependency groups
        console.print("[green]Installing selected dependencies...[/green]")

        all_failed_packages = []

        for group in dependency_groups:
            console.print(f"Installing {group} dependencies...")
            success, failed_packages = install_dependencies(python_exe, group, use_uv, uv_executable)
            all_failed_packages.extend(failed_packages)
            if not success and group == 'core':
                console.print(f"[red]Critical failure installing {group} dependencies[/red]")

        # Step 4: Install the package in editable mode
        console.print("[green]Installing NeuRPi in editable mode...[/green]")
        editable_installed = False

        # Try with uv first if available
        if use_uv and uv_executable:
            try:
                subprocess.run([uv_executable, "pip", "install", "-e", str(project_root), "--python", str(python_exe)],
                             check=True, capture_output=True, text=True)
                console.print("[green]✓ NeuRPi installed in editable mode with uv[/green]")
                editable_installed = True
            except subprocess.CalledProcessError:
                console.print("[yellow]uv editable install failed, trying with pip...[/yellow]")

        # Fallback to pip if uv failed or not available
        if not editable_installed:
            try:
                subprocess.run([str(python_exe), "-m", "pip", "install", "-e", str(project_root)],
                             check=True, capture_output=True, text=True)
                console.print("[green]✓ NeuRPi installed in editable mode with pip[/green]")
                editable_installed = True
            except subprocess.CalledProcessError as e:
                console.print(f"[yellow]Warning: Failed to install NeuRPi in editable mode: {e}[/yellow]")
                console.print("[cyan]This might be due to deprecated setup.py. Consider using modern packaging.[/cyan]")

                # Last attempt with uv and force options
                if use_uv and uv_executable:
                    try:
                        console.print("[yellow]Trying uv with force-reinstall...[/yellow]")
                        subprocess.run([uv_executable, "pip", "install", "-e", str(project_root),
                                      "--python", str(python_exe), "--force-reinstall"],
                                     check=True, capture_output=True, text=True)
                        console.print("[green]✓ NeuRPi installed in editable mode with uv (force-reinstall)[/green]")
                        editable_installed = True
                    except subprocess.CalledProcessError:
                        console.print("[red]All installation methods failed for editable mode[/red]")

        # Step 5: Success message and create executable script
        console.print("\n[bold green]✓ Setup completed![/bold green]")
        console.print(f"[green]✓ Installed dependency groups: {', '.join(dependency_groups)}[/green]")

        if all_failed_packages:
            unique_failed = list(set(all_failed_packages))
            console.print(f"\n[yellow]⚠️  Some dependencies failed to install ({len(unique_failed)} packages):[/yellow]")
            for pkg in unique_failed:
                console.print(f"[red]  • {pkg}[/red]")
            console.print("\n[cyan]💡 You can try to install failed packages manually using:[/cyan]")
            console.print(f"[cyan]   uv pip install {' '.join(unique_failed)} --python .venv/bin/python[/cyan]")
            console.print("[cyan]   OR[/cyan]")
            console.print(f"[cyan]   .venv/bin/python -m pip install {' '.join(unique_failed)}[/cyan]")

        console.print("\n[bold blue]To activate the virtual environment:[/bold blue]")
        if platform.system() == "Windows":
            console.print("[cyan]  .venv\\Scripts\\activate[/cyan]")
        else:
            console.print("[cyan]  source .venv/bin/activate[/cyan]")

        console.print("[blue]📝 Creating executable script...[/blue]")
        create_executable_script(project_root, venv_path)

        console.print("\n[green]🎉 Setup completed![/green]")
        if editable_installed:
            console.print("[green]✅ NeuRPi is ready to use![/green]")
        else:
            console.print("[yellow]⚠️  Setup completed but editable install failed[/yellow]")
        console.print(f"[green]✅ Installed: {', '.join(dependency_groups)}[/green]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Setup failed: {e}[/red]")
        sys.exit(1)
    except (ImportError, FileNotFoundError) as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


# Create the setup command for CLI integration
ensure_essential_dependencies()

try:
    import click
except ImportError:
    print("Click not available. Please install it first.")
    sys.exit(1)


@click.command()
@click.option('--server', is_flag=True, help='Install core + GUI dependencies')
@click.option('--rig', is_flag=True, help='Install code + hardwar dependencies')
@click.option('--dev', is_flag=True, help='Install core + development dependencies')
@click.option('--full', is_flag=True, help='Install all dependencies (default)')
@click.option('--python-version', default='3.9.13', help='Python version to use (default: 3.9.13)')
def setup_cli(server, rig, dev, full, python_version):
    """Set up NeuRPi development environment with selective dependency installation."""
    setup_neurpi(server=server, rig=rig, dev=dev, full=full, python_version=python_version)


if __name__ == "__main__":
    try:
        setup_cli()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
