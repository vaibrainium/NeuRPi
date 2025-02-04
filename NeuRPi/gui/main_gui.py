import csv
import sys
from pathlib import Path

import yaml
from omegaconf import OmegaConf
from PyQt5 import QtCore, QtWidgets, uic

from NeuRPi.prefs import prefs

Ui_Main, mainclass = uic.loadUiType("NeuRPi/gui/main_gui.ui")
Ui_NewSubject, newsubjectclass = uic.loadUiType("NeuRPi/gui/new_subject_form.ui")


def code_to_str(var: str):
    str_var = var.replace("_", " ")
    str_var = str.title(str_var)
    return str_var


def str_to_code(var: str):
    code_var = var.replace(" ", "_")
    code_var = code_var.lower()
    return code_var


################# main gui #################
class Application(mainclass):
    def __init__(self):
        super().__init__()
        self.thread = QtCore.QThread()

        # new subject dialog
        self.new_subject_window = QtWidgets.QDialog()
        self.new_subject_form = Ui_NewSubject()
        self.new_subject_form.setupUi(self.new_subject_window)
        self.new_subject_window.raise_()
        self.new_subject_window.hide()
        # main gui
        self.main_gui = Ui_Main()
        self.main_gui.setupUi(self)
        self.show()
        # rigs
        self.rigs_gui = {}

        # import protocols
        # get list of protocols from protocols directory and add to protocol dropdown
        list_protocols = [code_to_str(x.name) for x in Path(Path.cwd(), "protocols").iterdir() if x.is_dir() and x.name != "__pycache__"]
        self.main_gui.protocol.addItems(list_protocols)
        self.main_gui.protocol.setCurrentIndex(0)

        # all connect signals
        self.main_gui.protocol.activated[str].connect(self.add_experiments)
        self.main_gui.experiment.activated[str].connect(self.add_configurations)
        self.main_gui.start_experiment.clicked.connect(self.start_experiment)
        self.main_gui.create_new_subject.clicked.connect(self.show_subject_form)
        self.new_subject_form.create_button.clicked.connect(self.create_new_subject)
        # Connect the signal to a slot
        self.main_gui.tabs.currentChanged.connect(self.handleTabActivationChange)

    ################ main gui helper functions ################
    def add_experiments(self):
        if self.main_gui.protocol.currentText() == "SELECT":
            self.main_gui.experiment.clear()
            self.main_gui.experiment.addItem("SELECT")
            self.main_gui.experiment.setCurrentIndex(0)
            return None
        protocol = str_to_code(self.main_gui.protocol.currentText())
        self.main_gui.experiment.clear()
        list_experiments = ["SELECT"]
        self.main_gui.experiment.setCurrentIndex(0)
        for x in Path(Path.cwd(), "protocols", protocol).iterdir():
            if x.is_dir() and x.name not in ["__pycache__", "core"]:
                list_experiments.append(code_to_str(x.name))  # .upper()
        self.main_gui.experiment.addItems(list_experiments)

    def add_configurations(self):
        if self.main_gui.experiment.currentText() == "SELECT":
            self.main_gui.rig_id.clear()
            self.main_gui.rig_id.addItem("SELECT")
            self.main_gui.rig_id.setCurrentIndex(0)
            return None
        protocol = str_to_code(self.main_gui.protocol.currentText())
        experiment = str_to_code(self.main_gui.experiment.currentText())
        self.main_gui.configuration.clear()
        list_configurations = ["SELECT"]
        self.main_gui.configuration.setCurrentIndex(0)
        for x in Path(Path.cwd(), "protocols", protocol, experiment).iterdir():
            if not x.is_dir() and x.name not in ["__pycache__", "core"]:
                # list_configurations.append(code_to_str(x.name))
                list_configurations.append(code_to_str(x.stem))
        self.main_gui.configuration.addItems(list_configurations)

    def critical_message(self, message):
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Critical)
        msg.setText(message)
        msg.setWindowTitle("Error")
        msg.exec_()
        return None

    ##################### rig functions #####################
    def handleTabActivationChange(self, tab_index):
        # Emit the tabActiveStateChanged signal on the corresponding TaskGUI instance
        for rig_id, task_gui in self.rigs_gui.items():
            if self.get_tab_index(rig_id) == tab_index:
                task_gui.tabActiveStateChanged.emit(True)
            else:
                task_gui.tabActiveStateChanged.emit(False)

    def get_tab_index(self, tab_name, tab_widget=None):
        if not tab_widget:
            tab_widget = self.main_gui.tabs
        tab_name = code_to_str(tab_name)
        tab_index = None
        for index in range(tab_widget.count()):
            if tab_name == tab_widget.tabText(index):
                tab_index = index
        return tab_index

    def add_new_rig(
        self,
        id: str = "rig_",
        task_gui=None,
        session_info=None,
        subject=None,
    ):
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
            # clearing variables from control panel
            self.clear_variables()
        except Exception as e:
            print(f"COULD NOT ADD RIG GUI: {e}")

    def remove_rig(self, id: str):
        index = self.get_tab_index(id)
        if index:
            self.main_gui.tabs.removeTab(index)
            self.main_gui.tabs.setCurrentIndex(0)
            del self.rigs_gui[id]

    def message_from_taskgui(self, message):
        pass

    def message_to_taskgui(self, value):
        self.rigs_gui[value["pilot"]].comm_to_taskgui.emit(value)

    ##################### start experiment functions #####################
    def clear_variables(self):
        self.main_gui.subject_name.clear()
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

    def start_experiment(self):
        self.verify_session_info()

    def verify_session_info(self):
        """
        Performing basic checks. Remainder functionality to be written by child class
        """
        subject_name = self.main_gui.subject_name.toPlainText().upper()
        subject_weight = self.main_gui.subject_weight.toPlainText()
        protocol = self.main_gui.protocol.currentText()
        experiment = self.main_gui.experiment.currentText()
        configuration = self.main_gui.configuration.currentText()
        rig_id = self.main_gui.rig_id.currentText()

        if subject_name == "":
            self.critical_message("Enter Subject ID")
            return None

        elif not Path(Path(prefs.get("DATADIR"), subject_name)).exists():
            self.critical_message(f"'{subject_name}' does not exist. Please create new subject.")
            self.clear_variables()
            return None

        if subject_weight == "":
            self.critical_message("Enter Subject Weight")
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

        session_info = OmegaConf.create(
            {
                "subject_name": subject_name,
                "subject_weight": float(subject_weight),
                "rig_id": str_to_code(rig_id),
                "protocol": str_to_code(protocol),
                "experiment": str_to_code(experiment),
                "configuration": str_to_code(configuration),
            }
        )
        return session_info

    ##################### new subject functions #####################
    def show_subject_form(self):
        self.clear_variables()
        self.new_subject_window.show()
        self.new_subject_window.raise_()

    def create_new_subject(self):
        subject_name = self.new_subject_form.name.toPlainText().upper()
        subject_identification = self.new_subject_form.identification.toPlainText()
        subject_housing = self.new_subject_form.housing.toPlainText()
        subject_dob = self.new_subject_form.dob.selectedDate().toString("yyyy-MM-dd")

        if subject_name.strip() == "":
            self.critical_message("Please Enter Subject ID")
            return None

        # check if subject already exists
        if Path(Path(prefs.get("DATADIR"), subject_name)).exists():
            self.critical_message(f"{subject_name} already exists")
            return None

        # create subject directory
        subject_dir = Path(prefs.get("DATADIR"), subject_name)
        subject_dir.mkdir(parents=True, exist_ok=True)
        data_dir = Path(subject_dir, "data")
        data_dir.mkdir(parents=True, exist_ok=True)
        # create subject info file
        info_dict = {
            "Name": subject_name,
            "Identification": "N/A" if subject_identification == "" else subject_identification,
            "subject_dob": subject_dob,
            "subject_housing": "N/A" if subject_housing == "" else subject_housing,
        }
        with open(Path(subject_dir, "info.yaml"), "w") as file:
            yaml.dump(info_dict, file, default_flow_style=False)
        # create subject history file
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
        with open(Path(subject_dir, "history.csv"), "w") as file:
            writer = csv.writer(file)
            writer.writerow(header)

        # let user know subject was created
        msg = QtWidgets.QMessageBox()
        msg.setIcon(QtWidgets.QMessageBox.Information)
        msg.setText(f"{subject_name} created!")
        msg.setWindowTitle("Success")
        msg.exec_()

        # clear subject window
        self.new_subject_form.name.clear()
        self.new_subject_form.identification.clear()
        self.new_subject_form.housing.clear()
        self.new_subject_form.dob.setSelectedDate(QtCore.QDate())
        self.new_subject_window.hide()
        self.main_gui.subject_name.setText(subject_name)


if __name__ == "__main__":
    from protocols.random_dot_motion.core.gui.task_gui import TaskGUI

    app = QtWidgets.QApplication(sys.argv)
    window = Application()
    window.show()
    window.add_new_rig(id="rig_test", task_gui=TaskGUI)
    sys.exit(app.exec_())
