#!/usr/bin/env python3

import platform
import subprocess
import sys
from pathlib import Path

# Function to find uv executable path
def find_uv_executable():
    """Find the path to the uv executable."""
    import shutil
    import os
    
    # First try to find uv in PATH
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path
    
    # If not in PATH, look in common installation locations
    possible_locations = []
    
    if platform.system() == "Windows":
        # Current Python's Scripts directory
        scripts_dir = Path(sys.executable).parent / "Scripts"
        possible_locations.append(scripts_dir / "uv.exe")
        
        # User's AppData Scripts directory (common pip install location)
        if os.environ.get('APPDATA'):
            appdata_scripts = Path(os.environ['APPDATA']).parent / "Local" / "Programs" / "Python" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "Scripts"
            possible_locations.append(appdata_scripts / "uv.exe")
        
        # Check if we're in a virtual environment and look in the base Python
        if hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix:
            base_scripts = Path(sys.base_prefix) / "Scripts"
            possible_locations.append(base_scripts / "uv.exe")
            
        # Also check current working directory Scripts (sometimes pip installs here)
        cwd_scripts = Path.cwd() / "Scripts"
        possible_locations.append(cwd_scripts / "uv.exe")
        
    else:
        # Unix-like systems
        bin_dir = Path(sys.executable).parent / "bin"
        possible_locations.append(bin_dir / "uv")
        
        # Check user local bin
        home = Path.home()
        possible_locations.append(home / ".local" / "bin" / "uv")
    
    # Check each possible location
    for location in possible_locations:
        if location.exists():
            return str(location)
    
    return None

# Function to install uv and required packages for this script
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
        result = subprocess.run([sys.executable, "-m", "pip", "install", "uv"],
                     check=True, capture_output=True, text=True)
        print("✓ uv installed successfully")
        
        # Try to find the newly installed uv again
        uv_path = find_uv_executable()
        if uv_path:
            print(f"✓ Found uv at: {uv_path}")
            return uv_path
        
        # If still not found, try to use pip show to find where it was installed
        try:
            show_result = subprocess.run([sys.executable, "-m", "pip", "show", "-f", "uv"], 
                                       capture_output=True, text=True, check=True)
            print("uv installation details:")
            print(show_result.stdout)
            
            # Extract installation location from pip show output
            for line in show_result.stdout.split('\n'):
                if line.startswith('Location:'):
                    location = line.split(':', 1)[1].strip()
                    # Try to construct the path to the executable
                    if platform.system() == "Windows":
                        scripts_path = Path(location).parent / "Scripts" / "uv.exe"
                        if scripts_path.exists():
                            print(f"✓ Found uv executable at: {scripts_path}")
                            return str(scripts_path)
        except subprocess.CalledProcessError:
            pass
        
        print("Warning: uv installed but executable not found in expected locations")
        print("Attempting to use 'uv' command directly...")
        return "uv"  # fallback to command name
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to install uv: {e}")
        print("Please install manually with: pip install uv")
        sys.exit(1)
    
    # Now install script dependencies using regular pip for the setup script itself
    required_packages = ['click', 'rich']
    for package in required_packages:
        try:
            __import__(package)
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

import click
from rich.console import Console

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

console = Console()


def create_launcher(project_root, python_exe):
    """Create OS-specific launcher file for running neurpi commands."""
    try:
        if platform.system() == "Windows":
            # Create neurpi.bat for Windows
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
            # Create neurpi shell script for Unix-like systems (Linux/macOS)
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
            
            # Make the shell script executable
            import stat
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


@click.command()
def setup():
    """Set up NeuRPi development environment with uv and Python 3.9.13."""
    console.print("[bold blue]Setting up NeuRPi development environment with uv and Python 3.9.13...[/bold blue]")
    
    # Install uv and script dependencies first, and get uv path
    uv_executable = install_uv_and_dependencies()

    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        console.print("[yellow]Warning: Already in a virtual environment. Continuing...[/yellow]")

    venv_path = project_root / ".venv"
    use_uv = True  # Track whether we can use uv

    try:
        # Step 1: Create virtual environment with Python 3.9.13 using uv
        if not venv_path.exists():
            console.print("[green]Creating virtual environment with Python 3.9.13 using uv...[/green]")
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
        else:
            console.print("[yellow]Virtual environment already exists[/yellow]")

        # Step 2: Determine python executable path based on OS
        if platform.system() == "Windows":
            python_exe = venv_path / "Scripts" / "python.exe"
        else:
            python_exe = venv_path / "bin" / "python"

        # Step 3: Verify Python version
        console.print("[green]Verifying Python version...[/green]")
        try:
            result = subprocess.run([str(python_exe), "--version"], capture_output=True, text=True, check=True)
            python_version = result.stdout.strip()
            console.print(f"[green]✓ Using {python_version}[/green]")
            
            # Check if it's Python 3.9.x
            if "Python 3.9" not in python_version:
                console.print(f"[yellow]Warning: Expected Python 3.9.x, got {python_version}[/yellow]")
        except subprocess.CalledProcessError:
            console.print("[red]Could not verify Python version[/red]")

        # Step 4: Install dependencies using uv
        console.print("[green]Installing dependencies with uv...[/green]")

        # Install all dependencies using uv pip
        core_deps = [
            "numpy>=1.24.0",
            "click>=8.0.0", 
            "rich>=13.0.0",
            "omegaconf>=2.2.2",
            "pyserial>=3.5",
            "pyzmq>=25.0.0",
            "tornado>=6.0.0",
            "h5py>=3.8.0",
            "blosc2>=2.0.0",
            "sounddevice>=0.4.6",
            "tables>=3.8.0",
            "pyyaml>=6.0.0",
            "scipy>=1.10.0",
            "pandas>=2.0.0"        ]

        # Install core dependencies individually for better error handling
        if use_uv:
            console.print("Installing core dependencies with uv...")
        else:
            console.print("Installing core dependencies with pip...")
        pandas_success = True
        
        for dep in core_deps:
            try:
                console.print(f"Installing {dep}...")
                if use_uv:
                    subprocess.run([uv_executable, "pip", "install", dep, "--python", str(python_exe)], check=True)
                else:
                    subprocess.run([str(python_exe), "-m", "pip", "install", dep], check=True)
                console.print(f"[green]✓ {dep} installed[/green]")
            except (subprocess.CalledProcessError, FileNotFoundError):
                console.print(f"[yellow]Warning: Failed to install {dep}[/yellow]")
                if "pandas" in dep:
                    pandas_success = False

        if not pandas_success:
            console.print("[yellow]Warning: Could not install pandas automatically.[/yellow]")
            console.print("[yellow]You may need to install Microsoft Visual Studio Build Tools[/yellow]")
            console.print("[yellow]or install pandas manually after setup completes.[/yellow]")
            console.print("[cyan]Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/[/cyan]")        # Install GUI dependencies
        if use_uv:
            console.print("Installing GUI dependencies with uv...")
        else:
            console.print("Installing GUI dependencies with pip...")
        gui_deps = [
            "matplotlib>=3.7.0",
            "pygame>=2.1.2",
            "pyqtgraph>=0.13.0",
            "opencv-python>=4.8.0",
            "PyQt5>=5.15.0",
            "pyqt5-tools>=5.15.1.2",
            "sip>=6.0.0"
        ]

        gui_failed = []
        for dep in gui_deps:
            try:
                console.print(f"Installing {dep}...")
                if use_uv:
                    subprocess.run([uv_executable, "pip", "install", dep, "--python", str(python_exe)], check=True)
                else:
                    subprocess.run([str(python_exe), "-m", "pip", "install", dep], check=True)
                console.print(f"[green]✓ {dep} installed[/green]")
            except (subprocess.CalledProcessError, FileNotFoundError):
                console.print(f"[yellow]Warning: Failed to install {dep}[/yellow]")
                gui_failed.append(dep)

        if gui_failed:
            console.print(f"[yellow]Some GUI dependencies failed: {', '.join(gui_failed)}[/yellow]")
            console.print("[yellow]You may need to install them manually later[/yellow]")        # Step 5: Install the package in editable mode
        if use_uv:
            console.print("[green]Installing NeuRPi in editable mode with uv...[/green]")
        else:
            console.print("[green]Installing NeuRPi in editable mode with pip...[/green]")
        try:
            if use_uv:
                subprocess.run([uv_executable, "pip", "install", "-e", str(project_root), "--python", str(python_exe)], check=True)
            else:
                subprocess.run([str(python_exe), "-m", "pip", "install", "-e", str(project_root)], check=True)
            console.print("[green]✓ NeuRPi installed in editable mode[/green]")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            console.print(f"[yellow]Warning: Failed to install NeuRPi in editable mode: {e}[/yellow]")
            if use_uv:
                console.print("[yellow]You may need to install it manually with: uv pip install -e . --python .venv/Scripts/python.exe[/yellow]")
            else:
                console.print("[yellow]You may need to install it manually with: .venv/Scripts/python.exe -m pip install -e .[/yellow]")

        # Step 6: Create OS-specific launcher
        console.print("[green]Creating OS-specific launcher...[/green]")
        create_launcher(project_root, python_exe)

        # Step 7: Create module entry point (__main__.py)
        console.print("[green]Creating module entry point...[/green]")
        create_main_module(project_root)        # Step 8: Success message with instructions
        if use_uv:
            console.print("\n[bold green]✓ Setup completed with uv![/bold green]")
        else:
            console.print("\n[bold green]✓ Setup completed with pip![/bold green]")

        if not pandas_success or gui_failed:
            console.print("\n[yellow]Note: Some optional dependencies may have failed to install:[/yellow]")
            if not pandas_success:
                console.print("[yellow]  - pandas (data processing)[/yellow]")
            if gui_failed:
                console.print(f"[yellow]  - {', '.join(gui_failed)} (GUI components)[/yellow]")
            console.print("[yellow]The core system should still work for basic functionality.[/yellow]")

        console.print("\n[bold blue]To activate the virtual environment:[/bold blue]")
        if platform.system() == "Windows":
            console.print(f"[cyan]  .venv\\Scripts\\activate[/cyan]")
        else:
            console.print(f"[cyan]  source .venv/bin/activate[/cyan]")

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

        if use_uv:
            console.print("\n[bold blue]Using uv commands:[/bold blue]")
            if platform.system() == "Windows":
                console.print("[cyan]  uv pip list --python .venv\\Scripts\\python.exe  # List installed packages[/cyan]")
                console.print("[cyan]  uv pip install <package> --python .venv\\Scripts\\python.exe  # Install additional packages[/cyan]")
            else:
                console.print("[cyan]  uv pip list --python .venv/bin/python  # List installed packages[/cyan]")
                console.print("[cyan]  uv pip install <package> --python .venv/bin/python  # Install additional packages[/cyan]")
        else:
            console.print("\n[bold blue]Using pip commands:[/bold blue]")
            if platform.system() == "Windows":
                console.print("[cyan]  .venv\\Scripts\\python.exe -m pip list  # List installed packages[/cyan]")
                console.print("[cyan]  .venv\\Scripts\\python.exe -m pip install <package>  # Install additional packages[/cyan]")
            else:
                console.print("[cyan]  .venv/bin/python -m pip list  # List installed packages[/cyan]")
                console.print("[cyan]  .venv/bin/python -m pip install <package>  # Install additional packages[/cyan]")

        if not pandas_success or gui_failed:
            if use_uv:
                console.print("\n[bold blue]To install missing dependencies later with uv:[/bold blue]")
                if not pandas_success:
                    if platform.system() == "Windows":
                        console.print("[cyan]  uv pip install pandas --python .venv\\Scripts\\python.exe  # For data processing[/cyan]")
                    else:
                        console.print("[cyan]  uv pip install pandas --python .venv/bin/python  # For data processing[/cyan]")
                if gui_failed:
                    if platform.system() == "Windows":
                        console.print("[cyan]  uv pip install matplotlib PyQt5 opencv-python --python .venv\\Scripts\\python.exe  # For GUI[/cyan]")
                    else:
                        console.print("[cyan]  uv pip install matplotlib PyQt5 opencv-python --python .venv/bin/python  # For GUI[/cyan]")
            else:
                console.print("\n[bold blue]To install missing dependencies later with pip:[/bold blue]")
                if not pandas_success:
                    if platform.system() == "Windows":
                        console.print("[cyan]  .venv\\Scripts\\python.exe -m pip install pandas  # For data processing[/cyan]")
                    else:
                        console.print("[cyan]  .venv/bin/python -m pip install pandas  # For data processing[/cyan]")
                if gui_failed:
                    if platform.system() == "Windows":
                        console.print("[cyan]  .venv\\Scripts\\python.exe -m pip install matplotlib PyQt5 opencv-python  # For GUI[/cyan]")
                    else:
                        console.print("[cyan]  .venv/bin/python -m pip install matplotlib PyQt5 opencv-python  # For GUI[/cyan]")

    except subprocess.CalledProcessError as e:
        # Only exit on critical failures (like venv creation)
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
