# TODO: In future major update, plan is to move on to ray and ray-workflow

from PyQt5 import QtWidgets

from NeuRPi.agents.agent_terminal import Terminal


class Neurpi:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.terminal = Terminal()

        value = {
            "pilot": "rig_test",
            "ip": "pi1",
            "state": "IDLE",
            "prefs": None,  # prefs.get(),
        }
        self.terminal.l_handshake(value)
        self.terminal.l_state(value)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    neurpi = Neurpi()
    sys.exit(app.exec_())
