# NeuRPi - Unified Neuroscience Experiment Framework

> **A comprehensive, unified framework for neuroscience and psychophysics experiments that combines controller (Controller) and experiment (rig) functionality in a single, distributed architecture.**

[![Python 3.13+](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

NeuRPi provides a robust, scalable platform for conducting behavioral experiments with real-time hardware control, distributed computing capabilities, and comprehensive data management. Originally developed from separate Controller and Rig branches, it now offers a unified solution for experiment control and execution.

## 🧠 Key Features

### Core Architecture

- **🔗 Unified Codebase**: Single repository combining controller and experiment functionality
- **🌐 Distributed Computing**: Run components across multiple machines or locally
- **⚡ Real-time Performance**: High-precision timing for behavioral experiments
- **🔌 Hardware Abstraction**: Unified interface for diverse hardware components

### Deployment & Management

- **📦 Modern Package Management**: UV-based dependency management with Python 3.13+
- **🖥️ Flexible GUI**: Optional PyQt6 interface with headless operation support
- **🔧 Cross-Platform**: Native support for Windows and Linux
- **📊 Comprehensive Logging**: Structured logging with multiple output formats

### Networking & Communication

- **🚀 ZeroMQ Backbone**: High-performance, reliable inter-process communication
- **🔄 Auto-Discovery**: Automatic rig detection and management
- **📡 Protocol Flexibility**: Support for various experimental protocols
- **🛡️ Error Recovery**: Robust error handling and recovery mechanisms

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+** (Required for latest features and performance)
- **UV Package Manager** (Modern, fast Python package management)

### Installation

#### 1. Install UV Package Manager

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS (Bash)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Alternative: via pip
pip install uv
```

#### 2. Clone and Setup NeuRPi

```bash
# Clone the repository
git clone https://github.com/your-org/neurpi.git
cd neurpi

# Install all dependencies with development tools
uv sync --all-extras

# Or install minimal setup
uv sync
```

#### 3. Configure Environment

```bash
# Initialize default configuration
uv run neurpi init-config

# Set environment variables (optional)
export NEURPI_NAME="my_rig_01"
export NEURPI_MSGPORT=5560
export NEURPI_DATADIR="/path/to/data"
```

### Basic Usage

#### Run Controller (Controller)

```bash
# With GUI (default)
uv run neurpi controller

# Console mode (no GUI)
uv run neurpi controller --no-gui

# Custom configuration
uv run neurpi controller --config custom_config.yaml
```

#### Run rig (Experiment Node)

```bash
# Basic rig
uv run neurpi rig --name rig_01

# With specific hardware profile
uv run neurpi rig --name rig_01 --hardware lab_setup_a

# Child rig (hierarchical setup)
uv run neurpi rig --child --parent controller_main
```

#### Unified Mode (Auto-detection)

```bash
# Automatically detects role based on configuration
uv run neurpi unified

# With specific role override
uv run neurpi unified --force-role rig
```

## 📖 Usage Examples & Scenarios

### Scenario 1: Single Machine Development

Perfect for protocol development and testing:

```bash
# Controller 1: Start rig with test hardware
uv run neurpi rig --name dev_rig --hardware simulator

# Controller 2: Start controller
uv run neurpi controller --development-mode
```

### Scenario 2: Distributed Laboratory Setup

Production environment with multiple experiment rigs:

```bash
# Experiment Room - Rig 1
uv run neurpi rig --name rig_001 --hardware lab_config_a

# Experiment Room - Rig 2
uv run neurpi rig --name rig_002 --hardware lab_config_b

# Control Room - Controller
uv run neurpi controller --lab-mode --auto-discover
```

### Scenario 3: Console Mode for Remote Operation

Headless operation via SSH or automated scripts:

```bash
# Start controller in console mode
uv run neurpi controller --no-gui --remote-access

# Available console commands:
neurpi> status              # Show system status
neurpi> rigs              # List connected rigs
neurpi> ping all            # Ping all rigs
neurpi> hardware rig_001    # Check hardware status
neurpi> start rig_001 random_dot_motion subject_001  # Start experiment
neurpi> monitor rig_001     # Monitor experiment progress
neurpi> stop rig_001        # Stop experiment
neurpi> data export         # Export recent data
neurpi> quit                # Exit controller
```

### Scenario 4: Python API Integration

Embed NeuRPi in custom applications:

```python
from neurpi.agents.controller import Controller
from neurpi.agents.rig import rig
from neurpi.protocols import load_protocol

# Create controller programmatically
controller = Controller(gui_enabled=False)
controller.start()

# Connect to existing rig
rig_info = controller.get_rig("rig_001")

# Load and start experiment protocol
protocol = load_protocol("random_dot_motion", "rt_training")
controller.start_experiment(
    rig="rig_001",
    protocol=protocol,
    subject="mouse_042"
)

# Monitor progress
while controller.is_experiment_running("rig_001"):
    status = controller.get_experiment_status("rig_001")
    print(f"Trials completed: {status.trials_completed}")
    time.sleep(1)
```

### Scenario 5: Hierarchical Multi-Lab Setup

Coordinate multiple laboratories:

```bash
# Lab A - Main Controller
uv run neurpi controller --name lab_a_control --port 5555

# Lab A - Local rigs
uv run neurpi rig --name lab_a_rig_01 --parent lab_a_control
uv run neurpi rig --name lab_a_rig_02 --parent lab_a_control

# Lab B - Sub Controller
uv run neurpi controller --name lab_b_control --child --parent lab_a_control

# Lab B - Local rigs
uv run neurpi rig --name lab_b_rig_01 --parent lab_b_control
```

## 🗂️ Project Structure

```
neurpi/
├── agents/              # Core Controller and rig agents
├── networking/          # ZeroMQ-based communication
├── gui/                 # Optional PyQt6 interface
├── config/              # Configuration management
├── loggers/             # Unified logging system
├── hardware/            # Hardware abstraction (placeholder)
├── tasks/               # Experiment tasks (placeholder)
├── utils/               # Utility functions
└── data_model/          # Data structures (placeholder)
```

## ⚙️ Configuration

Configuration is handled through:

1. Default values in code
2. YAML config files (`neurpi_config.yaml`)
3. Environment variables (`NEURPI_*`)

```bash
# Initialize default config file
uv run neurpi init-config

# Set environment variables
export NEURPI_NAME=my_rig
export NEURPI_MSGPORT=5560
```

## 🔧 Development

```bash
# Development install
uv sync --dev

# Run tests
uv run pytest

# Check code
uv run black neurpi/
uv run isort neurpi/
```

## 📝 Migration from Old Structure

This unified version merges the previous separate `NeuRPi-controller` and `NeuRPi-rig` branches:

- **Controller** (controller) → `neurpi controller`
- **rig** (rig) → `neurpi rig`
- **Both** → `neurpi unified`

The networking and core functionality remain compatible while simplifying deployment and maintenance.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

Happy experimenting with NeuRPi!
