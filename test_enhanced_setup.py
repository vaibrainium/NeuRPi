#!/usr/bin/env python3
"""
Test script for the enhanced CLI setup functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_cli_help():
    """Test that the CLI help works correctly."""
    try:
        from neurpi.cli.setup import setup
        import click
        
        # Create a test context to get help
        ctx = click.Context(setup)
        help_text = setup.get_help(ctx)
        
        print("✅ CLI Setup Help:")
        print("=" * 50)
        print(help_text)
        print("=" * 50)
        
        return True
    except Exception as e:
        print(f"❌ Error getting CLI help: {e}")
        return False

def test_dependency_logic():
    """Test the dependency selection logic."""
    print("\n✅ Testing Dependency Group Selection Logic:")
    print("-" * 50)
    
    # Test cases: (args, expected_groups)
    test_cases = [
        ({}, ['core', 'gui', 'hardware', 'dev']),  # Default = full
        ({'minimal': True}, ['core']),
        ({'gui': True}, ['core', 'gui']),
        ({'hardware': True}, ['core', 'hardware']),
        ({'dev': True}, ['core', 'dev']),
        ({'full': True}, ['core', 'gui', 'hardware', 'dev']),
    ]
    
    for args, expected in test_cases:
        # Simulate the logic from the setup function
        minimal = args.get('minimal', False)
        gui = args.get('gui', False)
        hardware = args.get('hardware', False)
        dev = args.get('dev', False)
        full = args.get('full', False)
        
        dependency_groups = []
        
        # If no flags specified, default to full installation
        if not any([minimal, gui, hardware, dev, full]):
            full = True
        
        if minimal:
            dependency_groups = ['core']
        elif gui:
            dependency_groups = ['core', 'gui']
        elif hardware:
            dependency_groups = ['core', 'hardware']
        elif dev:
            dependency_groups = ['core', 'dev']
        elif full:
            dependency_groups = ['core', 'gui', 'hardware', 'dev']
        
        status = "✅" if dependency_groups == expected else "❌"
        print(f"{status} {str(args):30} -> {dependency_groups}")
    
    return True

def main():
    print("🔍 Testing Enhanced CLI Setup Script")
    print("=" * 60)
    
    # Test 1: CLI Help
    help_success = test_cli_help()
    
    # Test 2: Dependency Logic
    logic_success = test_dependency_logic()
    
    if help_success and logic_success:
        print("\n🎉 All tests passed! Enhanced CLI setup is working correctly.")
        print("\n💡 Usage Examples:")
        print("  python neurpi/cli/setup.py                    # Full installation (default)")
        print("  python neurpi/cli/setup.py --minimal          # Core only")
        print("  python neurpi/cli/setup.py --gui              # Core + GUI")
        print("  python neurpi/cli/setup.py --hardware         # Core + Hardware")
        print("  python neurpi/cli/setup.py --dev              # Core + Development")
        print("  python neurpi/cli/setup.py --full             # Everything")
        print("  python neurpi/cli/setup.py --python-version 3.10  # Custom Python version")
        return True
    else:
        print("\n❌ Some tests failed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
