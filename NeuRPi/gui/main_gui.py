import sys
import time

from PyQt5 import QtCore, QtGui, QtWidgets, uic

Ui_Main, mainclass = uic.loadUiType("NeuRPi/gui/main_gui.ui")


class Application(mainclass):
    def __init__(self):
        super().__init__()
        self.main_gui = Ui_Main()
        self.main_gui.setupUi(self)
        self.show()
        # Rigs
        self.rigs_gui = {}

        self.main_gui.start_experiment.clicked.connect(lambda: self.start_experiment())
        self.main_gui.calibrate_reward.clicked.connect(lambda: self.calibrate_reward())

    def code_to_str(self, var: str):
        display_var = var.replace("_", " ")
        display_var = str.title(display_var)
        return display_var

    def str_to_code(self, var: str):
        code_var = var.replace(" ", "_")
        code_var = code_var.lower()
        return code_var

    def get_tab_index(self, tab_name, tab_widget=None):
        if not tab_widget:
            tab_widget = self.main_gui.tabs
        tab_name = self.code_to_str(tab_name)
        tab_index = None
        for index in range(tab_widget.count()):
            if tab_name == tab_widget.tabText(index):
                tab_index = index
        return tab_index

    def add_new_rig(self, id: str = "rig_", task_gui=None):
        try:
            display_name = self.code_to_str(id)
            self.rigs_gui[id] = task_gui(id)
            tab_index = self.main_gui.tabs.addTab(self.rigs_gui[id], display_name)
            self.main_gui.tabs.setCurrentIndex(tab_index)
            self.rigs_gui[id].comm_from_taskgui.connect(self.message_from_taskgui)
        except:
            print("COULD NOT ADD RIG GUI")

    def remove_rig(self, id: str):
        index = self.get_tab_index(id)
        if index:
            self.main_gui.tabs.removeTab(index)
            self.main_gui.tabs.setCurrentIndex(0)
            del self.rigs_gui[id]

    def start_experiment(self):
        """
        Performing basic checks. Remainder functionality to be written by child class
        """

        subject = self.main_gui.subject.toPlainText().upper()
        subject_weight = self.main_gui.subject_weight.toPlainText()
        task_module = self.main_gui.task_module.currentText()
        task_phase = self.main_gui.task_phase.currentText()
        experiment_rig = self.main_gui.experiment_rig.currentText()

        if subject == "":
            msg = QtWidgets.QMessageBox()
            msg.setText("Enter Subject ID")
            msg.setWindowTitle("Error")
            msg.exec_()
            return None

        # for testing purposes allowing to proceed if subject name is 'XXX'
        elif subject == "XXX":
            subject_weight = "0"

        if subject_weight == "":
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Enter Subject Weight")
            msg.setWindowTitle("Error")
            msg.exec_()
            return None

        if experiment_rig == "None":
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Select Experiment Rig")
            msg.setWindowTitle("Error")
            msg.exec_()
            return None

        task_params = {
            "subject": subject,
            "subject_weight": float(subject_weight),
            "task_module": self.str_to_code(task_module),
            "task_phase": self.str_to_code(task_phase),
            "experiment_rig": self.str_to_code(experiment_rig),
        }

        return task_params

    def calibrate_reward(self):
        experiment_rig = self.main_gui.experiment_rig.currentText()
        if experiment_rig in ["None"]:  # , "Rig Test"]:
            return
        else:
            return self.str_to_code(experiment_rig)

    def message_from_taskgui(self, message):
        pass

    def message_to_taskgui(self, value):
        self.rigs_gui[value["pilot"]].comm_to_taskgui.emit(value)


if __name__ == "__main__":

    from protocols.random_dot_motion.gui.task_gui import TaskGUI

    app = QtWidgets.QApplication(sys.argv)
    window = Application()
    window.show()
    window.add_new_rig(id="rig_test", task_gui=TaskGUI)
    sys.exit(app.exec_())