#!/usr/bin/env python3

import platform
import subprocess
import sys
from pathlib import Path

# Function to install required packages for this script
def install_script_dependencies():
    """Install packages needed to run this setup script."""
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

# Install script dependencies first
install_script_dependencies()

import click
from rich.console import Console

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

console = Console()


@click.command()
def setup():
    """Set up NeuRPi development environment."""
    console.print("[bold blue]Setting up NeuRPi development environment...[/bold blue]")

    # Check if we're already in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        console.print("[yellow]Warning: Already in a virtual environment. Continuing...[/yellow]")

    venv_path = project_root / ".venv"

    try:
        # Step 1: Create virtual environment if it doesn't exist
        if not venv_path.exists():
            console.print("[green]Creating virtual environment at .venv...[/green]")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
            console.print("[green]✓ Virtual environment created[/green]")
        else:
            console.print("[yellow]Virtual environment already exists[/yellow]")

        # Step 2: Determine python executable path based on OS
        if platform.system() == "Windows":
            python_exe = venv_path / "Scripts" / "python.exe"
            pip_exe = venv_path / "Scripts" / "pip.exe"
        else:
            python_exe = venv_path / "bin" / "python"
            pip_exe = venv_path / "bin" / "pip"

        # Step 3: Upgrade pip
        console.print("[green]Upgrading pip...[/green]")
        subprocess.run([str(python_exe), "-m", "pip", "install", "--upgrade", "pip"], check=True)
        console.print("[green]✓ Pip upgraded[/green]")

        # Step 4: Install wheel and setuptools first
        console.print("[green]Installing build tools...[/green]")
        subprocess.run([str(pip_exe), "install", "--upgrade", "wheel", "setuptools"], check=True)
        console.print("[green]✓ Build tools installed[/green]")

        # Step 5: Install dependencies with pre-built wheels where possible
        console.print("[green]Installing dependencies...[/green]")

        # Install basic dependencies first
        basic_deps = [
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
            "pyyaml>=6.0.0"
        ]

        for dep in basic_deps:
            console.print(f"Installing {dep}...")
            subprocess.run([str(pip_exe), "install", dep], check=True)
          # Install scipy and pandas with specific versions that have wheels
        console.print("Installing scipy (this may take a moment)...")
        subprocess.run([str(pip_exe), "install", "scipy>=1.10.0"], check=True)

        # Try to install pandas with fallback options
        console.print("Installing pandas (this may take a moment)...")
        pandas_success = False

        # Try different approaches to install pandas
        pandas_options = [
            # First try with pre-built wheel
            ["install", "--only-binary=all", "pandas>=2.0.0"],
            # If that fails, try with a specific older version that has wheels
            ["install", "--only-binary=all", "pandas==2.2.3"],
            # As a last resort, try without build isolation
            ["install", "--no-build-isolation", "pandas>=2.0.0"],
        ]

        for i, options in enumerate(pandas_options):
            try:
                console.print(f"Trying pandas installation method {i+1}...")
                subprocess.run([str(pip_exe)] + options, check=True)
                pandas_success = True
                console.print("[green]✓ Pandas installed successfully[/green]")
                break
            except subprocess.CalledProcessError:
                if i < len(pandas_options) - 1:
                    console.print(f"[yellow]Method {i+1} failed, trying next approach...[/yellow]")
                else:
                    console.print("[red]All pandas installation methods failed[/red]")

        if not pandas_success:
            console.print("[yellow]Warning: Could not install pandas automatically.[/yellow]")
            console.print("[yellow]You may need to install Microsoft Visual Studio Build Tools[/yellow]")
            console.print("[yellow]or install pandas manually after setup completes.[/yellow]")
            console.print("[cyan]Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/[/cyan]")
          # Install GUI dependencies
        console.print("Installing GUI dependencies...")
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
                subprocess.run([str(pip_exe), "install", dep], check=True)
            except subprocess.CalledProcessError:
                console.print(f"[yellow]Warning: Failed to install {dep}[/yellow]")
                gui_failed.append(dep)

        if gui_failed:
            console.print(f"[yellow]Some GUI dependencies failed: {', '.join(gui_failed)}[/yellow]")
            console.print("[yellow]You may need to install them manually later[/yellow]")

        # Step 6: Install the package in editable mode
        console.print("[green]Installing NeuRPi in editable mode...[/green]")
        try:
            subprocess.run([str(pip_exe), "install", "-e", str(project_root)], check=True)
            console.print("[green]✓ NeuRPi installed in editable mode[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]Warning: Failed to install NeuRPi in editable mode: {e}[/yellow]")
            console.print(f"[yellow]Warning: Failed to install NeuRPi in editable mode: {e}[/yellow]")
            console.print("[yellow]You may need to install it manually with: pip install -e .[/yellow]")

        # Step 7: Success message with instructions
        console.print("\n[bold green]✓ Setup completed![/bold green]")

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

        console.print("\n[bold blue]Then you can run:[/bold blue]")
        console.print("[cyan]  neurpi terminal  # Start terminal agent[/cyan]")
        console.print("[cyan]  neurpi pilot     # Start pilot agent[/cyan]")
        console.print("[cyan]  neurpi status    # Check status[/cyan]")

        if not pandas_success or gui_failed:
            console.print("\n[bold blue]To install missing dependencies later:[/bold blue]")
            if not pandas_success:
                console.print("[cyan]  pip install pandas  # For data processing[/cyan]")
            if gui_failed:
                console.print("[cyan]  pip install matplotlib PyQt5 opencv-python  # For GUI[/cyan]")

    except subprocess.CalledProcessError as e:
        # Only exit on critical failures (like venv creation or pip upgrade)
        cmd_str = ' '.join(e.cmd) if hasattr(e, 'cmd') else 'unknown command'
        if "venv" in cmd_str or ("pip" in cmd_str and "upgrade" in cmd_str):
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
