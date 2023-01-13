import sys

from PyQt5 import QtCore, QtGui, QtWidgets, uic

Ui_rig, rigclass = uic.loadUiType("NeuRPi/gui/rdk_rig.ui")


class TaskGui(rigclass):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rig = Ui_rig()
        self.rig.setupUi(self)
        self.initialize_plots()

    def initialize_plots(
        self,
        coherences=[-100, -72, -36, -18, -9, 0, 9, 18, 36, 72, 100],
    ):
        # Accuracy plots
        self.rig.accuracy_plot.setTitle("Accuracy Plot", color="r", size="10pt")
        self.rig.accuracy_plot.setYRange(0, 1)
        self.rig.accuracy_plot.setInteractive(False)
        self.rig.accuracy_plot.setLabel("left", "Accuracy")
        self.rig.accuracy_plot.setLabel("bottom", "Trial No")
        # Psychometric plots
        self.rig.psychometric_plot.setTitle(
            "Psychometric Function", color="r", size="10pt"
        )
        self.rig.psychometric_plot.setXRange(-100, 100)
        self.rig.psychometric_plot.setYRange(0, 1)
        self.rig.psychometric_plot.setInteractive(False)
        self.rig.psychometric_plot.setLabel("left", "Proportion of Right Choices")
        self.rig.psychometric_plot.setLabel("bottom", "Coherence")
        self.rig.psychometric_plot.showGrid(x=False, y=True, alpha=0.6)
        self.rig.psychometric_plot.getAxis("bottom").setTicks(
            [[(v, str(v)) for v in coherences]]
        )
        # Total Trial Plot
        self.rig.trial_plot.setTitle("Total Trials", color="r", size="10pt")
        self.rig.trial_plot.setXRange(0, len(coherences))
        self.rig.trial_plot.setInteractive(False)
        self.rig.trial_plot.setLabel("left", "Trials")
        self.rig.trial_plot.setLabel("bottom", "Coherence")
        self.rig.trial_plot.showGrid(x=False, y=True, alpha=0.6)
        ticks = [list(zip(range(len(coherences)), list(coherences)))]
        self.rig.trial_plot.getAxis("bottom").setTicks(ticks)
        # Reaction Time Plot
        self.rig.rt_plot.setTitle("Reaction Times", color="r", size="10pt")
        self.rig.rt_plot.setXRange(-100, 100)
        self.rig.rt_plot.setInteractive(False)
        self.rig.rt_plot.setLabel("left", "Reaction Time")
        self.rig.rt_plot.setLabel("bottom", "Coherence")
        self.rig.rt_plot.showGrid(x=False, y=True, alpha=0.6)
        self.rig.rt_plot.getAxis("bottom").setTicks([[(v, str(v)) for v in coherences]])


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    window = TaskGui()
    window.show()
    sys.exit(app.exec_())
