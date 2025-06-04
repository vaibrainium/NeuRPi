"""
GUI Migration and Integration Script for NeuRPi

This script helps migrate from the old GUI system to the new unified GUI,
providing compatibility layers and integration utilities.
"""

from pathlib import Path
from typing import Any

try:
    from neurpi.gui.controller_window import ControllerWindow

    NEW_GUI_AVAILABLE = True
except ImportError:
    NEW_GUI_AVAILABLE = False


class GUIManager:
    """
    Unified GUI manager that can work with different GUI implementations.

    This class provides a compatibility layer between old and new GUI systems,
    allowing for gradual migration and backwards compatibility.
    """

    def __init__(self, terminal: Any = None):
        """
        Initialize the GUI manager.

        Args:
            terminal: The terminal instance to connect to
            gui_type: Type of GUI to use ("auto", "unified", "simple", "old")

        """
        self.terminal = terminal
        self.gui_instance = ControllerWindow(self.terminal)

    def _bridge_old_gui(self):
        """Bridge the old GUI to work with the terminal interface."""
        if hasattr(self.gui_instance, "main_gui"):
            # Add compatibility methods to the old GUI
            def update_pilot_state(pilot_name: str, state: str):
                # This would be implemented to update old GUI with pilot state
                pass

            def update_data(data: Any):
                # This would be implemented to update old GUI with data
                pass

            self.gui_instance.update_pilot_state = update_pilot_state
            self.gui_instance.update_data = update_data

    def run(self):
        """Run the GUI."""
        if self.gui_instance:
            if hasattr(self.gui_instance, "run"):
                self.gui_instance.run()
            elif hasattr(self.gui_instance, "show"):
                # For old GUI
                self.gui_instance.show()
                if hasattr(self.gui_instance, "app"):
                    self.gui_instance.app.exec_()

    def close(self):
        """Close the GUI."""
        if self.gui_instance and hasattr(self.gui_instance, "close"):
            self.gui_instance.close()

    def update_pilot_state(self, pilot_name: str, state: str):
        """Update pilot state in the GUI."""
        if self.gui_instance and hasattr(self.gui_instance, "update_pilot_state"):
            self.gui_instance.update_pilot_state(pilot_name, state)

    def update_data(self, data: Any):
        """Update with new data from pilots."""
        if self.gui_instance and hasattr(self.gui_instance, "update_data"):
            self.gui_instance.update_data(data)


def create_gui(terminal: Any = None) -> GUIManager:
    """
    Factory function to create the appropriate GUI instance.

    Args:
        terminal: The terminal instance to connect to

    Returns:
        GUIManager instance

    """
    return GUIManager(terminal)


def get_available_guis() -> dict:
    """Get information about available GUI implementations."""
    return {
        "unified": NEW_GUI_AVAILABLE,
    }


def migrate_old_gui_config():
    """
    Migrate configuration from old GUI to new unified GUI.

    This function can be extended to transfer settings, preferences,
    and data from the old GUI system to the new one.
    """
    old_config_paths = [
        Path.cwd() / "neurpi" / "old_gui",
        Path.cwd() / "config",
        Path.cwd() / "prefs",
    ]

    migration_data = {}

    # Look for old configuration files
    for path in old_config_paths:
        if path.exists():
            # Add migration logic here
            # For now, just record what's available
            migration_data[str(path)] = (
                list(path.iterdir()) if path.is_dir() else [path]
            )

    return migration_data


# Example usage and compatibility layer
def main():
    """Example of how to use the unified GUI system."""
    print("NeuRPi GUI System Status:")
    print("=" * 40)

    available = get_available_guis()
    for gui_type, is_available in available.items():
        status = "✓ Available" if is_available else "✗ Not Available"
        print(f"{gui_type.title()} GUI: {status}")

    if not any(available.values()):
        print("\nNo GUI implementations available!")
        print("Please install PyQt6 or PyQt5 dependencies.")
        return

    # # Migration info
    # migration_data = migrate_old_gui_config()
    # if migration_data:
    #     print(f"\nFound old configuration data in {len(migration_data)} locations")
    #     print("Consider migrating settings to the new unified GUI")


if __name__ == "__main__":
    main()
