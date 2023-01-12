import multiprocessing
import time

from PyQt5 import QtCore, QtGui, QtWidgets, uic

from NeuRPi.agents.test_terminal import Terminal
from NeuRPi.gui.rdk import Application


class Neurpi(Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.terminal = Terminal()

    def run(self):
        task = {
            "subject_id": "PSUIM4",
            "task_module": "RDK",
            "task_phase": "dynamic_training_rt",
        }

        self.terminal.node.send(to="rig_2", key="START", value=task)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    neurpi = Neurpi()
    sys.exit(app.exec_())

# import sys

# from PyQt5.QtWidgets import QApplication, QLabel, QWidget

# if __name__ == "__main__":
#     app = QApplication(sys.argv)

#     # Build the window widget
#     w = QWidget()
#     w.setGeometry(300, 300, 250, 150)  # x, y, w, h
#     w.setWindowTitle("My First Qt App")

#     # Add a label with tooltip
#     label = QLabel("Hello World", w)
#     label.setToolTip("This is a <b>QLabel</b> widget with Tooltip")
#     label.resize(label.sizeHint())
#     label.move(80, 50)

#     # Show window and run
#     w.show()
#     app.exec_()