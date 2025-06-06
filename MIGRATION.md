# Migration Guide: Requirements Directory to pyproject.toml

This guide helps existing users migrate from the old `requirements/` directory structure to the new unified `pyproject.toml` configuration.

## What Changed

### Before (Removed)
```
requirements/
├── base.txt          # Core dependencies with pinned versions
├── core.txt          # Core dependencies with minimum versions
├── dev.txt           # Development dependencies
├── gui.txt           # GUI dependencies
├── hardware.txt      # Hardware-specific dependencies
└── setup.txt         # Setup script dependencies
```

### After (Current)
All dependencies are now consolidated in `pyproject.toml`:
- **Core dependencies**: `project.dependencies`
- **Optional dependencies**: `project.optional-dependencies`
  - `gui`: GUI-related packages
  - `hardware`: Raspberry Pi hardware packages
  - `dev`: Development tools
  - `full`: All optional dependencies combined

## Migration Steps

### 1. Update Installation Commands

**Before:**
```bash
pip install -r requirements/core.txt
pip install -r requirements/gui.txt
pip install -r requirements/dev.txt
```

**After:**
```bash
pip install .                    # Core dependencies
pip install ".[gui]"             # Core + GUI
pip install ".[dev]"             # Core + development tools
pip install ".[full]"            # Everything
```

### 2. Update CI/CD Pipelines

**Before:**
```yaml
- name: Install dependencies
  run: |
    pip install -r requirements/core.txt
    pip install -r requirements/dev.txt
```

**After:**
```yaml
- name: Install dependencies
  run: pip install -e ".[dev]"
```

### 3. Update Docker Files

**Before:**
```dockerfile
COPY requirements/ requirements/
RUN pip install -r requirements/core.txt
```

**After:**
```dockerfile
COPY pyproject.toml setup.py ./
RUN pip install .
```

### 4. Update Development Setup

**Before:**
```bash
git clone repo
cd repo
pip install -r requirements/dev.txt
```

**After:**
```bash
git clone repo
cd repo
pip install -e ".[dev]"
```

## Benefits of the New Approach

### 1. **Standards Compliance**
- Uses PEP 518/621 standards
- Better tool compatibility
- Future-proof configuration

### 2. **Simplified Dependency Management**
- Single source of truth
- No duplicate dependency lists
- Automatic dependency resolution

### 3. **Better Optional Dependencies**
- Clear separation of concerns
- Install only what you need
- Easier to maintain

### 4. **Improved Development Experience**
- Faster installation with modern tools
- Better integration with IDEs
- Cleaner project structure

## Troubleshooting

### ImportError after migration
If you encounter import errors:
```bash
# Reinstall in development mode
pip uninstall neurpi
pip install -e ".[dev]"
```

### Missing dependencies
If dependencies seem missing:
```bash
# Install full dependency set
pip install ".[full]"
```

### Legacy scripts still referencing requirements/
Update any scripts that reference the old requirements files:
- Replace file paths with dependency groups
- Use `pip install ".[group]"` syntax
- Update documentation

## Platform-Specific Notes

### Raspberry Pi
Hardware dependencies are automatically included only on Linux:
```toml
"RPi.GPIO>=0.7.1; sys_platform == 'linux'"
```

### Development Machines
Use the dev extra for development tools:
```bash
pip install -e ".[dev]"
```

## Validation

After migration, verify everything works:
```bash
# Test installation
pip install -e ".[full]"

# Test imports
python -c "import neurpi; print('Success!')"

# Test CLI
neurpi --help
```

## Support

If you encounter issues during migration:
1. Check this guide first
2. Verify Python version compatibility (3.8+)
3. Try installing with verbose output: `pip install -v -e ".[full]"`
4. Open an issue if problems persist

The migration should be seamless for most users, with the main benefit being a cleaner, more maintainable dependency structure.
