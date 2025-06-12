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
        try:
            result = subprocess.run(
                [uv_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            return uv_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
    return None


def read_requirements_from_toml(group_name):
    """Read requirements from pyproject.toml file."""
    project_root = Path(__file__).parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        print("Error: pyproject.toml not found.")
        return []

    try:
        # Try to import tomllib (Python 3.11+) or tomli
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        project_config = config.get("project", {})

        if group_name == "core":
            return project_config.get("dependencies", [])

        optional_deps = project_config.get("optional-dependencies", {})
        return optional_deps.get(group_name, [])

    except (OSError, TypeError, KeyError) as e:
        print(f"Error reading pyproject.toml: {e}")
        return []


def ensure_essential_dependencies():
    """Ensure essential dependencies are available."""
    missing = []

    # Check for tomli/tomllib availability (needed for TOML parsing)
    try:
        try:
            import tomllib  # noqa: F401
        except ImportError:
            import tomli  # noqa: F401
    except ImportError:
        missing.append("tomli>=1.2.0")

    # Check for click and rich availability
    try:
        import click  # noqa: F401
    except ImportError:
        missing.append("click>=8.0.0")

    try:
        import rich  # noqa: F401
    except ImportError:
        missing.append("rich>=13.0.0")

    if missing:
        print(f"Installing essential dependencies: {', '.join(missing)}")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install"] + missing,
                check=True,
                capture_output=True,
                text=True,
            )
            print("✓ Essential dependencies installed")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install essential dependencies: {e}")
            sys.exit(1)


def create_executable_script(project_root, venv_path):
    """Create platform-specific executable script."""
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
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        # Make the script executable on Unix/Linux
        if platform.system() != "Windows":
            script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

        console.print(f"[green]✓ Created executable script: {script_name}[/green]")
        console.print(f"[blue]Run NeuRPi using: ./{script_name} [command] [options][/blue]")

    except OSError as e:
        console.print(f"[red]Warning: Failed to create executable script: {e}[/red]")


def create_virtual_environment(venv_path, python_version, use_uv=False, uv_executable=None):
    """Create virtual environment using uv or venv."""
    if venv_path.exists():
        print("Virtual environment already exists")
        return True

    print(f"Creating virtual environment with Python {python_version}...")

    try:
        if use_uv and uv_executable:
            subprocess.run(
                [uv_executable, "venv", str(venv_path), "--python", python_version],
                check=True,
                capture_output=True,
                text=True,
            )
        else:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        print("✓ Virtual environment created")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create virtual environment: {e}")
        return False


def ensure_pip_in_venv(python_exe):
    """Ensure pip is available in the virtual environment."""
    print("Ensuring pip is available in virtual environment...")

    # Determine the expected pip executable path
    venv_path = python_exe.parent.parent
    if platform.system() == "Windows":
        pip_exe = venv_path / "Scripts" / "pip.exe"
    else:
        pip_exe = venv_path / "bin" / "pip"

    try:
        # First check if pip is already available via python -m pip
        subprocess.run(
            [str(python_exe), "-m", "pip", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ pip module is available")

        # Check if pip executable exists
        if pip_exe.exists():
            print("✓ pip executable exists")
            return True
        else:
            print("⚠️ pip module available but executable missing")

    except subprocess.CalledProcessError:
        print("pip module not available, installing...")

    # Try to ensure pip using ensurepip
    try:
        subprocess.run(
            [str(python_exe), "-m", "ensurepip", "--upgrade"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ pip installed using ensurepip")        # Verify pip executable was created
        if pip_exe.exists():
            print("✓ pip executable created successfully")
            return True
        else:
            print("⚠️ pip installed but executable still missing")

            # Try to create pip executable manually
            print("Attempting to create pip executable...")
            try:
                # Install pip again to force creation of executables
                subprocess.run(
                    [str(python_exe), "-m", "pip", "install", "--force-reinstall", "pip"],
                    check=True,
                    capture_output=True,
                    text=True,                )

                if pip_exe.exists():
                    print("✓ pip executable created after force-reinstall")
                    return True
                else:
                    print("⚠️ pip executable still missing after force-reinstall")
                    # Create a pip wrapper script as fallback
                    print("Creating pip wrapper script as fallback...")
                    create_pip_wrapper(venv_path, python_exe)

            except subprocess.CalledProcessError as reinstall_error:
                print(f"Force-reinstall failed: {reinstall_error}")
                # Still try to create wrapper as fallback
                if not pip_exe.exists():
                    print("Creating pip wrapper script as fallback...")
                    create_pip_wrapper(venv_path, python_exe)

    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not ensure pip availability: {e}")

    # Final check: if pip module works, that's sufficient for our purposes
    try:
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ pip module is working (executable may be missing but module works)")
        return True
    except subprocess.CalledProcessError:
        # Try alternative method: install pip directly
        try:
            print("Trying to install pip directly...")
            subprocess.run(
                [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"],
                check=True,
                capture_output=True,
                text=True,
            )
            print("✓ pip upgraded successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ All pip installation methods failed")
            print("Note: You can still use 'python -m pip' instead of 'pip' command")
            return False

    return True


def install_dependencies(python_exe, group_name, use_uv=False, uv_executable=None):
    """Install dependencies from a dependency group."""
    requirements = read_requirements_from_toml(group_name)
    if not requirements:
        print(f"No requirements found for group '{group_name}'")
        return True, []

    print(f"Installing {group_name} dependencies...")
    failed_packages = []

    for dep in requirements:
        installed = False

        # Try with uv first if available
        if use_uv and uv_executable:
            try:
                subprocess.run(
                    [uv_executable, "pip", "install", dep, "--python", str(python_exe)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                print(f"✓ {dep} installed with uv")
                installed = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass

        # Fallback to pip if uv failed or not available
        if not installed:
            try:
                subprocess.run(
                    [str(python_exe), "-m", "pip", "install", dep],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                print(f"✓ {dep} installed with pip")
                installed = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass

        if not installed:
            print(f"⚠️ Failed to install {dep}")
            failed_packages.append(dep)

    success = len(failed_packages) == 0
    return success, failed_packages


def setup_neurpi(controller=False, rig=False, dev=False, full=False, python_version="3.11"):
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
    if not any([controller, rig, dev, full]):
        full = True

    if controller:
        dependency_groups = ["core", "gui"]
        console.print("[bold blue]Setting up NeuRPi with GUI dependencies...[/bold blue]")
    elif rig:
        dependency_groups = ["core", "hardware"]
        console.print("[bold blue]Setting up NeuRPi with HARDWARE dependencies...[/bold blue]")
    elif dev:
        dependency_groups = ["core", "dev"]
        console.print("[bold blue]Setting up NeuRPi with DEVELOPMENT dependencies...[/bold blue]")
    elif full:
        dependency_groups = ["core", "gui", "hardware", "dev"]
        console.print("[bold blue]Setting up NeuRPi with FULL dependencies...[/bold blue]")

    console.print(f"[cyan]Installing dependency groups: {', '.join(dependency_groups)}[/cyan]")
    console.print(f"[cyan]Using Python version: {python_version}[/cyan]")

    project_root = Path(__file__).parent.parent.parent
    venv_path = project_root / ".venv"

    try:
        # Step 1: Create virtual environment
        if not create_virtual_environment(venv_path, python_version, use_uv, uv_executable):
            console.print("[red]Failed to create virtual environment[/red]")
            sys.exit(1)        # Step 2: Determine python executable path
        python_exe = venv_path / (
            "Scripts/python.exe" if platform.system() == "Windows" else "bin/python"
        )

        # Step 3: Fix virtual environment activation scripts
        console.print("[blue]Fixing virtual environment activation...[/blue]")
        fix_venv_activation(venv_path)

        # Step 4: Ensure pip is available in the virtual environment
        if not ensure_pip_in_venv(python_exe):
            console.print("[yellow]Warning: pip may not be fully available in venv[/yellow]")        # Step 5: Install selected dependency groups
        console.print("[green]Installing selected dependencies...[/green]")
        all_failed_packages = []

        for group in dependency_groups:
            success, failed_packages = install_dependencies(
                python_exe, group, use_uv, uv_executable
            )
            all_failed_packages.extend(failed_packages)        # Step 6: Install the package in editable mode
        console.print("[green]Installing NeuRPi in editable mode...[/green]")
        editable_installed = False

        # Try with uv first if available
        if use_uv and uv_executable:
            try:
                subprocess.run(
                    [uv_executable, "pip", "install", "-e", str(project_root), "--python", str(python_exe)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                console.print("[green]✓ NeuRPi installed in editable mode with uv[/green]")
                editable_installed = True
            except subprocess.CalledProcessError:
                console.print("[yellow]uv editable install failed, trying with pip...[/yellow]")

        # Fallback to pip if uv failed or not available
        if not editable_installed:
            try:
                subprocess.run(
                    [str(python_exe), "-m", "pip", "install", "-e", str(project_root)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                console.print("[green]✓ NeuRPi installed in editable mode with pip[/green]")
                editable_installed = True
            except subprocess.CalledProcessError as e:
                console.print(f"[red]Failed to install NeuRPi in editable mode: {e}[/red]")        # Step 7: Create executable script
        console.print("[blue]📝 Creating executable script...[/blue]")
        create_executable_script(project_root, venv_path)        # Step 8: Summary
        console.print("\n[bold green]✓ Setup completed![/bold green]")

        if all_failed_packages:
            unique_failed = list(set(all_failed_packages))
            console.print(f"\n[yellow]⚠️ Some dependencies failed to install ({len(unique_failed)} packages):[/yellow]")
            for pkg in unique_failed:
                console.print(f"[red]  • {pkg}[/red]")

            console.print("\n[cyan]💡 You can try to install failed packages manually:[/cyan]")
            if platform.system() == "Windows":
                console.print(f"[cyan]   .venv\\Scripts\\python -m pip install {' '.join(unique_failed)}[/cyan]")
            else:
                console.print(f"[cyan]   .venv/bin/python -m pip install {' '.join(unique_failed)}[/cyan]")

        console.print("\n[bold blue]To activate the virtual environment:[/bold blue]")
        if platform.system() == "Windows":
            console.print("[cyan]  .venv\\Scripts\\activate[/cyan]")
            console.print("\n[bold blue]After activation, verify pip points to venv:[/bold blue]")
            console.print("[cyan]  where pip  # Should show .venv\\Scripts\\pip.exe[/cyan]")
            console.print("[cyan]  where python  # Should show .venv\\Scripts\\python.exe first[/cyan]")
        else:
            console.print("[cyan]  source .venv/bin/activate[/cyan]")
            console.print("\n[bold blue]After activation, verify pip points to venv:[/bold blue]")
            console.print("[cyan]  which pip  # Should show .venv/bin/pip[/cyan]")
            console.print("[cyan]  which python  # Should show .venv/bin/python[/cyan]")

        console.print("\n[bold blue]If pip still points to global installation:[/bold blue]")
        console.print("[cyan]  deactivate && .venv\\Scripts\\activate  # Re-activate on Windows[/cyan]")
        console.print("[cyan]  Or use: .venv\\Scripts\\python -m pip instead of pip[/cyan]")

        if editable_installed:
            console.print("[green]🎉 NeuRPi is ready to use![/green]")
        else:
            console.print("[yellow]⚠️ Setup completed but editable install failed[/yellow]")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Setup failed: {e}[/red]")
        sys.exit(1)
    except (ImportError, FileNotFoundError) as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


def fix_venv_activation(venv_path):
    """Fix virtual environment activation scripts to ensure proper PATH setup."""
    if platform.system() == "Windows":
        activate_script = venv_path / "Scripts" / "activate.bat"

        if not activate_script.exists():
            print("⚠️ activate.bat not found in virtual environment")
            return False

        try:
            # Read the current activation script
            with open(activate_script, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if the script properly sets up the PATH
            scripts_path = str(venv_path / "Scripts")

            if scripts_path not in content:
                print("Fixing PATH in activation script...")

                # Add proper PATH setup at the beginning
                path_fix = f"""@echo off
if defined _OLD_VIRTUAL_PATH (
    set "PATH=%_OLD_VIRTUAL_PATH%"
) else (
    set "_OLD_VIRTUAL_PATH=%PATH%"
)
set "PATH={scripts_path};%PATH%"
set "VIRTUAL_ENV={venv_path}"

"""
                # Write the fixed script
                with open(activate_script, 'w', encoding='utf-8') as f:
                    f.write(path_fix + content)

                print("✓ Virtual environment activation script fixed")
                return True
            else:
                print("✓ Virtual environment activation script is properly configured")
                return True

        except (OSError, UnicodeDecodeError) as e:
            print(f"⚠️ Could not fix activation script: {e}")
            return False

    else:
        # Unix/Linux activation script fix
        activate_script = venv_path / "bin" / "activate"

        if not activate_script.exists():
            print("⚠️ activate script not found in virtual environment")
            return False

        print("✓ Unix activation script should work correctly")
        return True


def create_pip_wrapper(venv_path, python_exe):
    """Create a pip wrapper script when pip.exe is missing."""
    if platform.system() == "Windows":
        pip_wrapper = venv_path / "Scripts" / "pip.bat"
        wrapper_content = f'''@echo off
"{python_exe}" -m pip %*
'''
        try:
            with open(pip_wrapper, 'w', encoding='utf-8') as f:
                f.write(wrapper_content)
            print(f"✓ Created pip wrapper: {pip_wrapper}")
            return True
        except OSError as e:
            print(f"Failed to create pip wrapper: {e}")
            return False
    else:
        pip_wrapper = venv_path / "bin" / "pip"
        wrapper_content = f'''#!/bin/bash
"{python_exe}" -m pip "$@"
'''
        try:
            with open(pip_wrapper, 'w', encoding='utf-8') as f:
                f.write(wrapper_content)
            pip_wrapper.chmod(0o755)  # Make executable
            print(f"✓ Created pip wrapper: {pip_wrapper}")
            return True
        except OSError as e:
            print(f"Failed to create pip wrapper: {e}")
            return False


# Create the setup command for CLI integration
ensure_essential_dependencies()

# Now we can safely import click since it's been verified
import click


def main():
    """Main entry point for the neurpi-setup command."""
    setup_cli()


@click.command()
@click.option("--controller", is_flag=True, help="Install core + GUI dependencies")
@click.option("--rig", is_flag=True, help="Install core + hardware dependencies")
@click.option("--dev", is_flag=True, help="Install core + development dependencies")
@click.option("--full", is_flag=True, help="Install all dependencies (default)")
@click.option("--python-version", default="3.11", help="Python version to use (default: 3.11)")
def setup_cli(controller, rig, dev, full, python_version):
    """Set up NeuRPi development environment with selective dependency installation."""
    setup_neurpi(
        controller=controller,
        rig=rig,
        dev=dev,
        full=full,
        python_version=python_version,
    )


if __name__ == "__main__":
    try:
        setup_cli()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
