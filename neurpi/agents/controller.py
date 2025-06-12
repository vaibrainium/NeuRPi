"""
NeuRPi Controller Module.

This module provides the main Controller class for managing experimental rigs,
subjects, and networking in the NeuRPi system.
"""

from __future__ import annotations

import importlib
import os
import signal
import sys
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

try:
    from PyQt6 import QtWidgets
except ImportError:
    try:
        from PyQt5 import QtWidgets
    except ImportError:
        QtWidgets = None


from neurpi.gui.main_gui import Application
from neurpi.loggers.logger import init_logger
from neurpi.networking import ControllerStation, Net_Node
from neurpi.prefs import prefs
from neurpi.utils import code_to_str


class RigState(Enum):
    """Enumeration of possible rig states."""

    IDLE = "IDLE"
    INITIALIZED = "INITIALIZED"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    OFFLINE = "OFFLINE"


class MessageType(Enum):
    """Enumeration of message types handled by the controller."""

    STATE = "STATE"
    PING = "PING"
    CHANGE = "CHANGE"
    DATA = "DATA"
    CONTINUOUS = "CONTINUOUS"
    STREAM = "STREAM"
    HANDSHAKE = "HANDSHAKE"
    SESSION_FILES = "SESSION_FILES"


@dataclass
class RigInfo:
    """Data class representing rig information."""

    ip: str = ""
    state: RigState | None = None
    prefs: dict[str, Any] | None = None
    subjects: list | None = None

    def __post_init__(self) -> None:
        """Initialize default values for optional fields."""
        if self.prefs is None:
            self.prefs = {}
        if self.subjects is None:
            self.subjects = []


@dataclass
class SessionInfo:
    """Data class representing session information."""

    subject_id: str
    rig_id: str
    protocol: str
    experiment: str
    configuration: str


class MessageHandler(ABC):
    """Abstract base class for message handlers."""

    @abstractmethod
    def handle_ping(self, value: dict[str, Any]) -> None:
        """Handle PING messages."""

    @abstractmethod
    def handle_state(self, value: dict[str, Any]) -> None:
        """Handle STATE messages."""

    @abstractmethod
    def handle_handshake(self, value: dict[str, Any]) -> None:
        """Handle HANDSHAKE messages."""

    @abstractmethod
    def handle_data(self, value: dict[str, Any]) -> None:
        """Handle DATA messages."""

    @abstractmethod
    def handle_change(self, value: dict[str, Any]) -> None:
        """Handle CHANGE messages."""

    @abstractmethod
    def handle_session_files(self, value: dict[str, Any]) -> None:
        """Handle SESSION_FILES messages."""


class RigManager:
    """Manages rig-related operations."""

    def __init__(self, logger) -> None:
        """Initialize the rig manager."""
        self._rigs: OrderedDict = OrderedDict()
        self.logger = logger

    @property
    def rigs(self) -> OrderedDict:
        """Get the rigs dictionary."""
        return self._rigs

    def add_rig(self, name: str, ip: str = "", rig_prefs: dict | None = None) -> None:
        """Add a new rig to the registry."""
        rig_info = RigInfo(ip=ip, prefs=rig_prefs or {})
        self._rigs[name] = {
            "ip": rig_info.ip,
            "prefs": rig_info.prefs,
            "subjects": rig_info.subjects,
            "state": rig_info.state.value if rig_info.state else None,
        }
        self.logger.info("Added new rig: %s", name)

    def update_rig_state(self, rig_id: str, state: str | RigState) -> None:
        """Update the state of a rig."""
        if isinstance(state, str):
            try:
                state = RigState(state)
            except ValueError:
                self.logger.warning("Invalid state '%s' for rig %s", state, rig_id)
                return

        if rig_id in self._rigs:
            self._rigs[rig_id]["state"] = state.value
            self.logger.debug("Updated rig %s state to %s", rig_id, state.value)
        else:
            self.logger.warning("Attempted to update state for unknown rig: %s", rig_id)

    def get_rig_state(self, rig_id: str) -> RigState | None:
        """Get the current state of a rig."""
        if rig_id in self._rigs and "state" in self._rigs[rig_id]:
            state_value = self._rigs[rig_id]["state"]
            if state_value:
                try:
                    return RigState(state_value)
                except ValueError:
                    self.logger.warning("Invalid state value '%s' for rig %s", state_value, rig_id)
        return None

    def rig_exists(self, rig_id: str) -> bool:
        """Check if a rig exists in the registry."""
        return rig_id in self._rigs


class NetworkManager:
    """Manages networking operations."""

    def __init__(self, controller_instance) -> None:
        """Initialize the network manager."""
        self.controller = controller_instance
        self.logger = controller_instance.logger
        self.heartbeat_timer: threading.Timer | None = None

    def initialize_networking(self, rigs: OrderedDict, listens: dict[str, callable]) -> tuple:
        """Initialize networking components."""
        try:
            networking = ControllerStation(rigs)
            networking.start()
            self.logger.info("Station object initialized")

            node = Net_Node(
                id="_T",
                upstream="T",
                port=prefs.get("MSGPORT"),
                listens=listens,
                instance=False,
            )
            self.logger.info("Net Node initialized")

            return networking, node

        except Exception as e:
            self.logger.exception("Failed to initialize networking: %s", e)
            raise

    def start_heartbeat(self, node: Net_Node, duration: int = 10) -> None:
        """Start the heartbeat mechanism."""
        def heartbeat_impl(once: bool = False) -> None:
            node.send("T", "INIT", repeat=False, flags={"NOREPEAT": True})

            if not once:
                self.heartbeat_timer = threading.Timer(duration, heartbeat_impl)
                self.heartbeat_timer.daemon = True
                self.heartbeat_timer.start()

        heartbeat_impl()

    def stop_heartbeat(self) -> None:
        """Stop the heartbeat mechanism."""
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
            self.heartbeat_timer = None


class ExperimentManager:
    """Manages experiment-related operations."""

    def __init__(self, controller_instance) -> None:
        """Initialize the experiment manager."""
        self.controller = controller_instance
        self.logger = controller_instance.logger

    def prepare_session_config(self, session_info: SessionInfo):
        """Prepare session configuration from session info."""
        try:
            return importlib.import_module(
                f"protocols.{session_info.protocol}.{session_info.experiment}."
                f"config.{session_info.configuration}",
            )
        except ImportError as e:
            self.logger.exception("Failed to load session config: %s", e)
            raise

    def initiate_subject(self, session_info: SessionInfo, session_config):
        """Initialize a subject object."""
        try:
            subject_module = importlib.import_module(
                f"protocols.{session_info.protocol}.core.data_model.subject",
            )

            subject = subject_module.Subject(
                session_info=session_info,
                session_config=session_config,
            )

            subject_config = subject.initiate_config()
            return subject, subject_config

        except ImportError as e:
            self.logger.exception("Failed to initialize subject: %s", e)
            raise

    def verify_hardware_requirements(self, session_config) -> bool:
        """Verify hardware requirements for the session."""
        # TODO(maintainer): Implement hardware verification on the rig
        # https://github.com/example/neurpi/issues/123
        return True

    def start_task_gui(self, session_info: SessionInfo):
        """Start the task GUI for the experiment."""
        try:
            gui_module = importlib.import_module(
                f"protocols.{session_info.protocol}.core.gui.task_gui",
            )
            return gui_module.TaskGUI
        except ImportError as e:
            self.logger.exception("Failed to load task GUI: %s", e)
            raise


class ControllerMessageHandler(MessageHandler):
    """Concrete implementation of MessageHandler for the Controller."""

    def __init__(self, controller_instance):
        """Initialize with reference to controller instance."""
        self.controller = controller_instance

    def handle_ping(self, value: dict[str, Any]) -> None:
        """Handle PING messages."""
        # Only our Station object should ever ping us, because
        # we otherwise want it handling any pings on our behalf.
        self.controller.logger.debug("PING received: %s", value)

    def handle_state(self, value: dict[str, Any]) -> None:
        """Handle STATE messages from rigs."""
        rig_id = value.get("rig")
        state = value.get("state")

        if not rig_id or not state:
            self.controller.logger.warning("Received incomplete state message: %s", value)
            return

        self.controller.logger.debug("Updating rig state: %s", value)

        if rig_id not in self.controller.rigs:
            self.controller.logger.info("Got state info from an unknown rig, adding...")
            self.controller.new_rig(name=rig_id)

        self.controller.rig_manager.update_rig_state(rig_id, state)

        if state == RigState.INITIALIZED.value:
            # Waiting for rig to initiate hardware and start session
            # Only call start_experiment if the rig GUI exists (experiment was started from GUI)
            if hasattr(self.controller, "rigs_gui") and rig_id in self.controller.rigs_gui:
                self.controller.rigs_gui[rig_id].start_experiment()

        # Update GUI
        self.controller.update_rig_availability()

    def handle_handshake(self, value: dict[str, Any]) -> None:
        """Handle HANDSHAKE messages from rigs."""
        rig_id = value.get("rig")
        if not rig_id:
            self.controller.logger.warning("Received handshake without rig ID: %s", value)
            return

        self.controller.logger.info("HANDSHAKE RECEIVED from %s", rig_id)

        if rig_id in self.controller.rigs:
            self.controller.rigs[rig_id]["ip"] = value.get("ip", "")
            self.controller.rigs[rig_id]["state"] = value.get("state", "")
            self.controller.rigs[rig_id]["prefs"] = value.get("prefs", {})
        else:
            self.controller.new_rig(
                name=rig_id,
                ip=value.get("ip", ""),
                rig_prefs=value.get("prefs", {}),
            )

        self.controller.update_rig_availability()

    def handle_data(self, value: dict[str, Any]) -> None:
        """Handle DATA messages from rigs."""
        try:
            if hasattr(self.controller, "message_to_taskgui"):
                self.controller.message_to_taskgui(value)
        except Exception:
            self.controller.logger.exception("Could not update GUI with data")

    def handle_change(self, value: dict[str, Any]) -> None:
        """Handle CHANGE messages from rigs."""
        # Currently no specific handling needed beyond logging
        self.controller.logger.debug("Received change message: %s", value)

    def handle_session_files(self, value: dict[str, Any]) -> None:
        """Handle SESSION_FILES messages from rigs."""
        try:
            if hasattr(self.controller, "message_to_taskgui"):
                self.controller.message_to_taskgui(value)
        except Exception:
            self.controller.logger.exception("Could not update GUI with session files")


class Controller(Application):
    """Controller class to initiate and manage all downstream agents."""

    def __init__(self) -> None:
        """Initialize the Controller."""
        super().__init__()

        # Store instance for signal handling
        globals()["_CONTROLLER"] = self

        # Initialize managers
        self.logger = init_logger(self)
        self.rig_manager = RigManager(self.logger)
        self.network_manager = NetworkManager(self)
        self.experiment_manager = ExperimentManager(self)

        # Initialize message handler with composition
        self.message_handler = ControllerMessageHandler(self)

        # Networking attributes
        self.node = None
        self.networking = None
        self.heartbeat_dur = 10

        # Data attributes
        self.subjects = {}  # Dict of our open subject objects

        # Setup message handlers
        self._setup_message_handlers()

        # Initialize networking
        self._initialize_networking()

        # Initial setup
        self._perform_initial_setup()

        self.logger.info("Controller Initialized")

    def _setup_message_handlers(self) -> None:
        """Setup the message handling dictionary."""
        self.listens = {
            MessageType.STATE.value: self.message_handler.handle_state,
            MessageType.PING.value: self.message_handler.handle_ping,
            MessageType.CHANGE.value: self.message_handler.handle_change,
            MessageType.DATA.value: self.message_handler.handle_data,
            MessageType.CONTINUOUS.value: self.message_handler.handle_data,
            MessageType.STREAM.value: self.message_handler.handle_data,
            MessageType.HANDSHAKE.value: self.message_handler.handle_handshake,
            MessageType.SESSION_FILES.value: self.message_handler.handle_session_files,
        }

    def _initialize_networking(self) -> None:
        """Initialize networking components."""
        try:
            self.networking, self.node = self.network_manager.initialize_networking(
                self.rigs, self.listens,
            )
        except Exception:
            self.logger.exception("Failed to initialize networking")
            raise

    def _perform_initial_setup(self) -> None:
        """Perform initial setup tasks."""
        # Send an initial ping looking for our rigs
        self.node.send("T", "INIT")        # Check if we need to add rigs
        if len(self.rigs) == 0:
            # TODO(maintainer): Implement communication with GUI to add new rig
            # https://github.com/example/neurpi/issues/124
            pass

    @property
    def rigs(self) -> OrderedDict:
        """Get the rigs dictionary from the rig manager."""
        return self.rig_manager.rigs

    def new_rig(
        self,
        name: str | None = None,
        ip: str = "",
        rig_prefs: dict | None = None,
    ) -> None:
        """Make a new entry in the rigs registry."""
        if name is None:
            self.logger.warning("Cannot add rig without a name")
            return
        self.rig_manager.add_rig(name, ip, rig_prefs)

    # Message handler delegate methods for backward compatibility
    def handle_ping(self, value: dict[str, Any]) -> None:
        """Handle PING messages."""
        return self.message_handler.handle_ping(value)

    def handle_state(self, value: dict[str, Any]) -> None:
        """Handle STATE messages from rigs."""
        return self.message_handler.handle_state(value)

    def handle_handshake(self, value: dict[str, Any]) -> None:
        """Handle HANDSHAKE messages from rigs."""
        return self.message_handler.handle_handshake(value)

    def handle_data(self, value: dict[str, Any]) -> None:
        """Handle DATA messages from rigs."""
        return self.message_handler.handle_data(value)

    def handle_change(self, value: dict[str, Any]) -> None:
        """Handle CHANGE messages from rigs."""
        return self.message_handler.handle_change(value)

    def handle_session_files(self, value: dict[str, Any]) -> None:
        """Handle SESSION_FILES messages from rigs."""
        return self.message_handler.handle_session_files(value)# Backward compatibility methods (keeping original method names)
    def l_ping(self, value: dict[str, Any]) -> None:
        """Legacy ping handler for backward compatibility."""
        self.handle_ping(value)

    def l_state(self, value: dict[str, Any]) -> None:
        """Legacy state handler for backward compatibility."""
        self.handle_state(value)

    def l_handshake(self, value: dict[str, Any]) -> None:
        """Legacy handshake handler for backward compatibility."""
        self.handle_handshake(value)

    def l_data(self, value: dict[str, Any]) -> None:
        """Legacy data handler for backward compatibility."""
        self.handle_data(value)

    def l_change(self, value: dict[str, Any]) -> None:
        """Legacy change handler for backward compatibility."""
        self.handle_change(value)

    def l_session_files(self, value: dict[str, Any]) -> None:
        """Legacy session files handler for backward compatibility."""
        self.handle_session_files(value)

    def ping_rig(self, rig: str) -> None:
        """Send a ping to a specific rig."""
        self.node.send(rig, "PING")

    def heartbeat(self, once: bool = False) -> None:
        """Send periodic INIT messages to check the status of connected rigs."""
        self.network_manager.start_heartbeat(self.node, self.heartbeat_dur)

    def message_from_taskgui(self, message: dict[str, Any]) -> None:
        """Handle messages from task GUI."""
        if message.get("to") == "main_gui":
            if message.get("key") == "KILL":
                if hasattr(self, "remove_rig"):
                    self.remove_rig(message["rig_id"])
        else:
            self.node.send(
                to=message["to"],
                key=message["key"],
                value=message["value"],
            )

    def update_rig_availability(self) -> None:
        """Update the GUI with available rigs."""
        if not hasattr(self, "main_gui"):
            return

        for key in self.rigs.keys():
            display_name = code_to_str(key)
            if self.main_gui.rig_id.findText(display_name) == -1:
                # Add Rig option to the GUI
                self.main_gui.rig_id.addItem(display_name)

    def prepare_session_config(self, session_info) -> Any:
        """Prepare session configuration."""
        return self.experiment_manager.prepare_session_config(session_info)

    def initiate_subject(self, session_info, session_config) -> Any:
        """Initialize a subject object."""
        subject, subject_config = self.experiment_manager.initiate_subject(
            session_info, session_config,
        )
        self.subjects[session_info.subject_id] = subject
        return subject_config

    def verify_hardware_requirements(self, session_config) -> bool:
        """Verify hardware requirements."""
        return self.experiment_manager.verify_hardware_requirements(session_config)

    def start_experiment(self) -> None:
        """Start an experiment."""
        if not hasattr(self, "verify_session_info"):
            self.logger.error("verify_session_info method not available")
            return

        session_info = self.verify_session_info()
        if not session_info:
            return

        rig_state = self.rig_manager.get_rig_state(session_info.rig_id)
        if rig_state != RigState.IDLE:
            if hasattr(self, "critical_message"):
                self.critical_message("Rig is not available to start experiment")
            return

        try:
            # Gather session configuration
            session_config = self.prepare_session_config(session_info)

            # Initialize subject
            subject_config = self.initiate_subject(session_info, session_config)

            # Verify hardware requirements
            self.verify_hardware_requirements(session_config)

            # Send message to rig to start
            self.node.send(
                to=session_info.rig_id,
                key="START",
                value={
                    "session_info": session_info,
                    "subject_config": subject_config,
                },
                flags={"NOLOG": True},
            )

            # Start Task GUI
            task_gui_class = self.experiment_manager.start_task_gui(session_info)

            if hasattr(self, "add_new_rig"):
                self.add_new_rig(
                    id=session_info.rig_id,
                    task_gui=task_gui_class,
                    session_info=session_info,
                    subject=self.subjects[session_info.subject_id],
                )

                if hasattr(self, "rigs_gui") and session_info.rig_id in self.rigs_gui:
                    self.rigs_gui[session_info.rig_id].set_rig_configuration(
                        self.rigs[session_info.rig_id]["prefs"],
                    )

        except Exception:
            self.logger.exception("Failed to start experiment")

    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # TODO(maintainer): Check if any subjects are currently running,
        # pop dialog asking if we want to stop
        # https://github.com/example/neurpi/issues/125

        # Close all subject files
        for subject in self.subjects.values():
            if hasattr(subject, "running") and subject.running is True:
                if hasattr(subject, "stop_run"):
                    subject.stop_run()

        # Stop networking
        try:
            self.node.send(key="KILL")
            time.sleep(0.5)
            self.node.release()
            self.logger.debug("Released net node and sent kill message to station")
        except Exception:
            self.logger.exception("Error during networking cleanup")

        event.accept()


# Global cleanup functions
def _cleanup_subjects() -> None:
    """Helper function to cleanup subjects."""
    controller = globals().get("_CONTROLLER")
    if not controller:
        return

    for subject in controller.subjects.values():
        if hasattr(subject, "running") and subject.running is True:
            if hasattr(subject, "stop_run"):
                subject.stop_run()


def _cleanup_networking() -> None:
    """Helper function to cleanup networking."""
    controller = globals().get("_CONTROLLER")
    if not controller:
        return

    # Stop networking station
    if hasattr(controller, "networking") and controller.networking is not None:
        try:
            controller.networking.send(key="KILL")
            time.sleep(0.2)
            if controller.networking.is_alive():
                controller.networking.terminate()
                controller.networking.join(timeout=1.0)
                if controller.networking.is_alive():
                    print("Force killing networking process...")
                    controller.networking.kill()
        except Exception as e:
            print(f"Error stopping networking: {e}")
            try:
                controller.networking.kill()
            except Exception:
                pass

    # Stop node
    if hasattr(controller, "node") and controller.node is not None:
        try:
            controller.node.send(key="KILL")
            time.sleep(0.2)
            controller.node.release()
        except Exception as e:
            print(f"Error stopping node: {e}")


def signal_handler(sig, frame) -> None:
    """Handle SIGINT (Ctrl+C) to gracefully exit the application."""
    print("\nReceived Ctrl+C, shutting down gracefully...")

    try:
        _cleanup_subjects()
        _cleanup_networking()
    except Exception as e:
        print(f"Error during shutdown: {e}")

    # Exit the application
    QtWidgets.QApplication.quit()
    sys.exit(0)


def main() -> None:
    """Main entry point for the Controller application."""
    # Set virtual environment using relative path
    script_dir = Path(__file__).parent
    venv_path = script_dir.parent.parent / ".venv"

    if venv_path.exists():
        os.environ["VIRTUAL_ENV"] = str(venv_path)
        os.environ["PATH"] = (
            str(venv_path / "Scripts") + os.pathsep + os.environ.get("PATH", "")
        )
        sys.path.insert(0, str(venv_path / "Lib" / "site-packages"))

    # Add the parent directory to Python path if needed
    sys.path.insert(0, str(Path(__file__).parent.parent))

    # Add the project root to the path to ensure protocols can be imported
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    import __main__
    if not hasattr(__main__, "__package__") or __main__.__package__ is None:
        __main__.__package__ = "neurpi.agents"

    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    app = QtWidgets.QApplication(sys.argv)

    # Configure prefs for controller mode
    from neurpi.prefs import configure_prefs
    configure_prefs(mode="controller")

    # Store the controller instance globally for signal handler access
    globals()["_CONTROLLER"] = Controller()

    sys.exit(app.exec())


if __name__ == "__main__":
    _CONTROLLER = None
    main()

