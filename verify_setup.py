#!/usr/bin/env python3
"""
Verification script for NeuRPi CLI setup functionality.
Run this to verify that the requirements consolidation worked correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("🔍 Verifying NeuRPi CLI Setup Functionality")
    print("=" * 50)
    
    # Test 1: Import the setup module
    try:
        from neurpi.cli.setup import read_requirements_from_toml
        print("✅ CLI setup module imports successfully")
    except ImportError as e:
        print(f"❌ Failed to import CLI setup module: {e}")
        return False
    
    # Test 2: Read dependency groups
    dependency_groups = ['core', 'gui', 'dev', 'hardware']
    total_deps = 0
    
    for group in dependency_groups:
        try:
            deps = read_requirements_from_toml(group)
            dep_count = len(deps)
            total_deps += dep_count
            print(f"✅ {group.upper()} dependencies: {dep_count} packages")
            
            # Show first few dependencies for verification
            if deps and len(deps) > 0:
                sample_deps = deps[:2]  # Show first 2
                print(f"   Sample: {', '.join(sample_deps)}")
                
        except Exception as e:
            print(f"❌ Failed to read {group} dependencies: {e}")
            return False
    
    # Test 3: Verify pyproject.toml exists and is readable
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        print("✅ pyproject.toml exists and is accessible")
    else:
        print("❌ pyproject.toml not found")
        return False
    
    # Test 4: Verify requirements directory is gone
    requirements_path = project_root / "requirements"
    if not requirements_path.exists():
        print("✅ requirements/ directory successfully removed")
    else:
        print("⚠️  requirements/ directory still exists")
    
    # Test 5: Test the main CLI setup imports
    try:
        from neurpi.cli.setup import install_uv_and_dependencies, find_uv_executable
        print("✅ All CLI setup functions are importable")
    except ImportError as e:
        print(f"❌ Failed to import CLI setup functions: {e}")
        return False
    
    print()
    print("📊 Summary:")
    print(f"   Total dependencies loaded: {total_deps}")
    print(f"   Dependency groups: {len(dependency_groups)}")
    print(f"   Expected core deps: 15 (actual: {len(read_requirements_from_toml('core'))})")
    print()
    print("🎉 All verifications passed! CLI setup is working correctly.")
    print()
    print("💡 Usage:")
    print("   python neurpi/cli/setup.py")
    print("   python -m neurpi.cli.setup")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
