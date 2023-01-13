import csv
import multiprocessing
import os
import threading
import time
from multiprocessing import Process, Queue

import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# from pybpod_rotaryencoder_module.module_api import RotaryEncoderModule

Ui_MainWindow, baseclass1 = uic.loadUiType("NeuRPi/gui/main_window.ui")
Ui_SummaryWindow, baseclass2 = uic.loadUiType("NeuRPi/gui/summary_window.ui")
# Ui_MainWindow, baseclass2 = uic.loadUiType("NeuRPi/gui/interface.ui")
# Ui_SettingsWindow, baseclass3 = uic.loadUiType("NeuRPi/gui/settings.ui")
# Ui_HardwareWindow, baseclass4 = uic.loadUiType("NeuRPi/gui/hardware.ui")


class Application(baseclass1):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.main = Ui_MainWindow()
        self.main.setupUi(self)

        self.SummaryWindow = QtWidgets.QMainWindow()
        self.summary_window = Ui_SummaryWindow()
        self.summary_window.setupUi(self.SummaryWindow)

        self.show()

        # self.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)

        self.SummaryWindow.raise_()
        self.rigs = {}
        # self.create_rig_access()
        # self.initialize_plots()

        self.main_window.start_rig.clicked.connect(lambda: self.start_experiment())
        # self.uLPP.valueChanged.connect(lambda: self.rewardPulseWidth(App))
        # self.pulseLeft.clicked.connect(lambda: rewardLeft(App))
        # self.pulseRight.clicked.connect(lambda: rewardRight(App))
        # self.endExperiment.clicked.connect(lambda: self.Terminate(App))
        # self.trialSettings.clicked.connect(self.ShowSettings)
        # self.pauseExperiment.clicked.connect(lambda: self.pauseExperiment(App))
        # self.closeExperiment.clicked.connect(lambda: self.closeExperiment(App, Cam))

        # self.main_window.closeExperiment.setDisabled(True)

    def create_rig_access(self):
        self.rigs["rigs_1"] = {}

    def initialize_plots(
        self,
        coherences=[-100, -72, -36, -18, -9, 0, 9, 18, 36, 72, 100],
    ):
        # initialize plots
        rig_list = ["rig_1_", "rig_2_", "rig_3_", "rig_4_"]
        for _, rig in enumerate(rig_list):
            rig_handle = "self.main." + rig
            updates = (
                # Accuracy plots
                rig_handle
                + "accuracy_plot.setTitle('Accuracy Plot', color='r', size='10pt') \n"
                + rig_handle
                + "accuracy_plot.setYRange(0, 1) \n"
                + rig_handle
                + "accuracy_plot.setInteractive(False) \n"
                + rig_handle
                + "accuracy_plot.setLabel('left', 'Accuracy') \n"
                + rig_handle
                + "accuracy_plot.setLabel('bottom', 'Trial No') \n"
                # Psychometric plots
                + rig_handle
                + "psychometric_plot.setTitle('Psychometric Function', color='r', size='10pt') \n"
                + rig_handle
                + "psychometric_plot.setXRange(-100, 100) \n"
                + rig_handle
                + "psychometric_plot.setYRange(0, 1) \n"
                + rig_handle
                + "psychometric_plot.setInteractive(False) \n"
                + rig_handle
                + "psychometric_plot.setLabel('left', 'Proportion of Right Choices') \n"
                + rig_handle
                + "psychometric_plot.setLabel('bottom', 'Coherence') \n"
                + rig_handle
                + "psychometric_plot.showGrid(x=False, y=True, alpha=0.6) \n"
                + rig_handle
                + "psychometric_plot.getAxis('bottom').setTicks([[(v, str(v)) for v in coherences]]) \n"
                # Total Trial Plot
                + rig_handle
                + "trial_plot.setTitle('Total Trials', color='r', size='10pt') \n"
                + rig_handle
                + "trial_plot.setXRange(0, len(coherences)) \n"
                + rig_handle
                + "trial_plot.setInteractive(False) \n"
                + rig_handle
                + "trial_plot.setLabel('left', 'Trials') \n"
                + rig_handle
                + "trial_plot.setLabel('bottom', 'Coherence') \n"
                + rig_handle
                + "trial_plot.showGrid(x=False, y=True, alpha=0.6) \n"
                + "ticks2 = [list(zip(range(len(coherences)), list(coherences)))] \n"
                + rig_handle
                + "trial_plot.getAxis('bottom').setTicks(ticks2) \n"
                # Reaction Time Plot
                + rig_handle
                + "rt_plot.setTitle('Reaction Times', color='r', size='10pt') \n"
                + rig_handle
                + "rt_plot.setXRange(-100, 100) \n"
                + rig_handle
                + "rt_plot.setInteractive(False) \n"
                + rig_handle
                + "rt_plot.setLabel('left', 'Reaction Time') \n"
                + rig_handle
                + "rt_plot.setLabel('bottom', 'Coherence') \n"
                + rig_handle
                + "rt_plot.showGrid(x=False, y=True, alpha=0.6) \n"
                + rig_handle
                + "rt_plot.getAxis('bottom').setTicks([[(v, str(v)) for v in coherences]]) \n"
            )
            exec(updates)

        # self.accuracyVec = np.array([])
        # self.correctVec = np.array([])
        # self.trialVec = np.array([])
        # self.psychometricPlot = self.UI2.psychometricPlot.plot()
        # # self.tottrialPlot = self.UI2.tottrialPlot.plot()
        # self.RTPlot = self.UI2.RTPlot.plot()

        pass

    def start_rig(self, rig: str):
        pass

    def update_plots(self, rig: str, data: dict):
        pass

    def update_trials(self, rig: str, data: dict):
        # Update trial counters
        rig_handle = "self.main_window." + rig + "_"
        updates = (
            rig_handle
            + "attempt_trials.setText(str(data['trial_counters']['attempt'])) \n"
            + rig_handle
            + "total_trials.setText(str(data['trial_counters']['trial'])) \n"
            + rig_handle
            + "correct_trials.setText(str(data['trial_counters']['correct'])) \n"
            + rig_handle
            + "incorrect_trials.setText(str(data['trial_counters']['incorrect'])) \n"
            + rig_handle
            + "noresponse_trials.setText(str(data['trial_counters']['noresponse'])) \n"
        )
        exec(updates)

    def update_stimulus(self, rig: str, data: dict):
        # Update trial counters
        rig_handle = "self.main_window." + rig + "_"
        updates = (
            rig_handle
            + "currect_stimulus.setText(str(data['stinulus_pars']['coherence'])) \n"
        )
        exec(updates)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    rdk_gui = Application()
    rdk_gui.show()
    sys.exit(app.exec_())
