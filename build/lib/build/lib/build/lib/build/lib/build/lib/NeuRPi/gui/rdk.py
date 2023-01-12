import csv
import multiprocessing
import os
import threading
import time
from multiprocessing import Process, Queue

import numpy as np
import pandas as pd
import pyqtgraph as pg
import pyqtgraph.exporters
from matplotlib import pyplot as plt
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# from pybpod_rotaryencoder_module.module_api import RotaryEncoderModule

Ui_StartWindow, baseclass1 = uic.loadUiType("NeuRPi/gui/start_window.ui")
Ui_MainWindow, baseclass2 = uic.loadUiType("NeuRPi/gui/interface.ui")
Ui_SettingsWindow, baseclass3 = uic.loadUiType("NeuRPi/gui/settings.ui")
Ui_HardwareWindow, baseclass4 = uic.loadUiType("NeuRPi/gui/hardware.ui")
Ui_DataWindow, baseclass5 = uic.loadUiType("NeuRPi/gui/behavior_data.ui")


class RDK_Application(baseclass1):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Creating all required windows
        self.thread = {}
        App = {}

        self.start_window = Ui_StartWindow()
        self.start_window.setupUi(self)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
