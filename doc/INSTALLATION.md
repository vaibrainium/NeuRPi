# NeuRPi Installation Guide

> **Complete installation guide for the NeuRPi Unified Psychophysics Framework**

[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![UV Package Manager](https://img.shields.io/badge/package--manager-UV-orange.svg)](https://github.com/astral-sh/uv)

## 📋 Table of Contents

- [System Requirements](#system-requirements)
- [Installation Methods](#installation-methods)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Platform-Specific Notes](#platform-specific-notes)

## 🖥️ System Requirements

### Minimum Requirements
- **Operating System**: Windows 10/11, Linux (Ubuntu 20.04+), macOS 11+
- **Python**: 3.8 or higher (**3.13+ recommended** for best performance)
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space
- **Network**: Ethernet/WiFi for distributed setups

### Recommended Hardware
- **CPU**: Multi-core processor (4+ cores recommended)
- **RAM**: 16GB for complex experiments
- **Storage**: SSD for better I/O performance
- **Network**: Gigabit Ethernet for high-throughput data transfer

## 🚀 Installation Methods

### Method 1: Quick Install (Recommended)

#### Step 1: Install UV Package Manager

**Windows (PowerShell as Administrator):**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Linux/macOS (Terminal):**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Alternative (via pip):**
```bash
pip install uv
```

#### Step 2: Clone and Setup NeuRPi
```bash
# Clone the repository
git clone https://github.com/your-org/NeuRPi.git
cd NeuRPi

# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements/base.txt

# Install NeuRPi in development mode
uv pip install -e .
```

### Method 2: Traditional pip Installation

```bash
# Clone repository
git clone https://github.com/your-org/NeuRPi.git
cd NeuRPi

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements/base.txt
pip install -e .
```

## 🎯 Quick Start

After installation, you can start NeuRPi components using the convenient launcher scripts:

### Windows Users

Use the provided batch script for easy startup:

```cmd
# Interactive menu (recommended for beginners)
start_new.bat

# Direct commands
start_new.bat terminal    # Start Terminal (controller)
start_new.bat pilot       # Start Pilot (experiment node)
start_new.bat test        # Run system tests
start_new.bat status      # Show system status
```

### Linux/macOS Users

```bash
# Using Python CLI directly
uv run python -m neurpi.cli terminal          # Start Terminal
uv run python -m neurpi.cli terminal --no-gui # Terminal without GUI
uv run python -m neurpi.cli pilot --name pilot_001  # Start named Pilot
uv run python -m neurpi.cli status            # Show status
```

## 🔧 Detailed Installation

### Step 1: Environment Setup

#### Install UV Package Manager
UV is a fast, modern Python package manager that significantly speeds up dependency resolution and installation.

**Verify UV installation:**
```bash
uv --version
```

#### Python Version Check
```bash
python --version
# Should show Python 3.8+ (3.13+ recommended)
```

### Step 2: Clone Repository

```bash
git clone https://github.com/your-org/NeuRPi.git
cd NeuRPi
```

### Step 3: Virtual Environment Setup

#### Using UV (Recommended)
```bash
# Create virtual environment
uv venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

#### Using Standard Python
```bash
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

### Step 4: Install Dependencies

#### Core Dependencies
```bash
# Install base requirements
uv pip install -r requirements/base.txt

# Or with standard pip:
pip install -r requirements/base.txt
```

#### Optional Dependencies

**GUI Components (PyQt5):**
```bash
uv pip install PyQt5>=5.15.0 pyqtgraph>=0.13.0
```

**Hardware Support (Raspberry Pi):**
```bash
uv pip install RPi.GPIO pigpio adafruit-circuitpython-busdevice
```

**Advanced Stimulus Presentation:**
```bash
uv pip install pygame>=2.1.2 psychopy
```

### Step 5: Install NeuRPi

```bash
# Development installation (recommended for research)
uv pip install -e .

# Or with standard pip:
pip install -e .
```

## ⚙️ Configuration

### Initial Configuration

NeuRPi uses YAML configuration files located in `neurpi/config/`:

- `config_terminal.yaml` - Terminal (controller) settings
- `config_pilot.yaml` - Pilot (experiment node) settings

#### Configure Terminal
Edit `neurpi/config/config_terminal.yaml`:

```yaml
# Terminal Configuration
DATADIR: "C:/Users/YourName/NeuRPi/Data/"
BASEDIR: "C:/Users/YourName/NeuRPi/"
PROTOCOLDIR: "protocols/"
VENVDIR: ".venv/"
LOGDIR: "logs/"
LOGLEVEL: "INFO"
NAME: "T"
MSGPORT: 11000
TERMINALIP: "192.168.1.100"  # Your terminal IP
```

#### Configure Pilot
Edit `neurpi/config/config_pilot.yaml`:

```yaml
# Pilot Configuration
NAME: "pilot_001"
MSGPORT: 11001
PARENTIP: "192.168.1.100"  # Terminal IP
PARENTPORT: 11000
LINEAGE: "CHILD"
```

### Network Configuration

For distributed setups, ensure:

1. **Firewall**: Open ports 11000-11010 for NeuRPi communication
2. **Network**: All machines on same network or VPN
3. **IP Addresses**: Update config files with correct IP addresses

## ✅ Verification

### Test Basic Installation

```bash
# Test CLI accessibility
uv run python -m neurpi.cli status

# Should output:
# ✓ NeuRPi CLI is operational
# ℹ Use 'neurpi.cli terminal' or 'neurpi.cli pilot' to start agents
```

### Test System Components

```bash
# Run basic system test
uv run python test_basic.py

# Or using the launcher:
start_new.bat test  # Windows
```

### Test GUI (Optional)

```bash
# Start Terminal with GUI
uv run python -m neurpi.cli terminal

# Should open PyQt5 interface
```

### Test Networking

1. **Start Terminal:**
```bash
uv run python -m neurpi.cli terminal --no-gui
```

2. **Start Pilot (different terminal/machine):**
```bash
uv run python -m neurpi.cli pilot --name pilot_001
```

3. **Verify Connection:**
   - Terminal should show "Pilot pilot_001 connected"
   - Pilot should show "Connected to Terminal"

## 🔧 Troubleshooting

### Common Issues

#### 1. UV Not Found
```bash
# Error: 'uv' is not recognized
# Solution: Restart terminal or add UV to PATH manually
```

#### 2. Python Version Issues
```bash
# Error: Python 3.8+ required
# Solution: Install newer Python version
pyenv install 3.13.0  # Using pyenv
pyenv global 3.13.0
```

#### 3. Permission Errors (Windows)
```cmd
# Run PowerShell as Administrator for UV installation
# Or use alternative installation method
```

#### 4. PyQt5 Installation Issues
```bash
# Ubuntu/Debian:
sudo apt-get install python3-pyqt5 python3-pyqt5-dev

# macOS:
brew install pyqt5

# Windows: Usually works with pip, try:
pip install --upgrade pip setuptools wheel
pip install PyQt5
```

#### 5. Network Connection Issues
- Check firewall settings
- Verify IP addresses in config files
- Ensure ports 11000-11010 are available
- Test with `telnet <ip> <port>`

#### 6. Hardware Access Issues
```bash
# Linux: Add user to dialout group for serial access
sudo usermod -a -G dialout $USER
# Logout and login again
```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# Set log level to DEBUG in config files
LOGLEVEL: "DEBUG"

# Or use environment variable
export NEURPI_LOGLEVEL=DEBUG
uv run python -m neurpi.cli terminal
```

### Log Files

Check log files in the `logs/` directory:
- `agents.agent_terminal.log` - Terminal agent logs
- `networking.node.log` - Network communication logs
- `neurpi_YYYY-MM-DD.log` - Daily system logs

## 🖥️ Platform-Specific Notes

### Windows

#### PowerShell Execution Policy
If you encounter execution policy errors:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Windows Defender
Add NeuRPi directory to Windows Defender exclusions for better performance.

#### Hardware Drivers
Install appropriate drivers for:
- Arduino/Teensy boards
- Serial devices
- GPIO expanders

### Linux

#### System Dependencies
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-dev python3-pip git build-essential

# CentOS/RHEL
sudo yum install python3-devel python3-pip git gcc gcc-c++
```

#### Serial Port Access
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
```

#### Real-time Capabilities
For high-precision timing:
```bash
# Install real-time kernel (optional)
sudo apt-get install linux-image-rt-amd64
```

### macOS

#### Xcode Command Line Tools
```bash
xcode-select --install
```

#### Homebrew Dependencies
```bash
brew install python@3.13 git
```

## 🎯 Next Steps

After successful installation:

1. **📚 Read the User Guide**: Learn about experiment design and protocols
2. **🧪 Run Example Experiments**: Start with provided example protocols
3. **🔧 Hardware Setup**: Configure your specific hardware components
4. **🌐 Network Configuration**: Set up distributed computing if needed
5. **📊 Data Analysis**: Explore data output formats and analysis tools

## 📞 Support

- **Documentation**: [Full Documentation](https://neurpi.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/your-org/NeuRPi/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/NeuRPi/discussions)
- **Email**: neurpi-support@yourorg.edu

## 📄 License

NeuRPi is released under the MIT License. See [LICENSE](LICENSE) for details.

---

**Happy experimenting! 🧠⚡**
