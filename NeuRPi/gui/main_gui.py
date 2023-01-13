import sys

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from NeuRPi.gui.gui import gui_event
from protocols.random_dot_motion.gui.task_gui import TaskGUI

Ui_Main, mainclass = uic.loadUiType("NeuRPi/gui/main.ui")


class Application(mainclass):
    def __init__(self):
        super().__init__()
        self.main_window = Ui_Main()
        self.main_window.setupUi(self)
        # Rigs
        self.rigs_gui = {}

        button = QtWidgets.QToolButton()
        button.setToolTip("Add New Tab")
        button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogYesButton))
        self.main_window.tabs.setCornerWidget(button, QtCore.Qt.TopRightCorner)
        button.clicked.connect(self.add_new_rig)
        self.show()

        self.main_window.start_experiment.clicked.connect(
            lambda: self.start_experiment()
        )

    def code_to_str(self, var: str):
        display_var = var.replace("_", " ")
        display_var = str.title(display_var)
        return display_var

    def str_to_code(self, var: str):
        code_var = var.replace(" ", "_")
        code_var = code_var.lower()
        return code_var

    def add_new_rig(self, name: str = "rig_", task_gui=TaskGUI):
        try:
            display_name = self.code_to_str(name)
            # self.rigs_gui[name] = task_gui()
            self.main_window.tabs.addTab(task_gui(), display_name)
            self.rigs_gui[name] = self.main_window.tabs.widget(
                self.main_window.tabs.count() - 1
            )
        except:
            pass

    def start_experiment(self):
        """
        Performing basic checks. Remainder functionality to be written by child class
        """

        subject = self.main_window.subject.toPlainText().upper()
        subject_weight = self.main_window.subject_weight.toPlainText()
        task_module = self.main_window.task_module.currentText()
        task_phase = self.main_window.task_phase.currentText()
        experiment_rig = self.main_window.experiment_rig.currentText()

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

    @gui_event
    def update_task_gui(self, value):
        self.rigs_gui[value["pilot"]].update_gui(value)


# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     window = Application()
#     window.show()
#     sys.exit(app.exec_())
