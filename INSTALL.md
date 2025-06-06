# NeuRPi Installation Guide

This document provides installation instructions for the NeuRPi distributed neuroscience experimentation platform.

## Dependencies

All dependencies are now managed through `pyproject.toml` using modern Python packaging standards. The old `requirements/` directory has been removed in favor of this consolidated approach.

## Installation Options

### Basic Installation (Core Dependencies Only)

```bash
pip install .
```

This installs only the core dependencies needed to run NeuRPi:
- numpy, scipy, pandas (scientific computing)
- PyQt5, pyqtgraph, opencv (GUI components)
- pyserial, pyzmq, tornado (hardware and networking)
- h5py, tables, blosc2 (data storage)
- click, rich, omegaconf (CLI and configuration)

### Development Installation

```bash
pip install -e ".[dev]"
```

This includes all core dependencies plus development tools:
- pytest, pytest-cov (testing)
- black, flake8, mypy (code quality)
- pre-commit (git hooks)
- sphinx (documentation)

### Hardware Installation (Raspberry Pi)

```bash
pip install ".[hardware]"
```

This includes hardware-specific dependencies for Raspberry Pi:
- RPi.GPIO, gpiozero (GPIO control)
- adafruit-circuitpython libraries (motor/servo control)

### GUI Installation

```bash
pip install ".[gui]"
```

This includes additional GUI dependencies:
- matplotlib (plotting)
- PyQt5 tools and plugins

### Full Installation (All Dependencies)

```bash
pip install ".[full]"
```

This installs all optional dependencies (equivalent to `[gui,hardware,dev]`).

## Using uv (Recommended for Development)

For faster dependency resolution and installation, you can use `uv`:

```bash
# Install uv
pip install uv

# Install NeuRPi with uv
uv pip install -e ".[full]"
```

## Platform-Specific Notes

### Raspberry Pi
Hardware dependencies (RPi.GPIO, gpiozero) are automatically included only on Linux systems. On other platforms, these will be skipped.

### Windows/macOS
Hardware dependencies are not installed on non-Linux platforms to avoid compatibility issues.

## Legacy Support

The `setup.py` file is maintained for backward compatibility but is now minimal. All configuration is handled through `pyproject.toml`.

## Troubleshooting

### Missing tomli Error
If you get an error about missing `tomli`, install it manually:
```bash
pip install tomli
```

### PyQt5 Installation Issues
On some systems, you may need to install PyQt5 separately:
```bash
# Ubuntu/Debian
sudo apt-get install python3-pyqt5

# Or via pip
pip install PyQt5
```

### Hardware Dependencies on Non-Linux
Hardware dependencies are automatically skipped on non-Linux systems. If you need to test hardware code on other platforms, you can mock the hardware interfaces.

## Verification

After installation, verify NeuRPi is working:

```bash
# Check CLI
neurpi --help

# Run setup script
neurpi-setup

# Test configuration
python -c "import neurpi; print('NeuRPi installed successfully')"
```
