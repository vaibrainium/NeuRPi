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





def find_uv_executable():
    """Find the path to the uv executable."""
    # First try to find uv in PATH
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path

    # If not in PATH, look in common installation locations
    possible_locations = []

    if platform.system() == "Windows":
        # Current Python's Scripts directory
        scripts_dir = Path(sys.executable).parent / "Scripts"
        possible_locations.extend([
            scripts_dir / "uv.exe",
            Path.cwd() / "Scripts" / "uv.exe"
        ])

        # User's AppData Scripts directory (common pip install location)
        if os.environ.get('APPDATA'):
            appdata_scripts = Path(os.environ['APPDATA']).parent / "Local" / "Programs" / "Python" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "Scripts"
            possible_locations.append(appdata_scripts / "uv.exe")

        # Check if we're in a virtual environment and look in the base Python
        if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
            base_scripts = Path(sys.base_prefix) / "Scripts"
            possible_locations.append(base_scripts / "uv.exe")
    else:
        # Unix-like systems
        bin_dir = Path(sys.executable).parent / "bin"
        home = Path.home()
        possible_locations.extend([
            bin_dir / "uv",
            home / ".local" / "bin" / "uv"
        ])

    # Check each possible location
    for location in possible_locations:
        if location.exists():
            return str(location)

    return None


def install_uv_and_dependencies():
    """Install uv package manager and packages needed to run this setup script."""
    # First check if uv is available
    uv_path = find_uv_executable()
    if uv_path:
        try:
            subprocess.run([uv_path, "--version"], check=True, capture_output=True)
            print("✓ uv is already installed")
            return uv_path
        except subprocess.CalledProcessError:
            pass

    print("Installing uv package manager...")
    try:
        # Install uv using pip
        subprocess.run([sys.executable, "-m", "pip", "install", "uv"],
                      check=True, capture_output=True, text=True)
        print("✓ uv installed successfully")

        # Try to find the newly installed uv again
        uv_path = find_uv_executable()
        if uv_path:
            print(f"✓ Found uv at: {uv_path}")
            return uv_path

        print("Warning: uv installed but executable not found in expected locations")
        print("Attempting to use 'uv' command directly...")
        return "uv"  # fallback to command name

    except subprocess.CalledProcessError as e:
        print(f"Failed to install uv: {e}")
        print("Please install manually with: pip install uv")
        sys.exit(1)

    # Now install script dependencies using regular pip for the setup script itself
    # Use minimal hardcoded dependencies since this is a bootstrap script
    setup_requirements = ['click>=8.0.0', 'rich>=13.0.0']

    for package in setup_requirements:
        try:
            package_name = package.split('>=')[0].split('==')[0]
            __import__(package_name)
        except ImportError:
            print(f"Installing {package}...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", package],
                             check=True, capture_output=True, text=True)
                print(f"✓ {package} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"Failed to install {package}: {e}")
                print("Please install manually with: pip install click rich")
                sys.exit(1)


# Import after ensuring dependencies are available
try:
    import click
    from rich.console import Console
except ImportError:
    install_uv_and_dependencies()
    import click
    from rich.console import Console

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

console = Console()


def install_dependencies(python_exe, uv_executable, use_uv, group_name):
    """Install dependencies from a dependency group (core, gui, dev, hardware)."""
    # Remove .txt extension if present for backward compatibility
    if group_name.endswith('.txt'):
        group_name = group_name[:-4]

    requirements = read_requirements_from_toml(group_name)
    if not requirements:
        console.print(f"[yellow]No requirements found for group '{group_name}'[/yellow]")
        return True, []

    failed_packages = []
    success = True

    for dep in requirements:
        try:
            console.print(f"Installing {dep}...")
            if use_uv:
                subprocess.run([uv_executable, "pip", "install", dep, "--python", str(python_exe)],
                             check=True, capture_output=True)
            else:
                subprocess.run([str(python_exe), "-m", "pip", "install", dep],
                             check=True, capture_output=True)
            console.print(f"[green]✓ {dep} installed[/green]")
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print(f"[yellow]Warning: Failed to install {dep}[/yellow]")
            failed_packages.append(dep)
            if "pandas" in dep:
                success = False

    return success, failed_packages


def create_virtual_environment(venv_path, uv_executable):
    """Create virtual environment using uv or fallback to standard venv."""
    use_uv = True

    try:
        # Try to create venv with specific Python version using uv
        subprocess.run([uv_executable, "venv", str(venv_path), "--python", "3.9.13"], check=True)
        console.print("[green]✓ Virtual environment created with Python 3.9.13[/green]")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        if isinstance(e, FileNotFoundError):
            console.print(f"[yellow]uv executable not found at: {uv_executable}[/yellow]")
            console.print("[yellow]Falling back to standard Python venv...[/yellow]")
            use_uv = False
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            console.print("[green]✓ Virtual environment created with standard venv[/green]")
        else:
            console.print("[yellow]Python 3.9.13 not found, trying with available Python 3.9...[/yellow]")
            try:
                subprocess.run([uv_executable, "venv", str(venv_path), "--python", "3.9"], check=True)
                console.print("[green]✓ Virtual environment created with Python 3.9.x[/green]")
            except (subprocess.CalledProcessError, FileNotFoundError):
                console.print("[yellow]uv failed, falling back to standard venv...[/yellow]")
                use_uv = False
                subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
                console.print("[green]✓ Virtual environment created[/green]")

    return use_uv


def create_launcher(project_root, python_exe):
    """Create OS-specific launcher file for running neurpi commands."""
    try:
        if platform.system() == "Windows":
            launcher_file = project_root / "neurpi.bat"
            bat_content = f'''@echo off
REM NeuRPi Launcher for Windows
REM Automatically uses virtual environment Python

set "NEURPI_ROOT=%~dp0"
set "NEURPI_PYTHON={python_exe}"

if not exist "%NEURPI_PYTHON%" (
    echo Error: Virtual environment Python not found at %NEURPI_PYTHON%
    echo Please run setup first: python neurpi/cli/setup.py
    exit /b 1
)

"%NEURPI_PYTHON%" -m neurpi %*
'''
            with open(launcher_file, 'w') as f:
                f.write(bat_content)
            console.print(f"[green]✓ Created Windows launcher: {launcher_file.name}[/green]")
        else:
            launcher_file = project_root / "neurpi"
            shell_content = f'''#!/bin/bash
# NeuRPi Launcher for Unix-like systems
# Automatically uses virtual environment Python

NEURPI_ROOT="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
NEURPI_PYTHON="{python_exe}"

if [ ! -f "$NEURPI_PYTHON" ]; then
    echo "❌ Error: Virtual environment Python not found at $NEURPI_PYTHON"
    echo "🔧 Please run setup first: python neurpi/cli/setup.py"
    exit 1
fi

"$NEURPI_PYTHON" -m neurpi "$@"
'''
            with open(launcher_file, 'w') as f:
                f.write(shell_content)
            launcher_file.chmod(launcher_file.stat().st_mode | stat.S_IEXEC)
            console.print(f"[green]✓ Created Unix launcher: {launcher_file.name}[/green]")

    except Exception as e:
        console.print(f"[yellow]Warning: Failed to create launcher: {e}[/yellow]")


def create_main_module(project_root):
    """Create __main__.py file in neurpi package to enable 'python -m neurpi' execution."""
    try:
        neurpi_package = project_root / "neurpi"
        main_file = neurpi_package / "__main__.py"

        main_content = '''#!/usr/bin/env python3
"""
Entry point for running neurpi as a module: python -m neurpi
"""

if __name__ == "__main__":
    from neurpi.cli.main import main
    main()
'''
        with open(main_file, 'w') as f:
            f.write(main_content)
        console.print(f"[green]✓ Created module entry point: {main_file.name}[/green]")

    except Exception as e:
        console.print(f"[yellow]Warning: Failed to create __main__.py: {e}[/yellow]")


def print_success_instructions(use_uv, pandas_success, all_failed_packages, dependency_groups):
    """Print final success instructions."""
    if use_uv:
        console.print("\n[bold green]✓ Setup completed with uv![/bold green]")
    else:
        console.print("\n[bold green]✓ Setup completed with pip![/bold green]")
    
    console.print(f"[green]✓ Installed dependency groups: {', '.join(dependency_groups)}[/green]")

    if not pandas_success or all_failed_packages:
        console.print("\n[yellow]Note: Some optional dependencies may have failed to install:[/yellow]")
        if not pandas_success:
            console.print("[yellow]  - pandas (data processing)[/yellow]")
        if all_failed_packages:
            console.print(f"[yellow]  - {', '.join(set(all_failed_packages))}[/yellow]")
        console.print("[yellow]The core system should still work for basic functionality.[/yellow]")
    
    # Show available installation options
    console.print("\n[bold blue]To install additional dependency groups later:[/bold blue]")
    console.print("[cyan]  pip install \".[gui]\"       # Add GUI dependencies[/cyan]")
    console.print("[cyan]  pip install \".[hardware]\"  # Add hardware dependencies[/cyan]")
    console.print("[cyan]  pip install \".[dev]\"       # Add development tools[/cyan]")
    console.print("[cyan]  pip install \".[full]\"      # Install everything[/cyan]")

    console.print("\n[bold blue]To activate the virtual environment:[/bold blue]")
    if platform.system() == "Windows":
        console.print("[cyan]  .venv\\Scripts\\activate[/cyan]")
    else:
        console.print("[cyan]  source .venv/bin/activate[/cyan]")

    console.print("\n[bold blue]Or use the launcher (no need to activate venv):[/bold blue]")
    if platform.system() == "Windows":
        console.print("[cyan]  neurpi.bat terminal  # Start terminal agent[/cyan]")
        console.print("[cyan]  neurpi.bat pilot     # Start pilot agent[/cyan]")
        console.print("[cyan]  neurpi.bat status    # Check status[/cyan]")
    else:
        console.print("[cyan]  ./neurpi terminal    # Start terminal agent[/cyan]")
        console.print("[cyan]  ./neurpi pilot       # Start pilot agent[/cyan]")
        console.print("[cyan]  ./neurpi status      # Check status[/cyan]")

    console.print("\n[bold blue]Or with activated venv:[/bold blue]")
    console.print("[cyan]  neurpi terminal  # Start terminal agent[/cyan]")
    console.print("[cyan]  neurpi pilot     # Start pilot agent[/cyan]")
    console.print("[cyan]  neurpi status    # Check status[/cyan]")


@click.command()
@click.option('--minimal', is_flag=True, help='Install only core dependencies')
@click.option('--gui', is_flag=True, help='Install core + GUI dependencies')
@click.option('--hardware', is_flag=True, help='Install core + hardware dependencies')
@click.option('--dev', is_flag=True, help='Install core + development dependencies')
@click.option('--full', is_flag=True, help='Install all dependencies (default)')
@click.option('--python-version', default='3.9.13', help='Python version to use (default: 3.9.13)')
def setup(minimal, gui, hardware, dev, full, python_version):
    """Set up NeuRPi development environment with selective dependency installation."""
    
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

    # Install uv and script dependencies first, and get uv path
    uv_executable = install_uv_and_dependencies()

    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        console.print("[yellow]Warning: Already in a virtual environment. Continuing...[/yellow]")

    venv_path = project_root / ".venv"

    try:
        # Step 1: Create virtual environment with specified Python version using uv
        if not venv_path.exists():
            console.print(f"[green]Creating virtual environment with Python {python_version} using uv...[/green]")
            use_uv = create_virtual_environment(venv_path, uv_executable)
        else:
            console.print("[yellow]Virtual environment already exists[/yellow]")
            use_uv = True  # Assume uv works if we have an existing venv

        # Step 2: Determine python executable path based on OS
        python_exe = venv_path / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

        # Step 3: Verify Python version
        console.print("[green]Verifying Python version...[/green]")
        try:
            result = subprocess.run([str(python_exe), "--version"], capture_output=True, text=True, check=True)
            python_version = result.stdout.strip()
            console.print(f"[green]✓ Using {python_version}[/green]")

            if "Python 3.9" not in python_version:
                console.print(f"[yellow]Warning: Expected Python 3.9.x, got {python_version}[/yellow]")
        except subprocess.CalledProcessError:
            console.print("[red]Could not verify Python version[/red]")

        # Step 4: Install selected dependency groups
        console.print("[green]Installing selected dependencies...[/green]")
        
        all_failed_packages = []
        pandas_success = True
        
        for group in dependency_groups:
            console.print(f"Installing {group} dependencies...")
            success, failed_packages = install_dependencies(python_exe, uv_executable, use_uv, group)
            all_failed_packages.extend(failed_packages)
            
            # Special handling for pandas (often in core)
            if group == 'core' and not success:
                pandas_success = False
        
        # Report any installation issues
        if not pandas_success:
            console.print("[yellow]Warning: Could not install pandas automatically.[/yellow]")
            console.print("[yellow]You may need to install Microsoft Visual Studio Build Tools[/yellow]")
            console.print("[yellow]or install pandas manually after setup completes.[/yellow]")
            console.print("[cyan]Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/[/cyan]")

        if all_failed_packages:
            console.print(f"[yellow]Some dependencies failed: {', '.join(set(all_failed_packages))}[/yellow]")
            console.print("[yellow]You may need to install them manually later[/yellow]")

        # Step 5: Install the package in editable mode
        console.print(f"[green]Installing NeuRPi in editable mode with {'uv' if use_uv else 'pip'}...[/green]")
        try:
            if use_uv:
                subprocess.run([uv_executable, "pip", "install", "-e", str(project_root), "--python", str(python_exe)], check=True)
            else:
                subprocess.run([str(python_exe), "-m", "pip", "install", "-e", str(project_root)], check=True)
            console.print("[green]✓ NeuRPi installed in editable mode[/green]")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            console.print(f"[yellow]Warning: Failed to install NeuRPi in editable mode: {e}[/yellow]")

        # Step 6: Create OS-specific launcher
        console.print("[green]Creating OS-specific launcher...[/green]")
        create_launcher(project_root, python_exe)

        # Step 7: Create module entry point (__main__.py)
        console.print("[green]Creating module entry point...[/green]")
        create_main_module(project_root)

        # Step 8: Success message with instructions
        print_success_instructions(use_uv, pandas_success, all_failed_packages, dependency_groups)

    except subprocess.CalledProcessError as e:
        cmd_str = ' '.join(e.cmd) if hasattr(e, 'cmd') else 'unknown command'
        if "venv" in cmd_str:
            console.print(f"[red]Critical setup step failed with exit code {e.returncode}[/red]")
            console.print(f"[red]Command that failed: {cmd_str}[/red]")
            console.print("\n[yellow]Try running setup again, or install dependencies manually[/yellow]")
            sys.exit(1)
        else:
            console.print(f"[yellow]Warning: A non-critical step failed: {cmd_str}[/yellow]")
            console.print("[yellow]Continuing with setup...[/yellow]")
    except Exception as e:
        console.print(f"[red]Unexpected error during setup: {e}[/red]")
        console.print("[yellow]You may need to install dependencies manually[/yellow]")
        sys.exit(1)


def main():
    """Main entry point for the setup CLI."""
    try:
        setup()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
