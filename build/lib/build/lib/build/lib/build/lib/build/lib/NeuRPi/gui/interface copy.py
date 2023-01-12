import csv
import multiprocessing
import os
import threading
import time
from multiprocessing import Process, Queue

import cv2
import numpy as np
import pandas as pd
import pyqtgraph as pg
import pyqtgraph.exporters
import serial
from matplotlib import pyplot as plt
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# from pybpod_rotaryencoder_module.module_api import RotaryEncoderModule

Ui_StartWindow, baseclass1 = uic.loadUiType("start_window.ui")
Ui_MainWindow, baseclass2 = uic.loadUiType("interface.ui")
Ui_SettingsWindow, baseclass3 = uic.loadUiType("settings.ui")
Ui_HardwareWindow, baseclass4 = uic.loadUiType("hardware.ui")
Ui_DataWindow, baseclass5 = uic.loadUiType("behavior_data.ui")


class RDK_Application(baseclass1):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Creating all required windows
        self.thread = {}
        App = {}

        self.start_window = Ui_StartWindow()
        self.start_window.setupUi(self)

        self.InterfaceWindow = QtWidgets.QMainWindow()
        App["UI2"] = Ui_MainWindow()
        App["UI2"].setupUi(self.InterfaceWindow)
        self.UI2 = App["UI2"]

        self.SettingsWindow = QtWidgets.QDialog()
        App["UI3"] = Ui_SettingsWindow()
        App["UI3"].setupUi(self.SettingsWindow)
        self.UI3 = App["UI3"]

        self.HardwareWindow = QtWidgets.QDialog()
        App["UI4"] = Ui_HardwareWindow()
        App["UI4"].setupUi(self.HardwareWindow)
        self.UI4 = App["UI4"]

        self.DataWindow = QtWidgets.QDialog()
        App["UI5"] = Ui_DataWindow()
        App["UI5"].setupUi(self.DataWindow)
        self.UI5 = App["UI5"]

        self.show()

        self.SettingsWindow.raise_()
        self.DataWindow.raise_()
        # Import all previously saved settings
        df = pd.read_csv("Settings.csv")
        # Ports
        App["UI4"].arduinoPort.setText(df.ArduinoPort[0])
        # App['UI4'].wheelPort.setText(df.WheelPort[0])
        App["directory"] = df.Directory[0]
        App["UI3"].repeatThreshold.setValue(df.RepeatThreshold[0])
        App["UI3"].pwPUL.setValue(df.PulseWidthperuL[0])
        App["UI3"].minViewTime.setValue(df.MinViewTime[0])
        App["UI3"].dotRadius.setValue(df.DotRadius[0])
        App["UI3"].dotFill.setValue(df.DotFill[0])
        App["UI3"].dotVel.setValue(df.DotVel[0])
        App["UI3"].stimFPS.setValue(df.StimFPS[0])
        App["UI3"].lickThresh.setValue(df.LickThresh[0])
        App["UI3"].lickSlope.setValue(df.LickSlope[0])
        App["UI3"].onsetTone.setChecked(bool(df.OnsetTone[0]))
        App["UI3"].correctTone.setChecked(bool(df.CorrectTone[0]))
        App["UI3"].incorrectTone.setChecked(bool(df.IncorrectTone[0]))
        App["UI3"].noresponseTone.setChecked(bool(df.NoResponseTone[0]))
        App["UI3"].bidirectionalCoherences.setChecked(
            bool(df.BiDirectionalCoherences[0])
        )
        App["UI3"].dynamicReward.setChecked(bool(df.DynamicReward[0]))
        App["UI3"].inCohlvlReward.setValue(df.IncreaseCoherencelvlReward[0])
        App["UI3"].inCohlvlReward.setValue(df.DecreaseCoherencelvlReward[0])

        App["UI3"].autoEnd.setChecked(bool(df.AutoEnd[0]))
        App["UI3"].endCriteria_45.setValue(df.EndCriteria_45min[0])
        App["UI3"].endCriteria_5.setValue(df.EndCriteria_5min[0])

        App["UI3"].camflipVertical.setChecked(bool(df.CamVFlip[0]))
        App["UI3"].camflipHorizontal.setChecked(bool(df.CamHFlip[0]))
        App["UI3"].camRGB.setChecked(bool(df.CamRGB[0]))

        # Connecting Arduino
        # App['Ard'] = serial.Serial('COM7', baudrate=9600, timeout=0)
        App["Ard"] = serial.Serial(
            App["UI4"].arduinoPort.text(), baudrate=9600, timeout=0
        )

        App["UI1"].primeReward.clicked.connect(lambda: rewardPrime(App))
        App["UI1"].leftValve.clicked.connect(lambda: self.leftValve(App))
        App["UI1"].rightValve.clicked.connect(lambda: self.rightValve(App))
        App["UI1"].trainingPhase.currentTextChanged.connect(
            lambda: self.addProgram(App)
        )
        App["UI1"].hardwareCheck.clicked.connect(self.OpenHardwareDialogue)
        App["UI1"].startExperiment.clicked.connect(
            lambda: self.StartExperiment(App, Cam)
        )

        App["UI2"].uLPP.valueChanged.connect(lambda: self.rewardPulseWidth(App))
        App["UI2"].pulseLeft.clicked.connect(lambda: rewardLeft(App))
        App["UI2"].pulseRight.clicked.connect(lambda: rewardRight(App))
        App["UI2"].endExperiment.clicked.connect(lambda: self.Terminate(App))
        App["UI2"].trialSettings.clicked.connect(self.ShowSettings)
        App["UI2"].pauseExperiment.clicked.connect(lambda: self.pauseExperiment(App))
        App["UI2"].closeExperiment.clicked.connect(
            lambda: self.closeExperiment(App, Cam)
        )
        #
        App["UI3"].dotRadius.valueChanged.connect(lambda: self.changeDotRadius(App))
        App["UI3"].dotFill.valueChanged.connect(lambda: self.changeDotFill(App))
        App["UI3"].dotVel.valueChanged.connect(lambda: self.changeDotVel(App))
        App["UI3"].stimFPS.valueChanged.connect(lambda: self.changeStimFPS(App))
        App["UI3"].lickThresh.valueChanged.connect(lambda: self.changelickThresh(App))
        App["UI3"].lickSlope.valueChanged.connect(lambda: self.changelickSlope(App))
        # App["UI3"].camflipVertical.stateChanged.connect(lambda: self.flipImage(Cam))
        # App["UI3"].camflipHorizontal.stateChanged.connect(lambda: self.flipImage(Cam))
        # App["UI3"].camRGB.stateChanged.connect(lambda: self.rgbImage(Cam))

        App["UI5"].okay.clicked.connect(lambda: self.closeData(App))

        App["UI2"].closeExperiment.setDisabled(True)
        App["UI3"].applySettings.clicked.connect(self.HideSettings)
        App["UI3"].makedefaultSettings.clicked.connect(lambda: self.SaveSettings(App))

        App["keepTraining"] = 0
        App["pauseSession"] = 0
        App["sessionClock"] = 0
        App["sessionTime"] = 0
        App["trialClock"] = 0
        App["trialTime"] = 0
        self.leftValveState = 0
        self.rightValveState = 0

        # # setting Camera
        Cam = {}
        Cam["Camera"] = Camera
        # self.flipImage(Cam)
        # self.rgbImage(Cam)

        # Miscellaneous GUI Buttons
        self.Timer = QtCore.QTimer()  # time.time()
        self.Timer.timeout.connect(
            lambda: self.updateTimer(
                App["keepTraining"],
                App["pauseSession"],
                App["sessionClock"],
                App["sessionTime"],
                App["trialClock"],
                App["trialTime"],
            )
        )
        self.Timer.start(10)

        # Window Manipulation Hints
        # self.InterfaceWindow.closeEvent = self.closeEvent                           # Connecting close event of interface window to closing of startwindow
        self.InterfaceWindow.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        # self.InterfaceWindow.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        self.SettingsWindow.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)
        self.SettingsWindow.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        # self.DataWindow.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        self.DataWindow.setWindowFlag(QtCore.Qt.FramelessWindowHint, True)

        self.pause = 0

    def addProgram(self, App):
        if App["UI1"].trainingPhase.currentText() == "+ Add Program":
            # Opening file dialog
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            fileName, _ = QFileDialog.getOpenFileName(
                self,
                "Select Program File",
                "",
                "All Files (*);;Python Files (*.py)",
                options=options,
            )
            print(fileName)

    def updateTimer(
        self,
        keeptraining,
        pausesession,
        sessionClock,
        sessionTime,
        trialClock,
        trialTime,
    ):
        if keeptraining:
            if not pausesession:
                trialTime = time.time() - trialClock
                self.UI2.trialTimer.setText("{:0.2f}".format(trialTime))  # trialTimer
                sessionTime = time.time() - sessionClock
                self.UI2.sessionTimer.display(int(sessionTime))  # sessionTimer

    def rewardPulseWidth(self, App):
        PW = App["UI2"].uLPP.value() * App["UI3"].pwPUL.value()
        rPW = "r" + str(PW)  # 'r' is the code on arduino to set pulse width
        App["Ard"].write(rPW.encode())

    def leftValve(self, App):
        if self.leftValveState == 0:
            App["Ard"].write(b"q")
            self.UI1.leftValve.setStyleSheet("background-color: green; color:white;")
            self.UI1.leftValve.setText("Left Valve Close")
            self.leftValveState = 1
        elif self.leftValveState == 1:
            App["Ard"].write(b"w")
            self.UI1.leftValve.setStyleSheet("background-color: rgb(235,235,235)")
            self.UI1.leftValve.setText("Left Valve Open")
            self.leftValveState = 0

    def rightValve(self, App):
        if self.rightValveState == 0:
            App["Ard"].write(b"o")
            self.UI1.rightValve.setStyleSheet("background-color: green; color:white;")
            self.UI1.rightValve.setText("Right Valve Close")
            self.rightValveState = 1
        elif self.rightValveState == 1:
            App["Ard"].write(b"p")
            self.UI1.rightValve.setStyleSheet("background-color: rgb(230,230,230)")
            self.UI1.rightValve.setText("Right Valve Open")
            self.rightValveState = 0

    def changelickThresh(self, App):
        Thresh = "t" + str(
            App["UI3"].lickThresh.value()
        )  # 't' is the code on arduino to set pulse width
        App["Ard"].write(Thresh.encode())

    def changelickSlope(self, App):
        Slope = "s" + str(
            App["UI3"].lickSlope.value()
        )  # 's' is the code on arduino to set pulse width
        App["Ard"].write(Slope.encode())

    def changeDotRadius(self, App):
        App["StimMsg"].put(["dotRadius", App["UI3"].dotRadius.value(), "NaN"])

    def changeDotFill(self, App):
        App["StimMsg"].put(["dotFill", App["UI3"].dotFill.value(), "NaN"])

    def changeStimFPS(self, App):
        App["StimMsg"].put(["frameRate", App["UI3"].stimFPS.value(), "NaN"])
        if App["UI1"].dotsLifetime.currentText() == "Short Lifetime":
            App["StimMsg"].put(["updateLifetime", 0.5 * App["FrameRate"], "NaN"])
        elif App["UI1"].dotsLifetime.currentText() == "Long Lifetime":
            App["StimMsg"].put(["updateLifetime", App["FrameRate"] * 200, "NaN"])

    def changeDotVel(self, App):
        App["StimMsg"].put(["dotVel", App["UI3"].dotVel.value(), "NaN"])

    def flipImage(self, Cam):
        if (
            self.UI3.camflipVertical.isChecked()
            and self.UI3.camflipHorizontal.isChecked()
        ):
            Cam["camFlip"] = -1
        elif self.UI3.camflipVertical.isChecked():
            Cam["camFlip"] = 0
        elif self.UI3.camflipHorizontal.isChecked():
            Cam["camFlip"] = 1
        else:
            Cam["camFlip"] = 2

    def rgbImage(self, Cam):
        if self.UI3.camRGB.isChecked():
            Cam["camColor"] = [cv2.COLOR_BGR2RGB, QImage.Format_RGB888]
        else:
            Cam["camColor"] = [cv2.COLOR_BGR2GRAY, QImage.Format_Grayscale8]

    def pauseExperiment(self, App):
        if self.pause == 0:
            self.pause = 1
            self.UI2.pauseExperiment.setStyleSheet("background-color: green")
            self.UI2.pauseExperiment.setText("Resume")
            App["pauseSession"] = 1

        elif self.pause == 1:
            self.pause = 0
            self.UI2.pauseExperiment.setStyleSheet("background-color: rgb(255,170,0)")
            self.UI2.pauseExperiment.setText("Pause")
            App["pauseSession"] = 0

    def closeExperiment(self, App, Cam):
        # self.stopDisplay(App)
        self.stopSession()
        self.stopBehavior()
        # self.stopCamera()
        self.savePlots(App)
        self.close()
        self.__init__(App["StimMsg"], Cam["Camera"])

    def initiatePlots(self, App):
        # pass
        self.UI2.accuracyPlot.setTitle("Accuracy Plot", color="r", size="10pt")
        self.UI2.accuracyPlot.setYRange(0, 1)
        self.UI2.accuracyPlot.setInteractive(False)
        self.UI2.accuracyPlot.setLabel("left", "Accuracy")
        self.UI2.accuracyPlot.setLabel("bottom", "Trial No")
        self.UI2.accuracyPlot.showGrid(x=False, y=True, alpha=0.6)
        self.accuracyPlot = self.UI2.accuracyPlot.plot()
        self.CorrectPlot = self.UI2.accuracyPlot.plot()
        self.IncorrectPlot = self.UI2.accuracyPlot.plot()
        self.accuracyVec = np.array([])
        self.correctVec = np.array([])
        self.trialVec = np.array([])

        self.UI2.psychometricPlot.setTitle(
            "Psychometric Function", color="r", size="10pt"
        )
        self.UI2.psychometricPlot.setXRange(-100, 100)
        self.UI2.psychometricPlot.setYRange(0, 1)
        self.UI2.psychometricPlot.setInteractive(False)
        self.UI2.psychometricPlot.setLabel("left", "Proportion of Right Choices")
        self.UI2.psychometricPlot.setLabel("bottom", "Coherence")
        self.UI2.psychometricPlot.getAxis("bottom").setTicks(
            [[(v, str(v)) for v in App["Coherences"]]]
        )
        self.UI2.psychometricPlot.showGrid(x=False, y=True, alpha=0.6)
        self.psychometricPlot = self.UI2.psychometricPlot.plot()

        self.UI2.tottrialPlot.setTitle("Total Trials", color="r", size="10pt")
        self.UI2.tottrialPlot.setXRange(0, len(App["Coherences"]))
        self.UI2.tottrialPlot.setInteractive(False)
        self.UI2.tottrialPlot.setLabel("left", "Trials")
        self.UI2.tottrialPlot.setLabel("bottom", "Coherence")
        ticks2 = [list(zip(range(len(App["Coherences"])), list(App["Coherences"])))]
        self.UI2.tottrialPlot.getAxis("bottom").setTicks(ticks2)
        self.UI2.tottrialPlot.showGrid(x=False, y=True, alpha=0.6)
        # self.tottrialPlot = self.UI2.tottrialPlot.plot()

        self.UI2.RTPlot.setTitle("Reaction Times", color="r", size="10pt")
        self.UI2.RTPlot.setXRange(-100, 100)
        self.UI2.RTPlot.setInteractive(False)
        self.UI2.RTPlot.setLabel("left", "Reaction Time")
        self.UI2.RTPlot.setLabel("bottom", "Coherence")
        self.UI2.RTPlot.getAxis("bottom").setTicks(
            [[(v, str(v)) for v in App["Coherences"]]]
        )
        self.UI2.RTPlot.showGrid(x=False, y=True, alpha=0.6)
        self.RTPlot = self.UI2.RTPlot.plot()

    def savePlots(self, App):

        App["UI2"].Plots.setCurrentIndex(0)
        exporter = pg.exporters.ImageExporter(App["UI2"].accuracyPlot.scene())
        exporter.parameters()[
            "width"
        ] = 800  # (note this also affects height parameter)
        exporter.export(App["accu"])

        App["UI2"].Plots.setCurrentIndex(1)
        exporter = pg.exporters.ImageExporter(App["UI2"].psychometricPlot.scene())
        exporter.parameters()[
            "width"
        ] = 800  # (note this also affects height parameter)
        exporter.export(App["psych"])

        App["UI2"].Plots.setCurrentIndex(2)
        exporter = pg.exporters.ImageExporter(App["UI2"].tottrialPlot.scene())
        exporter.parameters()[
            "width"
        ] = 800  # (note this also affects height parameter)
        exporter.export(App["tottrl"])

        App["UI2"].Plots.setCurrentIndex(3)
        exporter = pg.exporters.ImageExporter(App["UI2"].RTPlot.scene())
        exporter.parameters()[
            "width"
        ] = 800  # (note this also affects height parameter)
        exporter.export(App["RT"])

        App["UI2"].Plots.setCurrentIndex(0)

        data = np.genfromtxt(
            App["summary"],
            delimiter=",",
            names=["Attempts", "Trials", "Accuracy", "Bias", "Weight"],
            skip_header=1,
        )
        # Trials vs Weight
        plt.plot(
            data["Weight"], data["Attempts"], "go", label="Total Attempts vs Weight"
        )
        plt.legend()
        plt.xlabel("Weight")
        plt.ylabel("Trials")
        plt.savefig(App["dire_path"] + "\\" + "Attempts Vs Weight.png")
        plt.close()
        # Trials vs Training Days
        plt.plot(data["Trials"], "g-")
        plt.xlabel("Training Days")
        plt.ylabel("Trials")
        plt.savefig(App["dire_path"] + "\\" + "Trials Vs Trianing.png")
        plt.close()
        # Accuracy and Bias vs Training Days
        plt.plot(data["Accuracy"], "g-", label="Accuracy")
        plt.plot(data["Bias"], "b--", label="Bias")
        plt.legend()
        plt.xlabel("Training Days")
        plt.savefig(App["dire_path"] + "\\" + "Accuracy Vs Trianing.png")
        plt.close()

    def Terminate(self, App):
        App["terminateSession"] = 1
        os.system('taskkill /F /FI "WINDOWTITLE eq Camera')
        self.CanCloseExperiment = 1

    def closeData(self, App):
        if (
            self.UI5.baselineWeight.toPlainText() == ""
            or self.UI5.startWeight.toPlainText() == ""
            or self.UI5.endWeight.toPlainText() == ""
        ):
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Forgot to Enter one of the weights")
            msg.setWindowTitle("Error")
            msg.exec_()
        else:
            self.DataWindow.hide()
            App["LogData"] = 1

    def SaveSettings(self, App):
        self.HideSettings()
        Settings = {
            "RepeatThreshold": App["UI3"].repeatThreshold.value(),
            "PulseWidthperuL": App["UI3"].pwPUL.value(),
            "MinViewTime": App["UI3"].minViewTime.value(),
            "DotRadius": App["UI3"].dotRadius.value(),
            "DotFill": App["UI3"].dotFill.value(),
            "DotVel": App["UI3"].dotVel.value(),
            "StimFPS": App["UI3"].stimFPS.value(),
            "LickThresh": App["UI3"].lickThresh.value(),
            "LickSlope": App["UI3"].lickSlope.value(),
            "CamVFlip": App["UI3"].camflipVertical.isChecked(),
            "CamHFlip": App["UI3"].camflipHorizontal.isChecked(),
            "CamRGB": App["UI3"].camRGB.isChecked(),
            "ArduinoPort": App["UI4"].arduinoPort.text(),
            "WheelPort": App["UI4"].wheelPort.text(),
            "Directory": App["directory"],
            "OnsetTone": App["UI3"].onsetTone.isChecked(),
            "CorrectTone": App["UI3"].correctTone.isChecked(),
            "IncorrectTone": App["UI3"].incorrectTone.isChecked(),
            "NoResponseTone": App["UI3"].noresponseTone.isChecked(),
            "BiDirectionalCoherences": App["UI3"].bidirectionalCoherences.isChecked(),
            "DynamicReward": App["UI3"].dynamicReward.isChecked(),
            "IncreaseCoherencelvlReward": App["UI3"].inCohlvlReward.value(),
            "DecreaseCoherencelvlReward": App["UI3"].deCohlvlReward.value(),
            "AutoEnd": App["UI3"].autoEnd.isChecked(),
            "EndCriteria_45min": App["UI3"].endCriteria_45.value(),
            "EndCriteria_5min": App["UI3"].endCriteria_5.value(),
        }
        with open("Settings.csv", "w", newline="") as fSet:
            headers = list(Settings.keys())
            writer = csv.DictWriter(fSet, fieldnames=headers)
            writer.writeheader()
            writer.writerow(Settings)

    def StartExperiment(self, App, Cam):
        # Checking all required ports working
        error = 0
        self.CanCloseExperiment = 0

        if App["UI1"].mouseID.toPlainText() == "":
            error = 1
            msg = QtWidgets.QMessageBox()
            msg.setText("Enter Mouse ID")
            msg.setWindowTitle("Error")
            msg.exec_()

        if App["UI4"].arduinoPort.text() == "NA":
            error = 1
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Arduino Not Connected")
            msg.setWindowTitle("Error")
            msg.exec_()
        else:
            True
            # # Activating wheel Serial ports
            # if App["UI1"].responseModality.currentText() == 'Wheel':
            #     App['Whl'] = RotaryEncoderModule('COM5')

        if (
            App["UI4"].wheelPort.text() == "NA"
            and App["UI1"].responseModality.currentText() == "Wheel"
        ):
            error = 1
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Oh no! Daenerys broke the Wheel")
            msg.setWindowTitle("Error")
            msg.exec_()

        if (
            App["UI1"].mouseWeight.toPlainText() == ""
            and not App["UI1"].mouseID.toPlainText().upper() == "XXX"
        ):
            error = 1
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Enter Mouse Weight")
            msg.setWindowTitle("Error")
            msg.exec_()

        if not error:
            # Opening exernal camera app
            os.startfile("microsoft.windows.camera:")
            hwnd = win32gui.FindWindow(None, "Camera")  # Getting pid for camera app
            win32gui.MoveWindow(
                hwnd, 0, 0, 950, 600, 0
            )  # Setting camera app position (x,y,w,h)

            App["UI2"].mouseID.setText(
                App["UI1"].mouseID.toPlainText().upper()
            )  # Display mouse ID on main GUI
            StartWindow.hide()  # Hiding startWindow ~ App["UI1"]
            self.InterfaceWindow.show()
            os.startfile("microsoft.windows.camera:")
            if App["UI1"].trainingPhase.currentText() == "Free Reward":
                Session = Free_Reward
            elif App["UI1"].trainingPhase.currentText() == "Mixed Coherences":
                Session = Mixed_Coherence
            elif App["UI1"].trainingPhase.currentText() == "Dynamic Coherences":
                App["UI1"].cohLevel.setValue(5)
                Session = Dynamic_Coherence
            elif App["UI1"].trainingPhase.currentText() == "Burst Experiment":
                App["UI1"].cohLevel.setValue(5)
                Session = Burst_Coherence
            elif App["UI1"].trainingPhase.currentText() == "Prior Experiment":
                Session = Prior_Coherence

            self.startSession(Session, App)
            self.startBehavior(App)
            # if Cam['Camera']:
            #     self.startCamera(Cam)
