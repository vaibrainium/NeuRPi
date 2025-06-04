# neurpi.gui
"""
NeuRPi GUI Package

Provides unified GUI interfaces for NeuRPi Terminal operations.
Supports both legacy and modern GUI implementations with automatic
migration and compatibility layers.
"""

# Import the unified GUI system
try:
    from .controller_window import ControllerWindow
    from .gui_manager import GUIManager, create_gui, get_available_guis

    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    GUIManager = None
    create_gui = None
    get_available_guis = None
    ControllerWindow = None


# Export main interface
__all__ = [
    "GUI_AVAILABLE",
    "ControllerWindow",
    "GUIManager",
    "create_gui",
    "get_available_guis",
]


# Default GUI creation function for easy access
def create_neurpi_gui(terminal=None):
    """
    Create a NeuRPi GUI instance with automatic selection of the best available GUI.

    Args:
        terminal: Terminal instance to connect to
        gui_type: Type of GUI to create ("auto", "unified", "simple", "old")

    Returns:
        GUI instance ready to run

    """
    if not GUI_AVAILABLE:
        raise ImportError(
            "No GUI implementation available. Please install PyQt6: pip install PyQt6",
        )

    return create_gui(terminal)
