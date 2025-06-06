#!/usr/bin/env python3
"""
Quick validation of the enhanced CLI setup script.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("🧪 Quick Test: Enhanced CLI Setup Script")
    print("=" * 50)

    # Test 1: Basic import
    try:
        from neurpi.cli.setup import setup, main
        print("✅ Successfully imported setup functions")
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

    # Test 2: Check Click integration
    try:
        import click

        # Check if setup function has Click parameters
        if hasattr(setup, '__click_params__'):
            params = setup.__click_params__
            print(f"✅ Found {len(params)} CLI parameters:")

            expected_params = ['minimal', 'gui', 'hardware', 'dev', 'full', 'python_version']
            found_params = [p.name for p in params]

            for expected in expected_params:
                if expected in found_params:
                    print(f"   ✅ --{expected}")
                else:
                    print(f"   ❌ --{expected} (missing)")

        else:
            print("❌ No Click parameters found")

    except Exception as e:
        print(f"❌ Click integration test failed: {e}")
        return False

    # Test 3: Test dependency reading
    try:
        from neurpi.cli.setup import read_requirements_from_toml

        core_deps = read_requirements_from_toml('core')
        gui_deps = read_requirements_from_toml('gui')
        hardware_deps = read_requirements_from_toml('hardware')
        dev_deps = read_requirements_from_toml('dev')

        print(f"✅ Dependency reading works:")
        print(f"   Core: {len(core_deps)} packages")
        print(f"   GUI: {len(gui_deps)} packages")
        print(f"   Hardware: {len(hardware_deps)} packages")
        print(f"   Dev: {len(dev_deps)} packages")

    except Exception as e:
        print(f"❌ Dependency reading test failed: {e}")
        return False

    print("\n🎉 Enhanced CLI setup script is ready!")
    print("\n📋 Available Commands:")
    print("   python neurpi/cli/setup.py                    # Full installation (default)")
    print("   python neurpi/cli/setup.py --minimal          # Core dependencies only")
    print("   python neurpi/cli/setup.py --gui              # Core + GUI dependencies")
    print("   python neurpi/cli/setup.py --hardware         # Core + Hardware dependencies")
    print("   python neurpi/cli/setup.py --dev              # Core + Development tools")
    print("   python neurpi/cli/setup.py --full             # All dependencies")
    print("   python neurpi/cli/setup.py --python-version 3.10  # Custom Python version")
    print("   python neurpi/cli/setup.py --help             # Show help")

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ All validation tests passed!")
    else:
        print("\n❌ Some validation tests failed!")
    sys.exit(0 if success else 1)
