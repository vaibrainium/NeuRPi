import csv
import sys
from datetime import datetime
from pathlib import Path

import yaml
from omegaconf import OmegaConf
from PyQt6 import QtCore, QtWidgets, uic

from neurpi.prefs import prefs
from neurpi.utils import code_to_str, str_to_code

# Load UI files
Ui_Main, mainclass = uic.loadUiType("neurpi/gui/main_gui.ui")
Ui_NewSubject, newsubjectclass = uic.loadUiType("neurpi/gui/new_subject_form.ui")


class Application(mainclass):
    """Main application window for experiment control."""

    def __init__(self):
        super().__init__()
        self.thread = QtCore.QThread()

        # Initialize UI
        self._setup_ui()
        self._setup_new_subject_dialog()
        self._load_initial_data()
        self._connect_signals()

        # Initialize state
        self.rigs_gui = {}
        self.current_session_info = None

    def _setup_ui(self):
        """Setup the main user interface."""
        self.main_gui = Ui_Main()
        self.main_gui.setupUi(self)
        self.show()  # Setup initial UI state
        self._setup_initial_controls()

    def _setup_initial_controls(self):
        """Setup initial state of UI controls."""
        # Don't pre-populate rig_id - matches original behavior where only "SELECT" is available

        # Add response mode options
        response_options = ["Wheel", "Lickport", "Touch"]
        self.main_gui.response_mode.addItems(response_options)

        # Set initial log message
        self._log_message("NeuRPi system initialized")

    def _setup_new_subject_dialog(self):
        """Setup new subject creation dialog."""
        self.new_subject_window = QtWidgets.QDialog()
        self.new_subject_form = Ui_NewSubject()
        self.new_subject_form.setupUi(self.new_subject_window)
        self.new_subject_window.raise_()
        self.new_subject_window.hide()

    def _load_initial_data(self):
        """Load protocols and other initial data."""
        self._load_protocols()

    def _load_protocols(self):
        """Load available protocols from protocols directory."""
        try:
            protocols_path = Path(Path.cwd(), "protocols")
            if not protocols_path.exists():
                self._log_message("Warning: Protocols directory not found")
                return

            list_protocols = ["SELECT"]
            for x in protocols_path.iterdir():
                if x.is_dir() and x.name != "__pycache__":
                    list_protocols.append(code_to_str(x.name))

            self.main_gui.protocol.clear()
            self.main_gui.protocol.addItems(list_protocols)
            self.main_gui.protocol.setCurrentIndex(0)

            self._log_message(f"Loaded {len(list_protocols) - 1} protocols")
        except Exception as e:
            self._log_message(f"Error loading protocols: {e}")

    def _connect_signals(self):
        """Connect all widget signals to their handlers."""
        # Protocol/experiment selection signals
        self.main_gui.rig_id.currentTextChanged.connect(self.reset_protocol_selections)
        self.main_gui.protocol.currentTextChanged.connect(self.add_experiments)
        self.main_gui.experiment.currentTextChanged.connect(self.add_configurations)

        # Control buttons
        self.main_gui.start_experiment.clicked.connect(self.start_experiment)
        self.main_gui.create_new_subject.clicked.connect(self.show_subject_form)
        self.new_subject_form.create_button.clicked.connect(self.create_new_subject)

        # Tab management
        self.main_gui.tabs.currentChanged.connect(self.handleTabActivationChange)

        # Log controls
        if hasattr(self.main_gui, "clear_log_btn"):
            self.main_gui.clear_log_btn.clicked.connect(self._clear_log)

    # ==================== Protocol/Experiment Management ====================

    def reset_protocol_selections(self):
        """Reset protocol, experiment, and configuration selections when rig ID changes."""
        # Reset protocol to "SELECT" (index 0)
        self.main_gui.protocol.setCurrentIndex(0)

        # Clear and reset experiment dropdown
        self.main_gui.experiment.clear()
        self.main_gui.experiment.addItem("SELECT")
        self.main_gui.experiment.setCurrentIndex(0)

        # Clear and reset configuration dropdown
        self.main_gui.configuration.clear()
        self.main_gui.configuration.addItem("SELECT")
        self.main_gui.configuration.setCurrentIndex(0)

        # Log the reset action
        rig_id = self.main_gui.rig_id.currentText()
        if rig_id != "SELECT":
            self._log_message(f"Reset protocol selections due to rig change: {rig_id}")

    def add_experiments(self):
        """Add experiments based on selected protocol."""
        if self.main_gui.protocol.currentText() == "SELECT":
            self.main_gui.experiment.clear()
            self.main_gui.experiment.addItem("SELECT")
            self.main_gui.experiment.setCurrentIndex(0)
            return

        try:
            protocol = str_to_code(self.main_gui.protocol.currentText())
            protocol_path = Path(Path.cwd(), "protocols", protocol)

            self.main_gui.experiment.clear()
            list_experiments = ["SELECT"]

            if protocol_path.exists():
                for x in protocol_path.iterdir():
                    if x.is_dir() and x.name not in ["__pycache__", "core"]:
                        list_experiments.append(code_to_str(x.name))

            self.main_gui.experiment.addItems(list_experiments)
            self.main_gui.experiment.setCurrentIndex(0)

            # Only log if there are actual experiments loaded
            experiment_count = len(list_experiments) - 1
            if experiment_count > 0:
                self._log_message(
                    f"Loaded {experiment_count} experiments for protocol '{self.main_gui.protocol.currentText()}'",
                )
        except Exception as e:
            self._log_message(f"Error loading experiments: {e}")

    def add_configurations(self):
        """Add configurations based on selected experiment."""
        if self.main_gui.experiment.currentText() == "SELECT":
            self.main_gui.configuration.clear()
            self.main_gui.configuration.addItem("SELECT")
            self.main_gui.configuration.setCurrentIndex(0)
            return

        try:
            protocol = str_to_code(self.main_gui.protocol.currentText())
            experiment = str_to_code(self.main_gui.experiment.currentText())
            config_path = Path(Path.cwd(), "protocols", protocol, experiment, "config")

            self.main_gui.configuration.clear()
            list_configurations = ["SELECT"]

            if config_path.exists() and any(config_path.iterdir()):
                for x in config_path.iterdir():
                    if not x.is_dir() and x.name not in ["__pycache__", "core"]:
                        list_configurations.append(code_to_str(x.stem))

            self.main_gui.configuration.addItems(list_configurations)
            self.main_gui.configuration.setCurrentIndex(0)

            # Only log if there are actual configurations loaded
            configuration_count = len(list_configurations) - 1
            if configuration_count > 0:
                self._log_message(
                    f"Loaded {configuration_count} configurations for experiment '{self.main_gui.experiment.currentText()}'",
                )
        except Exception as e:
            self._log_message(f"Error loading configurations: {e}")

    # ==================== Session Management ====================

    def start_experiment(self):
        """Start experiment after verifying session information."""
        session_info = self.verify_session_info()
        if session_info:
            self.current_session_info = session_info
            self._update_session_display(session_info)
            self._log_message(f"Starting experiment for {session_info.subject_id}")

    def verify_session_info(self):
        """Verify and validate session information before starting experiment."""
        subject_id = self.main_gui.subject_id.toPlainText().strip().upper()
        subject_weight = self.main_gui.subject_weight.toPlainText().strip()
        protocol = self.main_gui.protocol.currentText()
        experiment = self.main_gui.experiment.currentText()
        configuration = self.main_gui.configuration.currentText()
        rig_id = self.main_gui.rig_id.currentText()

        # Validation checks
        if subject_id == "":
            self.critical_message("Enter Subject ID")
            return None

        if not Path(Path(prefs.get("DATADIR", "data"), subject_id)).exists():
            self.critical_message(
                f"'{subject_id}' does not exist. Please create new subject.",
            )
            self.clear_variables()
            return None

        if subject_weight == "":
            self.critical_message("Enter Subject Weight")
            return None

        try:
            weight_value = float(subject_weight)
            if weight_value <= 0:
                self.critical_message("Subject weight must be greater than 0")
                return None
        except ValueError:
            self.critical_message("Subject weight must be a valid number")
            return None

        if protocol == "SELECT":
            self.critical_message("Select Protocol")
            return None

        if experiment == "SELECT":
            self.critical_message("Select Experiment")
            return None

        if configuration == "SELECT":
            self.critical_message("Select Configuration")
            return None

        if rig_id == "SELECT":
            self.critical_message("Select Rig")
            return None

        # Create session info
        session_info = OmegaConf.create(
            {
                "subject_id": subject_id,
                "subject_weight": weight_value,
                "rig_id": str_to_code(rig_id),
                "protocol": str_to_code(protocol),
                "experiment": str_to_code(experiment),
                "configuration": str_to_code(configuration),
                "start_time": datetime.now().isoformat(),
            },
        )

        return session_info

    def clear_variables(self):
        """Clear all input variables."""
        self.main_gui.subject_id.clear()
        self.main_gui.subject_weight.clear()
        self.main_gui.protocol.setCurrentIndex(0)
        self.main_gui.experiment.clear()
        self.main_gui.experiment.addItem("SELECT")
        self.main_gui.experiment.setCurrentIndex(0)
        self.main_gui.configuration.clear()
        self.main_gui.configuration.addItem("SELECT")
        self.main_gui.configuration.setCurrentIndex(0)
        self.main_gui.rig_id.setCurrentIndex(0)
        self.main_gui.response_mode.setCurrentIndex(0)

        # Clear session display
        if hasattr(self.main_gui, "session_info_display"):
            self.main_gui.session_info_display.clear()

    def _update_session_display(self, session_info):
        """Update the session information display."""
        if hasattr(self.main_gui, "session_info_display"):
            display_text = f"""Current Session:
Subject: {session_info.subject_id}
Weight: {session_info.subject_weight}g
Protocol: {code_to_str(session_info.protocol)}
Experiment: {code_to_str(session_info.experiment)}
Configuration: {code_to_str(session_info.configuration)}
Rig: {code_to_str(session_info.rig_id)}
Start Time: {session_info.start_time}"""
            self.main_gui.session_info_display.setPlainText(display_text)

    # ==================== Rig Management ====================

    def handleTabActivationChange(self, tab_index):
        """Handle tab activation changes for rig GUIs."""
        for rig_id, task_gui in self.rigs_gui.items():
            if self.get_tab_index(rig_id) == tab_index:
                task_gui.tabActiveStateChanged.emit(True)
            else:
                task_gui.tabActiveStateChanged.emit(False)

    def get_tab_index(self, tab_name, tab_widget=None):
        """Get the index of a tab by name."""
        if not tab_widget:
            tab_widget = self.main_gui.tabs
        tab_name = code_to_str(tab_name)
        for index in range(tab_widget.count()):
            if tab_name == tab_widget.tabText(index):
                return index
        return None

    def add_new_rig(
        self,
        id: str = "rig_",
        task_gui=None,
        session_info=None,
        subject=None,
    ):
        """Add a new rig tab with task GUI."""
        try:
            display_name = code_to_str(id)
            self.rigs_gui[id] = task_gui(
                id,
                session_info=session_info,
                subject=subject,
            )
            tab_index = self.main_gui.tabs.addTab(self.rigs_gui[id], display_name)
            self.main_gui.tabs.setCurrentIndex(tab_index)
            self.rigs_gui[id].comm_from_taskgui.connect(self.message_from_taskgui)

            # Update active rigs display
            self._update_active_rigs_display()

            # Clear variables from control panel
            self.clear_variables()

            self._log_message(f"Added rig: {display_name}")
        except Exception as e:
            self._log_message(f"Could not add rig GUI: {e}")
            print(f"COULD NOT ADD RIG GUI: {e}")

    def remove_rig(self, id: str):
        """Remove a rig tab."""
        index = self.get_tab_index(id)
        if index is not None:
            self.main_gui.tabs.removeTab(index)
            self.main_gui.tabs.setCurrentIndex(0)
            if id in self.rigs_gui:
                del self.rigs_gui[id]
            self._update_active_rigs_display()
            self._log_message(f"Removed rig: {code_to_str(id)}")

    def _update_active_rigs_display(self):
        """Update the active rigs list display."""
        if hasattr(self.main_gui, "active_rigs_list"):
            self.main_gui.active_rigs_list.clear()
            for rig_id in self.rigs_gui.keys():
                self.main_gui.active_rigs_list.addItem(code_to_str(rig_id))

    def message_from_taskgui(self, message):
        """Handle messages from task GUIs."""
        self._log_message(f"Message from task GUI: {message}")

    def message_to_taskgui(self, value):
        """Send message to specific task GUI."""
        if "rig" in value and value["rig"] in self.rigs_gui:
            self.rigs_gui[value["rig"]].comm_to_taskgui.emit(value)

    # ==================== Subject Management ====================

    def show_subject_form(self):
        """Show the new subject creation form."""
        self.clear_variables()
        self.new_subject_window.show()
        self.new_subject_window.raise_()

    def create_new_subject(self):
        """Create a new subject with the provided information."""
        try:
            subject_id = self.new_subject_form.name.toPlainText().strip().upper()
            subject_identification = self.new_subject_form.identification.toPlainText().strip()
            subject_housing = self.new_subject_form.housing.toPlainText().strip()
            subject_dob = self.new_subject_form.dob.selectedDate().toString(
                "yyyy-MM-dd",
            )

            if subject_id == "":
                self.critical_message("Please Enter Subject ID")
                return

            # Check if subject already exists
            data_dir = prefs.get("DATADIR", "data")
            subject_dir = Path(data_dir, subject_id)

            if subject_dir.exists():
                self.critical_message(f"{subject_id} already exists")
                return

            # Create subject directory structure
            subject_dir.mkdir(parents=True, exist_ok=True)
            data_subdir = Path(subject_dir, "data")
            data_subdir.mkdir(parents=True, exist_ok=True)

            # Create subject info file
            info_dict = {
                "Name": subject_id,
                "Identification": "N/A" if subject_identification == "" else subject_identification,
                "subject_dob": subject_dob,
                "subject_housing": "N/A" if subject_housing == "" else subject_housing,
                "created_date": datetime.now().isoformat(),
            }

            with open(Path(subject_dir, "info.yaml"), "w") as file:
                yaml.dump(info_dict, file, default_flow_style=False)

            # Create subject history file
            header = [
                "date",
                "baseline_weight",
                "start_weight",
                "end_weight",
                "water_received",
                "rig_id",
                "protocol",
                "experiment",
                "session",
                "session_uuid",
            ]

            with open(Path(subject_dir, "history.csv"), "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(header)

            # Success message
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
            msg.setText(f"{subject_id} created successfully!")
            msg.setWindowTitle("Success")
            msg.exec()

            # Clear form and update main GUI
            self.new_subject_form.name.clear()
            self.new_subject_form.identification.clear()
            self.new_subject_form.housing.clear()
            self.new_subject_form.dob.setSelectedDate(QtCore.QDate.currentDate())
            self.new_subject_window.hide()
            self.main_gui.subject_id.setPlainText(subject_id)

            self._log_message(f"Created new subject: {subject_id}")

        except Exception as e:
            self._log_message(f"Error creating subject: {e}")
            self.critical_message(f"Error creating subject: {e}")

    # ==================== UI Helper Functions ====================

    def critical_message(self, message):
        """Show critical error message dialog."""
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.exec()

    def _log_message(self, message: str):
        """Add a message to the log display."""
        if hasattr(self.main_gui, "log_display"):
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_message = f"[{timestamp}] {message}"
            self.main_gui.log_display.append(formatted_message)

            # Auto-scroll to bottom
            cursor = self.main_gui.log_display.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.main_gui.log_display.setTextCursor(cursor)

    def _clear_log(self):
        """Clear the log display."""
        if hasattr(self.main_gui, "log_display"):
            self.main_gui.log_display.clear()
            self._log_message("Log cleared")

    # ==================== Menu Actions ====================

    def closeEvent(self, event):
        """Handle application close event."""
        reply = QtWidgets.QMessageBox.question(
            self,
            "Exit Application",
            "Are you sure you want to exit?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            # Clean up any running experiments or connections
            for rig_id in list(self.rigs_gui.keys()):
                self.remove_rig(rig_id)
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    # Example usage
    app = QtWidgets.QApplication(sys.argv)
    window = Application()
    window.show()

    # Uncomment to test with a task GUI
    # from protocols.random_dot_motion.core.gui.task_gui import TaskGUI
    # window.add_new_rig(id="rig_test", task_gui=TaskGUI)

    sys.exit(app.exec())
