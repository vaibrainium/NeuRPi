"""
ControllerWindow - Main GUI interface for experiment control and monitoring.

This module provides the main graphical user interface for the NeuRPi system,
allowing users to configure experiments, monitor pilot status, and control
experimental sessions.
"""

import csv
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PyQt6 import QtCore, QtWidgets, uic
from PyQt6.QtWidgets import QApplication, QDialog, QMainWindow, QMessageBox, QWidget


class SubjectDialog(QDialog):
    """Dialog for creating/editing subject information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the user interface."""
        # Load UI file
        ui_dir = Path(__file__).parent
        ui_file = (
            ui_dir / "subject_dialog.ui"
        )  # Use subject_dialog.ui instead of controller_window.ui

        if ui_file.exists():
            # Use loadUiType instead of loadUi for better type checking
            Ui_Form, _ = uic.loadUiType(str(ui_file))
            self.ui = Ui_Form()
            self.ui.setupUi(self)
        else:
            # Create basic dialog if UI file not found
            self.setWindowTitle("Subject Information")
            self.resize(400, 300)

        # Set default values if widgets exist
        if hasattr(self, "dob_edit"):
            self.ui.dob_edit.setDate(QtCore.QDate.currentDate())

    def get_subject_data(self) -> dict[str, Any]:
        """Get subject data from form fields."""
        if not hasattr(self, "subject_id_edit"):
            return {}

        return {
            "name": getattr(self.ui.subject_id_edit, "text", lambda: "")(),
            "species": getattr(self.ui.species_combo, "currentText", lambda: "")(),
            "strain": getattr(self.ui.strain_edit, "text", lambda: "")(),
            "sex": getattr(self.ui.sex_combo, "currentText", lambda: "")(),
            "identification": getattr(
                self.ui.identification_edit,
                "text",
                lambda: "",
            )(),
            "housing": getattr(self.ui.housing_edit, "text", lambda: "")(),
            "date_of_birth": getattr(
                self.ui.dob_edit,
                "date",
                lambda: QtCore.QDate.currentDate(),
            )().toString(),
            "weight": getattr(self.ui.weight_spinbox, "value", lambda: 0)(),
            "water_restricted": getattr(
                self.ui.water_restriction_check,
                "isChecked",
                lambda: False,
            )(),
            "notes": getattr(self.ui.notes_text, "toPlainText", lambda: "")(),
        }


class ControllerWindow(QMainWindow):
    """Main controller window for experiment management."""

    def __init__(self, terminal=None, parent=None):
        super().__init__(parent)

        self.terminal = terminal
        self.app = None
        self.pilots: OrderedDict = OrderedDict()
        self.subjects: dict[str, dict] = {}
        self.protocols: list[str] = []
        self.current_session_info: dict | None = None

        # Task GUI management for tabs
        self.task_guis: dict[str, Any] = {}  # Dictionary to store task GUIs by rig ID

        self._setup_ui()
        self._load_data()
        self._connect_signals()

    def _setup_ui(self):
        """Setup the user interface."""
        # Load UI file
        ui_dir = Path(__file__).parent
        ui_file = ui_dir / "controller_window.ui"

        if ui_file.exists():
            # Use loadUiType instead of loadUi for better type checking
            Ui_Form, _ = uic.loadUiType(str(ui_file))
            self.ui = Ui_Form()
            self.ui.setupUi(self)
        else:
            # Create basic interface if UI file not found
            self.setWindowTitle("NeuRPi Controller")
            self.resize(1200, 800)

            # Create central widget and basic layout
            central_widget = QWidget()
            self.setCentralWidget(central_widget)

        # Setup initial UI state
        self._setup_initial_state()

    def _setup_initial_state(self):
        """Setup initial UI state after widgets are loaded."""
        # Only access widgets if they exist
        if hasattr(self, "main_splitter"):
            self.ui.main_splitter.setSizes([600, 600])

        if hasattr(self, "pilots_table"):
            self.ui.pilots_table.setRowCount(0)
            self.ui.pilots_table.setColumnCount(4)
            self.ui.pilots_table.setHorizontalHeaderLabels(
                ["Name", "IP", "Status", "Last Seen"],
            )

    def _connect_signals(self):
        """Connect widget signals to their handlers."""
        # Only connect signals for widgets that exist
        widget_signal_map = {
            "protocol_combo": ("currentTextChanged", self._update_experiment_list),
            "experiment_combo": ("currentTextChanged", self._update_configuration_list),
            "subject_combo": ("currentTextChanged", self._update_subject_info),
            "new_subject_btn": ("clicked", self._create_new_subject),
            "start_btn": ("clicked", self._start_experiment),
            "stop_btn": ("clicked", self._stop_experiment),
            "refresh_btn": ("clicked", self._refresh_pilots),
            "ping_btn": ("clicked", self._ping_all_pilots),
            "clear_log_btn": ("clicked", self._clear_log),
        }

        for widget_name, (signal_name, handler) in widget_signal_map.items():
            if hasattr(self, widget_name):
                widget = getattr(self, widget_name)
                if hasattr(widget, signal_name):
                    signal = getattr(widget, signal_name)
                    signal.connect(handler)

        # Connect tab change handler if tabs widget exists
        if hasattr(self, "tabs"):
            self.ui.tabs.currentChanged.connect(self._handle_tab_activation_change)

    def _load_data(self):
        """Load protocols and subjects data."""
        self._load_protocols()
        self._load_subjects()

    def _load_protocols(self):
        """Load available protocols."""
        try:
            # Try to get protocols from terminal if available
            if self.terminal and hasattr(self.terminal, "protocols"):
                protocols = list(self.terminal.protocols.keys())
            else:
                # Default protocols
                protocols = ["Training", "Testing", "Free Water"]

            self.protocols = protocols
            if hasattr(self, "protocol_combo"):
                self.ui.protocol_combo.addItems(protocols)

        except Exception as e:
            self._log_message(f"Error loading protocols: {e}")

    def _load_subjects(self):
        """Load subjects from CSV file."""
        try:
            subjects_file = Path("subjects.csv")
            if subjects_file.exists():
                with subjects_file.open("r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.subjects[row.get("name", "")] = row

            self._update_subject_list()

        except Exception as e:
            self._log_message(f"Error loading subjects: {e}")

    def _update_subject_list(self):
        """Update subject combo box."""
        if hasattr(self, "subject_combo"):
            self.ui.subject_combo.clear()
            self.ui.subject_combo.addItems(list(self.subjects.keys()))

    def update_pilot_list(self, pilots: OrderedDict):
        """Update the pilots list from terminal."""
        self.pilots = pilots.copy()
        self._update_pilots_table()
        self._update_rig_list()

    def _update_pilots_table(self):
        """Update the pilots table display."""
        if not hasattr(self, "pilots_table"):
            return

        self.ui.pilots_table.setRowCount(len(self.pilots))

        for row, (name, pilot_info) in enumerate(self.pilots.items()):
            # Name
            self.ui.pilots_table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))

            # IP
            ip = pilot_info.get("ip", "Unknown")
            self.ui.pilots_table.setItem(row, 1, QtWidgets.QTableWidgetItem(ip))

            # Status
            status = pilot_info.get("status", "Unknown")
            self.ui.pilots_table.setItem(row, 2, QtWidgets.QTableWidgetItem(status))

            # Last seen
            last_seen = pilot_info.get("last_seen", "Never")
            self.ui.pilots_table.setItem(row, 3, QtWidgets.QTableWidgetItem(last_seen))

    def _update_rig_list(self):
        """Update rig combo box with available pilots."""
        if not hasattr(self, "rig_combo"):
            return

        self.ui.rig_combo.clear()
        rig_names = list(self.pilots.keys())
        self.ui.rig_combo.addItems(rig_names)

    def _update_experiment_list(self):
        """Update experiment list based on selected protocol."""
        if not hasattr(self, "experiment_combo"):
            return

        protocol = (
            self.ui.protocol_combo.currentText()
            if hasattr(self, "protocol_combo")
            else ""
        )
        self.ui.experiment_combo.clear()

        if protocol and self.terminal and hasattr(self.terminal, "protocols"):
            experiments = self.terminal.protocols.get(protocol, {}).get(
                "experiments",
                [],
            )
            self.ui.experiment_combo.addItems(experiments)

    def _update_configuration_list(self):
        """Update configuration list based on selected protocol/experiment."""
        if not hasattr(self, "configuration_combo"):
            return

        protocol = (
            self.ui.protocol_combo.currentText()
            if hasattr(self, "protocol_combo")
            else ""
        )
        experiment = (
            self.ui.experiment_combo.currentText()
            if hasattr(self, "experiment_combo")
            else ""
        )

        self.ui.configuration_combo.clear()

        if (
            protocol
            and experiment
            and self.terminal
            and hasattr(self.terminal, "protocols")
        ):
            configs = (
                self.terminal.protocols.get(protocol, {})
                .get("configurations", {})
                .get(experiment, [])
            )
            self.ui.configuration_combo.addItems(configs)

    def _update_subject_info(self):
        """Update subject information display."""
        if not hasattr(self, "subject_combo"):
            return

        subject_name = self.ui.subject_combo.currentText()
        subject_info = self.subjects.get(subject_name, {})

        # Update weight and water restriction
        weight = float(subject_info.get("weight", 0))
        water_restricted = (
            subject_info.get("water_restricted", "false").lower() == "true"
        )

        if hasattr(self, "weight_spinbox"):
            self.ui.weight_spinbox.setValue(weight)
        if hasattr(self, "water_restriction_check"):
            self.ui.water_restriction_check.setChecked(water_restricted)

    def _create_new_subject(self):
        """Create a new subject."""
        dialog = SubjectDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            subject_data = dialog.get_subject_data()
            if subject_data.get("name"):
                self.subjects[subject_data["name"]] = subject_data
                self._save_subject(subject_data)
                self._update_subject_list()

    def _save_subject(self, subject_data: dict[str, Any]):
        """Save subject to CSV file."""
        try:
            subjects_file = Path("subjects.csv")
            file_exists = subjects_file.exists()

            with subjects_file.open("a", newline="", encoding="utf-8") as f:
                fieldnames = list(subject_data.keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()
                writer.writerow(subject_data)

        except Exception as e:
            self._log_message(f"Error saving subject: {e}")

    def _start_experiment(self):
        """Start a new experiment."""
        # Get form values
        protocol = (
            self.ui.protocol_combo.currentText()
            if hasattr(self, "protocol_combo")
            else ""
        )
        experiment = (
            self.ui.experiment_combo.currentText()
            if hasattr(self, "experiment_combo")
            else ""
        )
        configuration = (
            self.ui.configuration_combo.currentText()
            if hasattr(self, "configuration_combo")
            else ""
        )
        subject_name = (
            self.ui.subject_combo.currentText()
            if hasattr(self, "subject_combo")
            else ""
        )
        rig_id = self.ui.rig_combo.currentText() if hasattr(self, "rig_combo") else ""

        # Validate required fields
        if not all([protocol, experiment, subject_name, rig_id]):
            QMessageBox.warning(self, "Error", "Please select all required fields")
            return

        # Start experiment via terminal
        if self.terminal:
            success = self.terminal.start_experiment(rig_id, protocol, subject_name)
            if success:
                self._log_message(
                    f"Started experiment: {protocol} for {subject_name} on {rig_id}",
                )
                self._update_experiment_ui(True)

                # Try to load the task GUI for monitoring if not already loaded
                if not self.is_rig_monitoring(rig_id):
                    try:
                        # Create session info dictionary
                        session_info = {
                            "subject_name": subject_name,
                            "protocol": protocol,
                            "experiment": experiment,
                            "configuration": configuration,
                            "rig_id": rig_id,
                        }

                        # Get subject info
                        subject_info = self.subjects.get(subject_name, {})

                        # Try to import the appropriate task GUI class
                        task_gui_class = self._import_task_gui(protocol, experiment)
                        if task_gui_class:
                            self.add_new_rig_tab(
                                rig_id=rig_id,
                                task_gui_class=task_gui_class,
                                session_info=session_info,
                                subject=subject_info,
                            )
                        else:
                            self._log_message(
                                f"No monitoring GUI available for {protocol}/{experiment}",
                            )
                    except Exception as e:
                        self._log_message(f"Could not load monitoring GUI: {e}")
            else:
                self._log_message("Failed to start experiment")
        else:
            self._log_message("No terminal connection available")

    def _stop_experiment(self):
        """Stop the current experiment."""
        rig_id = self.ui.rig_combo.currentText() if hasattr(self, "rig_combo") else ""

        if rig_id and self.terminal:
            success = self.terminal.stop_experiment(rig_id)
            if success:
                self._log_message(f"Stopped experiment on {rig_id}")
                self._update_experiment_ui(False)
            else:
                self._log_message("Failed to stop experiment")

    def _update_experiment_ui(self, running: bool):
        """Update UI state based on experiment status."""
        if hasattr(self, "start_btn"):
            self.ui.start_btn.setEnabled(not running)
        if hasattr(self, "stop_btn"):
            self.ui.stop_btn.setEnabled(running)

    def _refresh_pilots(self):
        """Refresh pilot information."""
        if self.terminal:
            self.terminal.ping_all_pilots()
            self._log_message("Refreshing pilot information...")

    def _ping_all_pilots(self):
        """Ping all pilots to check connectivity."""
        if self.terminal:
            self.terminal.ping_all_pilots()
            self._log_message("Pinging all pilots...")

    def _clear_log(self):
        """Clear the log display."""
        if hasattr(self, "log_text"):
            self.ui.log_text.clear()

    def _log_message(self, message: str):
        """Add a message to the log display."""
        if hasattr(self, "log_text"):
            timestamp = datetime.now(UTC).strftime("%H:%M:%S")
            self.ui.log_text.appendPlainText(f"[{timestamp}] {message}")
        else:
            print(f"LOG: {message}")  # Fallback to console

    def update_pilot_state(self, pilot_name: str, new_state: str):
        """Update pilot state from terminal."""
        if pilot_name in self.pilots:
            self.pilots[pilot_name]["status"] = new_state
            self.pilots[pilot_name]["last_seen"] = datetime.now(
                UTC,
            ).isoformat()
            self._update_pilots_table()

    def log_message(self, message: str):
        """Public method for terminal to log messages."""
        self._log_message(message)

    def run(self):
        """Run the GUI application."""
        if not self.app:
            import sys

            self.app = QApplication(sys.argv)

        self.show()
        return self.app.exec()

    def close(self) -> bool:
        """Close the window and clean up."""
        if self.app:
            self.app.quit()
        return super().close()

    # ==================== Tab Management Functions ====================
    def _handle_tab_activation_change(self, tab_index: int):
        """Handle tab activation changes for task GUIs."""
        # Emit the tabActiveStateChanged signal on the corresponding TaskGUI instance
        for rig_id, task_gui in self.task_guis.items():
            if self._get_tab_index(rig_id) == tab_index:
                if hasattr(task_gui, "tabActiveStateChanged"):
                    task_gui.tabActiveStateChanged.emit(True)
            elif hasattr(task_gui, "tabActiveStateChanged"):
                task_gui.tabActiveStateChanged.emit(False)

    def _get_tab_index(self, tab_name: str, tab_widget=None) -> int | None:
        """Get the index of a tab by name."""
        if not tab_widget and hasattr(self, "tabs"):
            tab_widget = self.ui.tabs
        elif not tab_widget:
            return None

        # Convert tab name to display format
        display_name = self._code_to_str(tab_name)

        for index in range(tab_widget.count()):
            if display_name == tab_widget.tabText(index):
                return index
        return None

    def add_new_rig_tab(
        self,
        rig_id: str = "rig_",
        task_gui_class=None,
        session_info: dict | None = None,
        subject: dict | None = None,
    ):
        """Add a new rig tab with task GUI for detailed monitoring."""
        try:
            if not hasattr(self, "tabs"):
                self._log_message("No tabs widget available for rig monitoring")
                return

            if not task_gui_class:
                self._log_message("No task GUI class provided")
                return

            display_name = self._code_to_str(rig_id)

            # Create the task GUI instance
            self.task_guis[rig_id] = task_gui_class(
                rig_id,
                session_info=session_info,
                subject=subject,
            )

            # Add tab to the tab widget
            tab_index = self.ui.tabs.addTab(self.task_guis[rig_id], display_name)
            self.ui.tabs.setCurrentIndex(tab_index)

            # Connect communication signals if they exist
            if hasattr(self.task_guis[rig_id], "comm_from_taskgui"):
                self.task_guis[rig_id].comm_from_taskgui.connect(
                    self._message_from_taskgui,
                )

            self._log_message(f"Added monitoring tab for rig: {display_name}")

        except Exception as e:
            self._log_message(f"Could not add rig GUI: {e}")

    def remove_rig_tab(self, rig_id: str):
        """Remove a rig tab and clean up the task GUI."""
        try:
            if not hasattr(self, "tabs"):
                return

            index = self._get_tab_index(rig_id)
            if index is not None:
                # Remove the tab
                self.ui.tabs.removeTab(index)
                self.ui.tabs.setCurrentIndex(0)

                # Clean up the task GUI
                if rig_id in self.task_guis:
                    # Disconnect signals if they exist
                    if hasattr(self.task_guis[rig_id], "comm_from_taskgui"):
                        try:
                            self.task_guis[rig_id].comm_from_taskgui.disconnect()
                        except Exception:
                            pass  # Signal might not be connected

                    # Delete the task GUI
                    del self.task_guis[rig_id]

                self._log_message(
                    f"Removed monitoring tab for rig: {self._code_to_str(rig_id)}",
                )

        except Exception as e:
            self._log_message(f"Error removing rig tab: {e}")

    def _message_from_taskgui(self, message: dict):
        """Handle messages from task GUIs."""
        # Log the message or process it as needed
        rig_id = message.get("rig_id", "unknown")
        msg_type = message.get("type", "info")
        content = message.get("content", "")

        self._log_message(f"[{rig_id}] {msg_type}: {content}")

    def message_to_taskgui(self, rig_id: str, message: dict):
        """Send a message to a specific task GUI."""
        if rig_id in self.task_guis:
            if hasattr(self.task_guis[rig_id], "comm_to_taskgui"):
                try:
                    self.task_guis[rig_id].comm_to_taskgui.emit(message)
                except Exception as e:
                    self._log_message(f"Error sending message to {rig_id}: {e}")

    def _code_to_str(self, var: str) -> str:
        """Convert code format to display string format."""
        str_var = var.replace("_", " ")
        str_var = str_var.title()
        return str_var

    def _str_to_code(self, var: str) -> str:
        """Convert display string to code format."""
        code_var = var.replace(" ", "_")
        code_var = code_var.lower()
        return code_var

    def _import_task_gui(self, protocol: str, experiment: str):
        """
        Import the task GUI class for a specific protocol and experiment.

        Args:
            protocol: Protocol name (e.g., 'random_dot_motion')
            experiment: Experiment name (e.g., 'rt_directional_training')

        Returns:
            The task GUI class if found, None otherwise

        """
        try:
            # Convert display names to code format if needed
            protocol_code = self._str_to_code(protocol)
            experiment_code = self._str_to_code(experiment)

            # Try to import the GUI module
            import importlib

            # First try protocol-specific experiment GUI
            try:
                module_path = (
                    f"protocols.{protocol_code}.{experiment_code}.core.gui.task_gui"
                )
                task_gui_module = importlib.import_module(module_path)
                return getattr(task_gui_module, "TaskGUI", None)
            except (ImportError, AttributeError):
                # If not found, try protocol-wide GUI
                try:
                    module_path = f"protocols.{protocol_code}.core.gui.task_gui"
                    task_gui_module = importlib.import_module(module_path)
                    return getattr(task_gui_module, "TaskGUI", None)
                except (ImportError, AttributeError):
                    self._log_message(f"Could not find GUI for {protocol}/{experiment}")
                    return None
        except Exception as e:
            self._log_message(f"Error importing task GUI: {e}")
            return None

    def clear_experiment_controls(self):
        """Clear the experiment control form."""
        try:
            if hasattr(self, "subject_combo"):
                self.ui.subject_combo.setCurrentIndex(0)
            if hasattr(self, "protocol_combo"):
                self.ui.protocol_combo.setCurrentIndex(0)
            if hasattr(self, "experiment_combo"):
                self.ui.experiment_combo.clear()
                self.ui.experiment_combo.addItem("SELECT")
                self.ui.experiment_combo.setCurrentIndex(0)
            if hasattr(self, "configuration_combo"):
                self.ui.configuration_combo.clear()
                self.ui.configuration_combo.addItem("SELECT")
                self.ui.configuration_combo.setCurrentIndex(0)
            if hasattr(self, "rig_combo"):
                self.ui.rig_combo.setCurrentIndex(0)
            if hasattr(self, "weight_spinbox"):
                self.ui.weight_spinbox.setValue(0)

            self._log_message("Cleared experiment controls")

        except Exception as e:
            self._log_message(f"Error clearing controls: {e}")

    def get_active_rigs(self) -> list[str]:
        """Get list of active rig IDs with monitoring tabs."""
        return list(self.task_guis.keys())

    def is_rig_monitoring(self, rig_id: str) -> bool:
        """Check if a rig is currently being monitored."""
        return rig_id in self.task_guis
