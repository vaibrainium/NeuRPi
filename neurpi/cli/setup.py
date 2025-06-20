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
            print(f"✓ UV found: {result.stdout.strip()}")
            return uv_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass
    
    # UV not found, try to install it
    print("UV not found. Installing UV...")
    if _install_uv():
        return shutil.which("uv")
    
    return None


def _install_uv():
    """Install UV package manager."""
    try:
        # Method 1: Try installing via pip
        print("Attempting to install UV via pip...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user", "uv"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ UV installed via pip")
        return True
    except subprocess.CalledProcessError:
        pass
    
    try:
        # Method 2: Try the official installer script
        print("Attempting to install UV via official installer...")
        
        # Check if curl is available
        curl_available = shutil.which("curl") is not None
        wget_available = shutil.which("wget") is not None
        
        if curl_available:
            # Download and run the installer
            subprocess.run(
                ["curl", "-LsSf", "https://astral.sh/uv/install.sh"],
                stdout=subprocess.PIPE,
                check=True,
                text=True,
            )
            # The installer script needs to be piped to sh
            installer_result = subprocess.run(
                ["curl", "-LsSf", "https://astral.sh/uv/install.sh"],
                capture_output=True,
                text=True,
                check=True,
            )
            subprocess.run(
                ["sh"],
                input=installer_result.stdout,
                text=True,
                check=True,
            )
            print("✓ UV installed via official installer")
            return True
        elif wget_available:
            # Alternative with wget
            subprocess.run(
                ["wget", "-qO-", "https://astral.sh/uv/install.sh"],
                stdout=subprocess.PIPE,
                check=True,
            )
            installer_result = subprocess.run(
                ["wget", "-qO-", "https://astral.sh/uv/install.sh"],
                capture_output=True,
                text=True,
                check=True,
            )
            subprocess.run(
                ["sh"],
                input=installer_result.stdout,
                text=True,
                check=True,
            )
            print("✓ UV installed via official installer")
            return True
    except subprocess.CalledProcessError as e:
        print(f"Official installer failed: {e}")
    
    print("❌ Failed to install UV automatically")
    print("Please install UV manually:")
    print("  • pip install uv")
    print("  • curl -LsSf https://astral.sh/uv/install.sh | sh")
    print("  • Visit: https://docs.astral.sh/uv/getting-started/installation/")
    
    return False


def _ensure_python_version_with_uv(uv_executable, python_version):
    """Ensure the specified Python version is available with UV."""
    try:
        # Check if the Python version is already available
        result = subprocess.run(
            [uv_executable, "python", "list"],
            capture_output=True,
            text=True,
            check=True,
        )
        
        if python_version in result.stdout:
            print(f"✓ Python {python_version} is already available")
            return True
        
        # Install the Python version
        print(f"Installing Python {python_version} with UV...")
        subprocess.run(
            [uv_executable, "python", "install", python_version],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"✓ Python {python_version} installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Python {python_version}: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False


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
        
        # Try multiple installation methods
        if not _try_install_dependencies(missing):
            _show_manual_installation_help(missing)
            sys.exit(1)
        
        # After installation, refresh the Python path to ensure modules are available
        _refresh_python_path()


def _refresh_python_path():
    """Refresh Python path to include user site-packages after installation."""
    import site
    import importlib
    
    # Reload site module to pick up new user site-packages
    importlib.reload(site)
    
    # Add user site-packages to sys.path if not already there
    user_site = site.getusersitepackages()
    if user_site not in sys.path:
        sys.path.insert(0, user_site)
        print(f"✓ Added user site-packages to Python path: {user_site}")


def _try_install_dependencies(packages):
    """Try multiple methods to install packages, return True if successful."""
    # First, check if pip is available at all
    if not _check_pip_availability():
        print("❌ pip is not available. Attempting to install pip...")
        if not _install_pip():
            return False

    installation_methods = [
        ("with --user flag", [sys.executable, "-m", "pip", "install", "--user"] + packages),
        ("standard method", [sys.executable, "-m", "pip", "install"] + packages),
        ("with --break-system-packages", [sys.executable, "-m", "pip", "install", "--break-system-packages"] + packages),
    ]

    for method_name, command in installation_methods:
        try:
            print(f"Attempting installation {method_name}...")
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"✓ Essential dependencies installed {method_name}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Installation {method_name} failed: {e}")
            if e.stderr:
                print(f"Error details: {e.stderr}")

    # Try upgrading pip first, then install
    try:
        print("Attempting to upgrade pip first...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ pip upgraded, retrying dependency installation...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--user"] + packages,
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ Essential dependencies installed after pip upgrade")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Installation after pip upgrade failed: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")

    return False


def _check_pip_availability():
    """Check if pip is available via python -m pip."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        print(f"✓ pip is available: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"pip check failed: {e}")
        return False


def _install_pip():
    """Try to install pip using various methods."""
    print("Attempting to install pip...")

    # Method 1: Try using ensurepip
    try:
        print("Trying to install pip using ensurepip...")
        subprocess.run(
            [sys.executable, "-m", "ensurepip", "--upgrade"],
            check=True,
            capture_output=True,
            text=True,
        )
        print("✓ pip installed using ensurepip")
        return _check_pip_availability()
    except subprocess.CalledProcessError as e:
        print(f"ensurepip failed: {e}")

    # Method 2: Try downloading get-pip.py (if curl/wget available)
    try:
        print("Trying to download and install pip using get-pip.py...")

        # Check if we can download get-pip.py
        download_commands = [
            ["curl", "-o", "get-pip.py", "https://bootstrap.pypa.io/get-pip.py"],
            ["wget", "-O", "get-pip.py", "https://bootstrap.pypa.io/get-pip.py"],
        ]

        downloaded = False
        for cmd in download_commands:
            try:
                subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=30)
                downloaded = True
                print(f"✓ Downloaded get-pip.py using {cmd[0]}")
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                continue

        if downloaded:
            # Run get-pip.py
            subprocess.run(
                [sys.executable, "get-pip.py", "--user"],
                check=True,
                capture_output=True,
                text=True,
            )
            print("✓ pip installed using get-pip.py")

            # Clean up
            try:
                Path("get-pip.py").unlink()
            except FileNotFoundError:
                pass

            return _check_pip_availability()

    except subprocess.CalledProcessError as e:
        print(f"get-pip.py method failed: {e}")

    return False


def _show_manual_installation_help(packages):
    """Show help message for manual installation."""
    print("\n" + "=" * 60)
    print("❌ FAILED TO INSTALL ESSENTIAL DEPENDENCIES")
    print("=" * 60)
    print("All installation methods failed. Please try one of the following:")
    print("\n📋 FIRST, ensure pip is installed:")
    print("   • sudo apt update && sudo apt install python3-pip  # On Debian/Ubuntu/Raspberry Pi OS")
    print("   • curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py && python3 get-pip.py --user")
    print("   • python3 -m ensurepip --upgrade")
    print("\n📦 THEN, install the required packages:")
    print(f"1. Manual installation: pip install --user {' '.join(packages)}")
    print(f"2. System installation: sudo pip install {' '.join(packages)}")
    print(f"3. Alternative: python3 -m pip install --user {' '.join(packages)}")
    print(f"4. Virtual environment: python3 -m venv venv && source venv/bin/activate && pip install {' '.join(packages)}")
    print("\n🔍 TROUBLESHOOTING:")
    print("   • Check if you have internet connection: ping google.com")
    print("   • Check Python version: python3 --version")
    print("   • Check if pip works: python3 -m pip --version")
    print("   • Update package list: sudo apt update (on Debian-based systems)")
    print("\nAfter manual installation, run this setup script again.")
    print("=" * 60)


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
        console.print(
            f"[blue]Run NeuRPi using: ./{script_name} [command] [options][/blue]",
        )

    except OSError as e:
        console.print(f"[red]Warning: Failed to create executable script: {e}[/red]")


def create_virtual_environment(
    venv_path,
    python_version,
    use_uv=False,
    uv_executable=None,
):
    """Create virtual environment using uv or venv."""
    if venv_path.exists():
        print("Virtual environment already exists")
        return True

    print(f"Creating virtual environment with Python {python_version}...")

    try:
        if use_uv and uv_executable:
            print(f"Using uv to create virtual environment with Python {python_version}")
            result = subprocess.run(
                [uv_executable, "venv", str(venv_path), "--python", python_version],
                check=True,
                capture_output=True,
                text=True,
            )
            print("✓ Virtual environment created with uv")
        else:
            # When not using uv, fall back to system Python version if 3.11 not available
            if python_version == "3.11":
                current_version = f"{sys.version_info.major}.{sys.version_info.minor}"
                if current_version != "3.11":
                    print(f"System has Python {current_version}, using that instead of 3.11")
                    print("Install uv to use Python 3.11: https://docs.astral.sh/uv/")
                    python_version = current_version
            
            print(f"Using venv to create virtual environment with Python {python_version}")
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            print("✓ Virtual environment created with venv")

        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create virtual environment: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        
        # If uv failed to find Python 3.11, suggest installation
        if use_uv and "python" in str(e).lower() and python_version == "3.11":
            print("\n💡 Python 3.11 not found. You can install it with uv:")
            print("   uv python install 3.11")
            print("   Then run this setup script again.")
        
        return False
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create virtual environment: {e}")
        # Print more detailed error information
        print(f"Command that failed: {e.cmd}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        if e.stdout:
            print(f"Standard output: {e.stdout}")
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
        print("✓ pip installed using ensurepip")  # Verify pip executable was created
        if pip_exe.exists():
            print("✓ pip executable created successfully")
            return True
        print("⚠️ pip installed but executable still missing")

        # Try to create pip executable manually
        print("Attempting to create pip executable...")
        try:
            # Install pip again to force creation of executables
            subprocess.run(
                [
                    str(python_exe),
                    "-m",
                    "pip",
                    "install",
                    "--force-reinstall",
                    "pip",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            if pip_exe.exists():
                print("✓ pip executable created after force-reinstall")
                return True
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


def setup_neurpi(
    controller=False,
    rig=False,
    dev=False,
    full=False,
    python_version="3.11",
):
    """Set up NeuRPi development environment with selective dependency installation."""
    # First, ensure essential dependencies are installed
    ensure_essential_dependencies()

    # Now we can safely import
    from rich.console import Console

    console = Console()

    # Check for uv availability and install if needed
    uv_executable = check_uv_available()
    use_uv = uv_executable is not None

    if use_uv:
        console.print("[green]✓ Using uv package manager[/green]")
        
        # Ensure the specified Python version is available
        if not _ensure_python_version_with_uv(uv_executable, python_version):
            console.print(f"[yellow]Warning: Could not ensure Python {python_version} is available[/yellow]")
            console.print("[yellow]Continuing with available Python version...[/yellow]")
    else:
        console.print("[yellow]Using pip package manager[/yellow]")
        console.print("[yellow]UV not available - will use system Python[/yellow]")

    # Determine which dependency groups to install
    dependency_groups = []    # If no flags specified, default to full installation
    if not any([controller, rig, dev, full]):
        full = True

    if controller:
        dependency_groups = ["core", "gui"]
        console.print(
            "[bold blue]Setting up NeuRPi with GUI dependencies...[/bold blue]",
        )
    elif rig:
        dependency_groups = ["core", "hardware"]
        console.print(
            "[bold blue]Setting up NeuRPi with HARDWARE dependencies...[/bold blue]",
        )
    elif dev:
        dependency_groups = ["core", "dev"]
        console.print(
            "[bold blue]Setting up NeuRPi with DEVELOPMENT dependencies...[/bold blue]",
        )
    elif full:
        dependency_groups = ["core", "gui", "hardware", "dev"]
        console.print(
            "[bold blue]Setting up NeuRPi with FULL dependencies...[/bold blue]",
        )

    console.print(
        f"[cyan]Installing dependency groups: {', '.join(dependency_groups)}[/cyan]",
    )
    console.print(f"[cyan]Using Python version: {python_version}[/cyan]")

    project_root = Path(__file__).parent.parent.parent
    venv_path = project_root / ".venv"

    # Clean up any existing virtual environment
    if venv_path.exists():
        console.print("[yellow]Removing existing virtual environment...[/yellow]")
        try:
            import shutil
            shutil.rmtree(venv_path)
            console.print("[green]✓ Existing virtual environment removed[/green]")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not remove existing venv: {e}[/yellow]")

    try:
        # Step 1: Create virtual environment
        if not create_virtual_environment(
            venv_path,
            python_version,
            use_uv,
            uv_executable,
        ):
            console.print("[red]Failed to create virtual environment[/red]")
            sys.exit(1)
            
        # ...existing code...
        python_exe = venv_path / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

        # Step 3: Fix virtual environment activation scripts
        console.print("[blue]Fixing virtual environment activation...[/blue]")
        fix_venv_activation(venv_path)

        # Step 4: Ensure pip is available in the virtual environment
        if not ensure_pip_in_venv(python_exe):
            console.print(
                "[yellow]Warning: pip may not be fully available in venv[/yellow]",
            )  # Step 5: Install selected dependency groups
        console.print("[green]Installing selected dependencies...[/green]")
        all_failed_packages = []

        for group in dependency_groups:
            success, failed_packages = install_dependencies(
                python_exe,
                group,
                use_uv,
                uv_executable,
            )
            all_failed_packages.extend(
                failed_packages,
            )  # Step 6: Install the package in editable mode
        console.print("[green]Installing NeuRPi in editable mode...[/green]")
        editable_installed = False

        # Try with uv first if available
        if use_uv and uv_executable:
            try:
                subprocess.run(
                    [
                        uv_executable,
                        "pip",
                        "install",
                        "-e",
                        str(project_root),
                        "--python",
                        str(python_exe),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                console.print(
                    "[green]✓ NeuRPi installed in editable mode with uv[/green]",
                )
                editable_installed = True
            except subprocess.CalledProcessError:
                console.print(
                    "[yellow]uv editable install failed, trying with pip...[/yellow]",
                )

        # Fallback to pip if uv failed or not available
        if not editable_installed:
            try:
                subprocess.run(
                    [str(python_exe), "-m", "pip", "install", "-e", str(project_root)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                console.print(
                    "[green]✓ NeuRPi installed in editable mode with pip[/green]",
                )
                editable_installed = True
            except subprocess.CalledProcessError as e:
                console.print(
                    f"[red]Failed to install NeuRPi in editable mode: {e}[/red]",
                )  # Step 7: Create executable script
        console.print("[blue]📝 Creating executable script...[/blue]")
        create_executable_script(project_root, venv_path)  # Step 8: Summary
        console.print("\n[bold green]✓ Setup completed![/bold green]")

        if all_failed_packages:
            unique_failed = list(set(all_failed_packages))
            console.print(
                f"\n[yellow]⚠️ Some dependencies failed to install ({len(unique_failed)} packages):[/yellow]",
            )
            for pkg in unique_failed:
                console.print(f"[red]  • {pkg}[/red]")

            console.print(
                "\n[cyan]💡 You can try to install failed packages manually:[/cyan]",
            )
            if platform.system() == "Windows":
                console.print(
                    f"[cyan]   .venv\\Scripts\\python -m pip install {' '.join(unique_failed)}[/cyan]",
                )
            else:
                console.print(
                    f"[cyan]   .venv/bin/python -m pip install {' '.join(unique_failed)}[/cyan]",
                )

        console.print("\n[bold blue]To activate the virtual environment:[/bold blue]")
        if platform.system() == "Windows":
            console.print("[cyan]  .venv\\Scripts\\activate[/cyan]")
            console.print(
                "\n[bold blue]After activation, verify pip points to venv:[/bold blue]",
            )
            console.print(
                "[cyan]  where pip  # Should show .venv\\Scripts\\pip.exe[/cyan]",
            )
            console.print(
                "[cyan]  where python  # Should show .venv\\Scripts\\python.exe first[/cyan]",
            )
        else:
            console.print("[cyan]  source .venv/bin/activate[/cyan]")
            console.print(
                "\n[bold blue]After activation, verify pip points to venv:[/bold blue]",
            )
            console.print("[cyan]  which pip  # Should show .venv/bin/pip[/cyan]")
            console.print("[cyan]  which python  # Should show .venv/bin/python[/cyan]")

        console.print(
            "\n[bold blue]If pip still points to global installation:[/bold blue]",
        )
        console.print(
            "[cyan]  deactivate && .venv\\Scripts\\activate  # Re-activate on Windows[/cyan]",
        )
        console.print(
            "[cyan]  Or use: .venv\\Scripts\\python -m pip instead of pip[/cyan]",
        )

        if editable_installed:
            console.print("[green]🎉 NeuRPi is ready to use![/green]")
        else:
            console.print(
                "[yellow]⚠️ Setup completed but editable install failed[/yellow]",
            )

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
            with open(activate_script, encoding="utf-8") as f:
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
                with open(activate_script, "w", encoding="utf-8") as f:
                    f.write(path_fix + content)

                print("✓ Virtual environment activation script fixed")
                return True
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
        wrapper_content = f"""@echo off
"{python_exe}" -m pip %*
"""
        try:
            with open(pip_wrapper, "w", encoding="utf-8") as f:
                f.write(wrapper_content)
            print(f"✓ Created pip wrapper: {pip_wrapper}")
            return True
        except OSError as e:
            print(f"Failed to create pip wrapper: {e}")
            return False
    else:
        pip_wrapper = venv_path / "bin" / "pip"
        wrapper_content = f"""#!/bin/bash
"{python_exe}" -m pip "$@"
"""
        try:
            with open(pip_wrapper, "w", encoding="utf-8") as f:
                f.write(wrapper_content)
            pip_wrapper.chmod(0o755)  # Make executable
            print(f"✓ Created pip wrapper: {pip_wrapper}")
            return True
        except OSError as e:
            print(f"Failed to create pip wrapper: {e}")
            return False


# Create the setup command for CLI integration
ensure_essential_dependencies()

# Import click inside functions to avoid import issues
def main():
    """Main entry point for the neurpi-setup command."""
    setup_cli()


def setup_cli(controller=False, rig=False, dev=False, full=False, python_version="3.11"):
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
        # Import click here to ensure it's available after installation
        import click

        @click.command()
        @click.option("--controller", is_flag=True, help="Install core + GUI dependencies")
        @click.option("--rig", is_flag=True, help="Install core + hardware dependencies")
        @click.option("--dev", is_flag=True, help="Install core + development dependencies")
        @click.option("--full", is_flag=True, help="Install all dependencies (default)")
        @click.option(
            "--python-version",
            default="3.11",
            help="Python version to use (default: 3.11)",
        )
        def cli_command(controller, rig, dev, full, python_version):
            """Set up NeuRPi development environment with selective dependency installation."""
            setup_neurpi(
                controller=controller,
                rig=rig,
                dev=dev,
                full=full,
                python_version=python_version,
            )

        cli_command()
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        print("Please ensure all essential dependencies are installed.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
