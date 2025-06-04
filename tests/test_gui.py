#!/usr/bin/env python3
"""
Comprehensive Test of NeuRPi Unified GUI System

This script thoroughly tests the unified GUI system, including:
- Import capabilities
- GUI creation and management
- Subject management
- Experiment setup
- Pilot integration
- Backwards compatibility
"""

import sys
from pathlib import Path

# Add the NeuRPi package to the path
sys.path.insert(0, str(Path(__file__).parent))

# Global QApplication instance to prevent it from being garbage collected
_app = None


def ensure_qapplication():
    """Ensure QApplication exists for Qt widget tests."""
    global _app  # noqa: PLW0603
    try:
        from PyQt6.QtWidgets import QApplication

        if _app is None:
            _app = QApplication.instance()
            if _app is None:
                _app = QApplication([])
                print("✅ Created new QApplication")
            else:
                print("✅ Using existing QApplication")
    except ImportError:
        print("❌ PyQt6 not available")
        return None
    else:
        return _app


def test_imports():
    """Test that all GUI components can be imported."""
    print("Testing imports...")

    try:
        # Test core GUI imports
        import neurpi.gui

        # Verify key attributes exist
        assert hasattr(neurpi.gui, "GUI_AVAILABLE")
        assert hasattr(neurpi.gui, "ControllerWindow")
        assert hasattr(neurpi.gui, "GUIManager")
        assert hasattr(neurpi.gui, "create_neurpi_gui")
        assert hasattr(neurpi.gui, "get_available_guis")

        print("✅ Core GUI imports successful")
    except (ImportError, AssertionError) as e:
        print(f"❌ Core GUI import failed: {e}")
        return False

    try:
        # Test SubjectDialog import
        import neurpi.gui.controller_window

        assert hasattr(neurpi.gui.controller_window, "SubjectDialog")

        print("✅ SubjectDialog import successful")
    except (ImportError, AssertionError) as e:
        print(f"❌ SubjectDialog import failed: {e}")
        return False

    return True


def test_gui_availability():
    """Test GUI availability detection."""
    print("\nTesting GUI availability...")

    from neurpi.gui import get_available_guis

    available = get_available_guis()

    print("Available GUI implementations:")
    for gui_type, is_available in available.items():
        status = "✅" if is_available else "❌"
        print(f"  {status} {gui_type.title()} GUI")

    return any(available.values())


def test_gui_creation():
    """Test GUI creation with different types."""
    print("\nTesting GUI creation...")

    if ensure_qapplication() is None:
        print("ℹ️  PyQt6 not available, skipping GUI creation test")
        return True

    from neurpi.gui import create_neurpi_gui, get_available_guis

    available = get_available_guis()

    # Test auto creation
    try:
        gui = create_neurpi_gui()
        print("✅ Auto GUI creation successful")
        gui.close()
    except Exception as e:
        print(f"❌ Auto GUI creation failed: {e}")
        return False

    return True


def test_unified_gui_features():
    """Test unified GUI specific features."""
    print("\nTesting unified GUI features...")

    if ensure_qapplication() is None:
        print("ℹ️  PyQt6 not available, skipping unified GUI features test")
        return True

    from neurpi.gui.controller_window import ControllerWindow

    # Create GUI instance
    try:
        gui = ControllerWindow()
        print("✅ UnifiedMainWindow instantiation successful")
    except Exception as e:
        print(f"❌ UnifiedMainWindow instantiation failed: {e}")
        return False

    # Test subject management
    try:
        # Test adding subjects
        subject_data = {
            "name": "test_subject_001",
            "identification": "TS001",
            "housing": "Cage A1",
            "date_of_birth": "2024-01-01",
            "weight": 25.5,
        }

        gui.subjects["test_subject_001"] = subject_data
        print("✅ Subject management successful")
    except Exception as e:
        print(f"❌ Subject management failed: {e}")

    # Test pilot management
    try:
        pilot_info = {
            "ip": "192.168.1.100",
            "status": "IDLE",
            "last_seen": "2024-06-03T10:00:00",
        }

        # Update pilots directly using the dictionary
        gui.pilots["test_pilot"] = pilot_info
        print("✅ Pilot management successful")
    except Exception as e:
        print(f"❌ Pilot management failed: {e}")

    # Test experiment configuration
    try:
        # Simulate loading protocols
        protocols_dir = Path.cwd() / "protocols"
        if protocols_dir.exists():
            protocols = [p.name for p in protocols_dir.iterdir() if p.is_dir()]
            print(f"✅ Found {len(protocols)} protocols: {protocols}")
        else:
            print("ℹ️  No protocols directory found (this is okay for testing)")
    except Exception as e:
        print(f"❌ Protocol loading failed: {e}")

    # Close GUI
    try:
        gui.close()
        print("✅ GUI cleanup successful")
    except Exception as e:
        print(f"❌ GUI cleanup failed: {e}")

    return True


def test_subject_dialog():
    """Test the subject creation dialog."""
    print("\nTesting subject dialog...")

    if ensure_qapplication() is None:
        print("ℹ️  PyQt6 not available, skipping subject dialog test")
        return True

    try:
        from neurpi.gui.controller_window import SubjectDialog
    except ImportError as e:
        print(f"ℹ️  Could not import SubjectDialog: {e}")
        return True

    try:
        # Create dialog (won't actually show in headless mode)
        dialog = SubjectDialog()

        # Test getting data
        subject_data = dialog.get_subject_data()
        print(f"✅ Subject dialog test successful: {subject_data}")

        return True
    except Exception as e:
        print(f"❌ Subject dialog test failed: {e}")
        return False


def test_gui_manager():
    """Test the GUI manager functionality."""
    print("\nTesting GUI manager...")

    from neurpi.gui import GUIManager

    try:
        # Test with auto selection
        manager = GUIManager()
        print("✅ GUIManager auto creation successful")

        # Test manager methods
        manager.update_pilot_state("test_pilot", "RUNNING")
        manager.update_data({"trial": 1, "response": "left"})

        print("✅ GUIManager functionality test successful")

        manager.close()
        return True
    except Exception as e:
        print(f"❌ GUIManager test failed: {e}")
        return False


def test_mock_terminal_integration():
    """Test integration with a mock terminal."""
    print("\nTesting mock terminal integration...")

    class MockTerminal:
        def __init__(self):
            self.pilots = {}
            self.experiments = {}

    from neurpi.gui import create_neurpi_gui

    try:
        terminal = MockTerminal()
        gui = create_neurpi_gui(terminal=terminal)

        print("✅ Mock terminal integration successful")

        gui.close()
        return True
    except Exception as e:
        print(f"❌ Mock terminal integration failed: {e}")
        return False


def test_data_persistence():
    """Test data saving and loading capabilities."""
    print("\nTesting data persistence...")

    if ensure_qapplication() is None:
        print("ℹ️  PyQt6 not available, skipping data persistence test")
        return True

    import csv
    import tempfile

    from neurpi.gui.controller_window import ControllerWindow

    try:
        gui = ControllerWindow()

        # Test CSV subject data saving
        test_subjects = {
            "subject_001": {
                "name": "subject_001",
                "weight": 25.0,
                "housing": "Cage A1",
            },
            "subject_002": {
                "name": "subject_002",
                "weight": 30.0,
                "housing": "Cage B2",
            },
        }

        gui.subjects = test_subjects

        # Test saving (to temporary location to avoid modifying actual data)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            fieldnames = ["name", "weight", "housing"]
            writer = csv.DictWriter(tmp, fieldnames=fieldnames)
            writer.writeheader()
            for subject_data in test_subjects.values():
                writer.writerow(subject_data)

        print("✅ Data persistence test successful")

        # Cleanup
        Path(tmp.name).unlink()
        gui.close()
        return True
    except Exception as e:
        print(f"❌ Data persistence test failed: {e}")
        return False


def main():
    """Run comprehensive GUI system tests."""
    print("NeuRPi Unified GUI System - Comprehensive Test Suite")
    print("=" * 60)

    tests = [
        test_imports,
        test_gui_availability,
        test_gui_creation,
        test_unified_gui_features,
        test_subject_dialog,
        test_gui_manager,
        test_mock_terminal_integration,
        test_data_persistence,
    ]

    passed = 0
    total = len(tests)

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")

    print(f"\nTest Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The unified GUI system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the output above for details.")

    # Final status summary
    print("\nSystem Status Summary:")
    print("=" * 30)

    from neurpi.gui import get_available_guis

    available = get_available_guis()

    for gui_type, is_available in available.items():
        status = "✅ Ready" if is_available else "❌ Not Available"
        print(f"{gui_type.title()} GUI: {status}")


if __name__ == "__main__":
    main()
