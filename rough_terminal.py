from PyQt5 import QtWidgets

from NeuRPi.agents.test_terminal import Terminal


class Neurpi:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.terminal = Terminal()


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    neurpi = Neurpi()
    sys.exit(app.exec_())
