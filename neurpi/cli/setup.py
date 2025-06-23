#!/usr/bin/env python3

import importlib
import os
import platform
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def clean_environment():
    """Clean environment variables to prevent venv pollution."""
    # Clear VIRTUAL_ENV environment variable
    if "VIRTUAL_ENV" in os.environ:
        print("🧹 Clearing VIRTUAL_ENV environment variable...")
        del os.environ["VIRTUAL_ENV"]
        print("✓ VIRTUAL_ENV cleared")

    # Remove .venv paths from PATH
    current_path = os.environ.get("PATH", "")
    if current_path:
        print("🧹 Cleaning PATH of .venv entries...")

        if platform.system() == "Windows":
            path_separator = ";"
            # Remove various .venv patterns from PATH
            path_parts = current_path.split(path_separator)
            cleaned_parts = []
            removed_count = 0

            for part in path_parts:
                # Skip parts that contain .venv patterns
                if ".venv" in part.lower() and any(pattern in part.lower() for pattern in ["scripts", "bin"]):
                    removed_count += 1
                    continue
                cleaned_parts.append(part)

            if removed_count > 0:
                os.environ["PATH"] = path_separator.join(cleaned_parts)
                print(f"✓ Removed {removed_count} .venv entries from PATH")
            else:
                print("✓ No .venv entries found in PATH")
        else:
            # Unix/Linux/Mac
            path_separator = ":"
            path_parts = current_path.split(path_separator)
            cleaned_parts = []
            removed_count = 0

            for part in path_parts:
                # Skip parts that contain .venv patterns
                if ".venv" in part and ("bin" in part or "scripts" in part.lower()):
                    removed_count += 1
                    continue
                cleaned_parts.append(part)

            if removed_count > 0:
                os.environ["PATH"] = path_separator.join(cleaned_parts)
                print(f"✓ Removed {removed_count} .venv entries from PATH")
            else:
                print("✓ No .venv entries found in PATH")


def run_subprocess_with_debug(command, description, show_command=False, **kwargs):
    """Run a subprocess command with detailed error reporting."""
    try:
        # Set default arguments
        default_kwargs = {
            'capture_output': True,
            'text': True,
            'timeout': 30,
            'check': True
        }
        default_kwargs.update(kwargs)

        print(f"🔧 {description}")
        if show_command:
            print(f"   Command: {' '.join(str(arg) for arg in command)}")

        result = subprocess.run(command, **default_kwargs)

        # Don't show output for successful installations unless requested
        return result

    except subprocess.CalledProcessError as e:
        print(f"   ❌ Command failed with exit code {e.returncode}")
        print(f"   Command: {' '.join(str(arg) for arg in command)}")
        if e.stdout:
            print(f"   📤 Stdout: {e.stdout.strip()}")
        if e.stderr:
            print(f"   📥 Stderr: {e.stderr.strip()}")
        raise
    except subprocess.TimeoutExpired as e:
        print(f"   ⏰ Command timed out after {e.timeout} seconds")
        print(f"   Command: {' '.join(str(arg) for arg in command)}")
        if e.stdout:
            print(f"   📤 Partial stdout: {e.stdout.strip()}")
        if e.stderr:
            print(f"   📥 Partial stderr: {e.stderr.strip()}")
        raise
    except FileNotFoundError as e:
        print(f"   📁 File not found: {e}")
        print(f"   Command: {' '.join(str(arg) for arg in command)}")
        print(f"   💡 Make sure the command is installed and in your PATH")
        raise


def check_uv_available():
    """Check if uv is available and return the executable path."""
    # First check if uv is in PATH
    uv_path = shutil.which("uv")
    if uv_path:
        try:
            result = subprocess.run([uv_path, "--version"], capture_output=True, text=True, timeout=10, check=True)
            print(f"✓ UV found in PATH: {result.stdout.strip()}")
            return uv_path
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    # Check common installation locations before installing
    print("UV not found in PATH. Checking common installation locations...")

    if platform.system() == "Windows":
        common_paths = [
            Path.home() / ".cargo" / "bin" / "uv.exe",
            Path.home() / "AppData" / "Roaming" / "uv" / "bin" / "uv.exe",
            Path.home() / ".local" / "bin" / "uv.exe",
            Path.home() / "AppData" / "Roaming" / "Python" / f"Python{sys.version_info.major}{sys.version_info.minor}" / "Scripts" / "uv.exe"
        ]
    else:
        common_paths = [
            Path.home() / ".cargo" / "bin" / "uv",
            Path.home() / ".local" / "bin" / "uv",
            Path("/usr/local/bin/uv")        ]

    for uv_path in common_paths:
        if uv_path.exists():
            try:
                result = subprocess.run([str(uv_path), "--version"], capture_output=True, text=True, timeout=10, check=True)
                print(f"✓ UV found at: {uv_path}")
                print(f"  Version: {result.stdout.strip()}")

                # Add UV directory to PATH for current session if not already there
                uv_dir = str(uv_path.parent)
                current_path = os.environ.get("PATH", "")
                if uv_dir not in current_path:
                    os.environ["PATH"] = f"{uv_dir}{os.pathsep}{current_path}"
                    print(f"  Added {uv_dir} to PATH for current session")

                return str(uv_path)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue

    print("UV not found in common locations. Installing UV...")

    # Try official installation methods
    if platform.system() == "Windows":
        # Use PowerShell with irm and iex
        try:
            print("Installing UV via PowerShell...")
            subprocess.run([
                "powershell", "-ExecutionPolicy", "ByPass", "-c",
                "irm https://astral.sh/uv/install.ps1 | iex"
            ], check=True, capture_output=True, text=True, timeout=120)
            print("✓ UV installed via PowerShell")

            # After installation, check the same common paths again
            for uv_path in common_paths:
                if uv_path.exists():
                    try:
                        result = subprocess.run([str(uv_path), "--version"], capture_output=True, text=True, timeout=10, check=True)
                        print(f"✓ UV found after installation: {uv_path}")
                        return str(uv_path)
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                        continue

            # If not found in common paths, check PATH again
            uv_path = shutil.which("uv")
            if uv_path:
                return uv_path

            print("⚠️ UV installed but not found. You may need to restart your terminal.")
            return None

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            pass
    else:
        # Unix/Linux: Try curl first, then wget
        for cmd_name, command in [
            ("curl", ["curl", "-LsSf", "https://astral.sh/uv/install.sh"]),
            ("wget", ["wget", "-qO-", "https://astral.sh/uv/install.sh"])
        ]:
            if shutil.which(cmd_name):
                try:
                    print(f"Installing UV via {cmd_name}...")
                    # Download and pipe to sh
                    download_proc = subprocess.run(command, capture_output=True, text=True, timeout=60, check=True)
                    subprocess.run(["sh"], input=download_proc.stdout, text=True, check=True, timeout=60)
                    print(f"✓ UV installed via {cmd_name}")

                    # Check common paths after installation
                    for uv_path in common_paths:
                        if uv_path.exists():
                            try:
                                result = subprocess.run([str(uv_path), "--version"], capture_output=True, text=True, timeout=10, check=True)
                                print(f"✓ UV found after installation: {uv_path}")
                                return str(uv_path)
                            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                                continue

                    # Check PATH again
                    uv_path = shutil.which("uv")
                    if uv_path:
                        return uv_path

                    return None
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    continue

    # Fallback to pip installation
    try:
        print("Trying pip installation as fallback...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", "uv"], check=True, capture_output=True)
        print("✓ UV installed via pip")

        # Check PATH and common paths after pip installation
        uv_path = shutil.which("uv")
        if uv_path:
            return uv_path

        for uv_path in common_paths:
            if uv_path.exists():
                try:
                    result = subprocess.run([str(uv_path), "--version"], capture_output=True, text=True, timeout=10, check=True)
                    print(f"✓ UV found after pip installation: {uv_path}")
                    return str(uv_path)
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    continue

        return None
    except subprocess.CalledProcessError:
        print("❌ Failed to install UV. Please install manually:")
        if platform.system() == "Windows":
            print("  powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
        else:
            print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("  Or: pip install --user uv")
        return None


def ensure_python_version_with_uv(uv_executable, python_version):
    """Ensure the specified Python version is available with UV."""
    try:
        result = subprocess.run([uv_executable, "python", "list"], capture_output=True, text=True, check=True)
        if python_version in result.stdout:
            print(f"✓ Python {python_version} available")
            return True

        print(f"Installing Python {python_version}...")
        subprocess.run([uv_executable, "python", "install", python_version], check=True, capture_output=True)
        print(f"✓ Python {python_version} installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Python {python_version}: {e}")
        return False


def read_requirements_from_toml(group_name):
    """Read requirements from pyproject.toml file."""
    project_root = Path(__file__).parent.parent.parent
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        print("Error: pyproject.toml not found.")
        return []

    try:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib

        with open(pyproject_path, "rb") as f:
            config = tomllib.load(f)

        project_config = config.get("project", {})
        if group_name == "core":
            return project_config.get("dependencies", [])

        return project_config.get("optional-dependencies", {}).get(group_name, [])
    except Exception as e:
        print(f"Error reading pyproject.toml: {e}")
        return []


def refresh_python_path():
    """Refresh Python path to include user site-packages after installation."""
    try:
        import site
        importlib.reload(site)
        user_site = site.getusersitepackages()
        if user_site not in sys.path:
            sys.path.insert(0, user_site)
            print(f"✓ Added {user_site} to Python path")
    except Exception as e:
        print(f"Warning: Could not refresh Python path: {e}")


def install_packages_with_fallback(packages):
    """Try multiple methods to install packages."""
    for method_name, command in [
        ("with --user", [sys.executable, "-m", "pip", "install", "--user"] + packages),
        ("standard", [sys.executable, "-m", "pip", "install"] + packages),
        ("--break-system-packages", [sys.executable, "-m", "pip", "install", "--break-system-packages"] + packages),
    ]:
        try:
            print(f"🔧 Trying to install packages {method_name}...")
            print(f"   Command: {' '.join(command)}")
            result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
            print(f"✓ Dependencies installed {method_name}")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Installation {method_name} failed with exit code {e.returncode}")
            if e.stderr:
                print(f"   Error: {e.stderr.strip()}")
            continue
        except subprocess.TimeoutExpired:
            print(f"   ⏰ Installation {method_name} timed out")
            continue
    return False


def show_manual_installation_help(packages):
    """Show help for manual installation."""
    print(f"\n❌ Failed to install: {', '.join(packages)}")
    print(f"Please install manually: pip install --user {' '.join(packages)}")


def ensure_essential_dependencies():
    """Ensure essential dependencies are available."""
    missing = []

    # Check for required modules
    for module, package in [("tomllib", "tomli>=1.2.0"), ("click", "click>=8.0.0"), ("rich", "rich>=13.0.0")]:
        try:
            if module == "tomllib":
                try:
                    import tomllib  # noqa: F401
                except ImportError:
                    import tomli  # noqa: F401
            else:
                __import__(module)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"Installing essential dependencies: {', '.join(missing)}")
        if not install_packages_with_fallback(missing):
            show_manual_installation_help(missing)
            sys.exit(1)
        refresh_python_path()


def create_executable_script(project_root, venv_path):
    """Create platform-specific executable script."""
    script_name = "start.bat" if platform.system() == "Windows" else "start.sh"

    if platform.system() == "Windows":
        script_content = f"""@echo off
cd /d "{project_root}"
call "{venv_path}\\Scripts\\activate.bat"
python -m neurpi %*
"""
    else:
        script_content = f"""#!/bin/bash
cd "{project_root}"
source "{venv_path}/bin/activate"
python -m neurpi "$@"
"""

    script_path = project_root / script_name
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        if platform.system() != "Windows":
            script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

        print(f"✓ Created: {script_name}")
    except OSError as e:
        print(f"Warning: Failed to create script: {e}")


def create_virtual_environment(venv_path, python_version, use_uv=False, uv_executable=None):
    """Create virtual environment using uv or venv."""
    # Force recreation if path exists but is incomplete
    if venv_path.exists():
        if platform.system() == "Windows":
            possible_python_paths = [
                venv_path / "Scripts" / "python.exe",
                venv_path / "bin" / "python.exe",
                venv_path / "python.exe"
            ]
        else:
            possible_python_paths = [
                venv_path / "bin" / "python",
                venv_path / "Scripts" / "python"
            ]

        python_found = any(path.exists() for path in possible_python_paths)

        if not python_found:
            print("Incomplete virtual environment detected, removing...")
            try:
                import shutil
                shutil.rmtree(venv_path)
            except Exception as e:
                print(f"Warning: Could not remove incomplete venv: {e}")
        else:
            print("Virtual environment already exists and appears complete")
            return True

    print(f"Creating virtual environment with Python {python_version}...")

    try:
        if use_uv and uv_executable:
            # Use uv as primary venv creator
            print(f"🔧 Running: {uv_executable} venv {venv_path} --python {python_version}")
            result = subprocess.run([uv_executable, "venv", str(venv_path), "--python", python_version],
                         check=True, capture_output=True, text=True)
            print("✓ Virtual environment created with uv")
            if result.stdout:
                print(f"📤 UV output: {result.stdout.strip()}")
        else:
            # Fallback to standard venv
            print(f"🔧 Running: {sys.executable} -m venv {venv_path}")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)],
                         check=True, capture_output=True, text=True)
            print("✓ Virtual environment created with venv")

        # Debug: Show what was actually created
        print("📁 Virtual environment contents:")
        try:
            for item in venv_path.iterdir():
                print(f"  {item.name}/")
                if item.is_dir() and item.name in ["Scripts", "bin"]:
                    for subitem in item.iterdir():
                        if "python" in subitem.name.lower():
                            print(f"    {subitem.name}")
        except Exception as e:
            print(f"Could not list venv contents: {e}")

        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create virtual environment: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def ensure_pip_in_venv(python_exe):
    """Ensure pip is available in the virtual environment."""
    if not python_exe.exists():
        print(f"❌ Python executable not found: {python_exe}")
        return False

    try:
        run_subprocess_with_debug(
            [str(python_exe), "-m", "pip", "--version"],
            "Checking pip availability",
            timeout=30
        )
        print("\033[92m✓ pip is available\033[0m")
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        print("Installing pip in virtual environment...")
        try:
            run_subprocess_with_debug(
                [str(python_exe), "-m", "ensurepip", "--upgrade"],
                "Installing pip...",
                timeout=60
            )
            print("\033[92m✓ pip installed\033[0m")

            # Verify pip installation
            run_subprocess_with_debug(
                [str(python_exe), "-m", "pip", "--version"],
                "Verifying pip installation",
                timeout=10
            )
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"❌ Failed to install pip: {e}")
            return False


def install_dependencies(python_exe, group_name, use_uv=False, uv_executable=None):
    """Install dependencies from a dependency group."""
    requirements = read_requirements_from_toml(group_name)
    if not requirements:
        print(f"No requirements found for group '{group_name}'")
        return True, []

    print(f"Installing {group_name} dependencies...")
    failed_packages = []

    for dep in requirements:
        installed = False        # Always prefer UV if available
        if use_uv and uv_executable:
            # Use uv pip install which works well with existing environments
            try:
                run_subprocess_with_debug(
                    [uv_executable, "pip", "install", dep, "--python", str(python_exe)],
                    f"Installing {dep}...",
                    timeout=300
                )
                print(f"\033[92m✓ {dep} installed\033[0m")
                installed = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                # Check if it's a dependency resolution issue
                if "No solution found" in str(e) or "are incompatible" in str(e):
                    print(f"   Dependency conflict detected for {dep}, trying with --no-deps...")
                    try:
                        run_subprocess_with_debug(
                            [uv_executable, "pip", "install", dep, "--python", str(python_exe), "--no-deps"],
                            f"Installing {dep} (no deps)...",
                            timeout=300
                        )
                        print(f"\033[92m✓ {dep} installed (no deps)\033[0m")
                        installed = True
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
                        print(f"   uv pip install failed even with --no-deps for {dep}")
                        failed_packages.append(dep)
                        continue
                else:
                    print(f"   uv pip install failed for {dep}: {e}")
                    # Don't fallback to regular pip - if UV fails, we should investigate why
                    print(f"   Skipping {dep} - UV should handle all package installations")
                    failed_packages.append(dep)
                    continue        # Only use regular pip if UV is completely unavailable
        if not installed and not use_uv:
            try:
                run_subprocess_with_debug(
                    [str(python_exe), "-m", "pip", "install", dep],
                    f"Installing {dep}...",
                    timeout=300
                )
                print(f"\033[92m✓ {dep} installed\033[0m")
                installed = True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                print(f"   pip install failed for {dep}: {e}")
                failed_packages.append(dep)

        if not installed:
            print(f"⚠️ Failed to install {dep}")
            if dep not in failed_packages:
                failed_packages.append(dep)

    return len(failed_packages) == 0, failed_packages


def setup_neurpi(controller=False, rig=False, dev=False, full=False, python_version="3.11"):
    """Set up NeuRPi development environment with selective dependency installation."""
    # Clean environment to prevent venv pollution
    clean_environment()

    # Import rich here after dependencies are installed
    try:
        from rich.console import Console
        console = Console()
    except ImportError:
        # If rich is not available, fall back to print statements
        class SimpleConsole:
            def print(self, *args, **kwargs):
                # Extract the message and remove rich formatting
                if args:
                    msg = str(args[0])
                    # Remove rich color tags
                    import re
                    msg = re.sub(r'\[/?[a-zA-Z0-9 ]+\]', '', msg)
                    print(msg)
        console = SimpleConsole()    # Check for uv availability - prioritize uv installation
    uv_executable = check_uv_available()
    use_uv = uv_executable is not None

    if use_uv:
        console.print("[green]✓ Using uv package manager (primary)[/green]")
        if not ensure_python_version_with_uv(uv_executable, python_version):
            console.print(f"[yellow]Warning: Could not ensure Python {python_version}[/yellow]")
    else:
        console.print("[red]❌ UV not available - this is required for optimal performance[/red]")
        console.print("[yellow]Please install UV manually and restart:[/yellow]")
        if platform.system() == "Windows":
            console.print("[cyan]  powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"[/cyan]")
        else:
            console.print("[cyan]  curl -LsSf https://astral.sh/uv/install.sh | sh[/cyan]")
        console.print("[cyan]  Or: pip install --user uv[/cyan]")
        console.print("[red]Exiting - UV is required for this setup script[/red]")
        sys.exit(1)

    # Determine dependency groups
    if not any([controller, rig, dev, full]):
        full = True

    if controller:
        dependency_groups = ["core", "gui"]
    elif rig:
        dependency_groups = ["core", "hardware"]
    elif dev:
        dependency_groups = ["core", "dev"]
    elif full:
        dependency_groups = ["core", "gui", "hardware", "dev"]

    console.print(f"[cyan]Installing: {', '.join(dependency_groups)}[/cyan]")

    project_root = Path(__file__).parent.parent.parent
    venv_path = project_root / ".venv"    # Check if virtual environment already exists and is functional
    venv_needs_creation = True
    if venv_path.exists():
        console.print("[blue]Checking existing virtual environment...[/blue]")

        # Check for Python executable in the existing venv
        if platform.system() == "Windows":
            possible_python_paths = [
                venv_path / "Scripts" / "python.exe",
                venv_path / "bin" / "python.exe"
            ]
        else:
            possible_python_paths = [
                venv_path / "bin" / "python",
                venv_path / "Scripts" / "python"
            ]

        for path in possible_python_paths:
            if path.exists():
                try:
                    result = subprocess.run([str(path), "--version"],
                                          capture_output=True, text=True, timeout=10, check=True)
                    console.print(f"[green]✓ Using existing virtual environment with {result.stdout.strip()}[/green]")
                    venv_needs_creation = False
                    break
                except:
                    continue

        if venv_needs_creation:
            console.print("[yellow]Existing venv appears incomplete, will recreate...[/yellow]")
            # Remove incomplete venv
            try:
                import shutil
                shutil.rmtree(venv_path)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not remove incomplete venv: {e}[/yellow]")

    # Create virtual environment only if it doesn't exist or was incomplete
    if venv_needs_creation:
        if not create_virtual_environment(venv_path, python_version, use_uv, uv_executable):
            console.print("[red]Failed to create virtual environment[/red]")
            sys.exit(1)
    else:
        console.print("[green]✓ Virtual environment ready[/green]")# Set up Python executable - check multiple possible locations
    if platform.system() == "Windows":
        possible_python_paths = [
            venv_path / "Scripts" / "python.exe",
            venv_path / "bin" / "python.exe",  # UV sometimes uses bin on Windows
            venv_path / "python.exe",
            venv_path / "Scripts" / "python",  # Check non-.exe versions too
            venv_path / "bin" / "python"
        ]
    else:
        possible_python_paths = [
            venv_path / "bin" / "python",
            venv_path / "bin" / "python3",
            venv_path / "Scripts" / "python"
        ]

    python_exe = None
    console.print("[blue]🔍 Searching for Python executable...[/blue]")
    for path in possible_python_paths:
        console.print(f"[blue]   Checking: {path}[/blue]")
        if path.exists():
            python_exe = path
            console.print(f"[green]✓ Found Python executable: {python_exe}[/green]")

            # Test that the executable actually works
            try:
                result = subprocess.run([str(python_exe), "--version"],
                                      capture_output=True, text=True, timeout=10, check=True)
                console.print(f"[green]✓ Python executable verified: {result.stdout.strip()}[/green]")
                break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
                console.print(f"[yellow]⚠️ Python executable found but not working: {e}[/yellow]")
                python_exe = None
                continue
        else:
            console.print(f"[dim]   Not found: {path}[/dim]")

    if not python_exe:
        console.print(f"[red]❌ Could not find working Python executable in virtual environment[/red]")
        console.print(f"[yellow]Checked paths:[/yellow]")
        for path in possible_python_paths:
            console.print(f"[yellow]  {path} - exists: {path.exists()}[/yellow]")

        # Let's also check what files actually exist in the venv
        console.print(f"[blue]📁 Contents of venv directory:[/blue]")
        try:
            if venv_path.exists():
                for item in venv_path.rglob("python*"):
                    console.print(f"[blue]  Found: {item}[/blue]")
        except Exception as e:
            console.print(f"[yellow]Could not list venv contents: {e}[/yellow]")

        sys.exit(1)# Verify the Python executable actually works
    try:
        result = run_subprocess_with_debug(
            [str(python_exe), "--version"],
            "Verifying Python executable",
            timeout=10
        )
        console.print(f"[green]✓ Python executable verified: {result.stdout.strip()}[/green]")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        console.print(f"[red]❌ Python executable verification failed: {e}[/red]")
        console.print(f"[yellow]Executable path: {python_exe}[/yellow]")
        console.print(f"[yellow]Path exists: {python_exe.exists()}[/yellow]")
        sys.exit(1)

    # Ensure pip is available
    if not ensure_pip_in_venv(python_exe):
        console.print("[yellow]Warning: pip may not be fully available[/yellow]")

    # Install dependencies
    all_failed_packages = []
    for group in dependency_groups:
        success, failed_packages = install_dependencies(python_exe, group, use_uv, uv_executable)
        all_failed_packages.extend(failed_packages)    # Install NeuRPi in editable mode
    console.print("[green]Installing NeuRPi in editable mode...[/green]")
    try:
        if use_uv and uv_executable:
            # Use uv pip install with editable flag - more reliable than uv add
            run_subprocess_with_debug(
                [uv_executable, "pip", "install", "-e", str(project_root), "--python", str(python_exe)],
                "Installing NeuRPi in editable mode...",
                timeout=300
            )
            console.print("[green]✓ NeuRPi installed in editable mode[/green]")
        else:
            # Fallback to regular pip only if UV is not available
            run_subprocess_with_debug(
                [str(python_exe), "-m", "pip", "install", "-e", str(project_root)],
                "Installing NeuRPi in editable mode...",
                timeout=300
            )
            console.print("[green]✓ NeuRPi installed in editable mode[/green]")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        console.print(f"[red]Failed to install NeuRPi: {e}[/red]")
        if use_uv:
            console.print("[yellow]This may be due to dependency conflicts. Check the UV error output above.[/yellow]")
        sys.exit(1)

    # Create executable script
    create_executable_script(project_root, venv_path)

    # Summary
    console.print("\n[bold green]✓ Setup completed![/bold green]")

    if all_failed_packages:
        console.print(f"\n[yellow]⚠️ Failed packages: {', '.join(set(all_failed_packages))}[/yellow]")

    console.print(f"\n[bold blue]Activate with:[/bold blue]")
    if platform.system() == "Windows":
        console.print("[cyan]  .venv\\Scripts\\activate[/cyan]")
    else:
        console.print("[cyan]  source .venv/bin/activate[/cyan]")

    console.print("[green]🎉 NeuRPi is ready![/green]")


def main():
    """Main entry point for the neurpi-setup command."""
    ensure_essential_dependencies()
    setup_neurpi()


if __name__ == "__main__":
    try:
        # First ensure essential dependencies are available
        ensure_essential_dependencies()

        # Now we can safely import click
        import click

        @click.command()
        @click.option("--controller", is_flag=True, help="Install core + GUI dependencies")
        @click.option("--rig", is_flag=True, help="Install core + hardware dependencies")
        @click.option("--dev", is_flag=True, help="Install core + development dependencies")
        @click.option("--full", is_flag=True, help="Install all dependencies (default)")
        @click.option("--python-version", default="3.11", help="Python version to use (default: 3.11)")
        def cli_command(controller, rig, dev, full, python_version):
            """Set up NeuRPi development environment with selective dependency installation."""
            setup_neurpi(controller=controller, rig=rig, dev=dev, full=full, python_version=python_version)

        cli_command()
    except ImportError as e:
        print(f"Error importing required modules: {e}")
        print("Essential dependencies may not be properly installed.")
        print("Try running: pip install --user click rich tomli")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except SystemExit:
        raise
