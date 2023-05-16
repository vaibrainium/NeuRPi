import sys
import time

import cv2
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets, uic

Ui_rig, rigclass = uic.loadUiType("protocols/random_dot_motion/gui/rdk_rig.ui")
Ui_summary, summaryclass = uic.loadUiType("protocols/random_dot_motion/gui/summary.ui")
camera_index = 0


class TaskGUI(rigclass):
    comm_to_taskgui = QtCore.pyqtSignal(dict)
    comm_from_taskgui = QtCore.pyqtSignal(dict)

    def __init__(self, rig_id=None):
        super().__init__()
        # Load GUIs
        # main rig window
        self.rig_id = rig_id
        self.rig = Ui_rig()
        self.rig.setupUi(self)
        self.rig.close_experiment.hide()
        # summary dialogue
        self.summary_window = QtWidgets.QDialog()
        self.summary = Ui_summary()
        self.summary.setupUi(self.summary_window)
        self.summary_window.raise_()
        # Camera
        self.video_device = cv2.VideoCapture(camera_index)
        # Rig parameter variables
        self.session_clock = {}
        self.pause_time = None
        self.session_start_time = None
        self.session_display_clock = None
        self.session_pause_time = 0
        self.session_timer = QtCore.QTimer()
        self.trial_timer = QtCore.QTimer()
        self.camera_timer = QtCore.QTimer()
        self.trial_clock = None
        self.stopped = False
        self.state = "IDLE"

        # Task parameter variables
        self.coherences = [-100, -72, -36, -18, -9, 0, 9, 18, 36, 72, 100]
        self.initialize_plots()

        # Setting up gui intearaction connections
        self.comm_to_taskgui.connect(self.update_gui)
        self.rig.reward_left.clicked.connect(lambda: self.reward("reward_left"))
        self.rig.reward_right.clicked.connect(lambda: self.reward("reward_right"))
        self.rig.reward_volume.valueChanged.connect(
            lambda: self.reward("update_reward")
        )
        self.rig.toggle_left_reward.clicked.connect(
            lambda: self.reward("toggle_left_reward")
        )
        self.rig.toggle_right_reward.clicked.connect(
            lambda: self.reward("toggle_right_reward")
        )
        self.rig.lick_threshold_left.valueChanged.connect(
            lambda: self.lick_sensor("update_lick_threshold_left")
        )
        self.rig.lick_threshold_right.valueChanged.connect(
            lambda: self.lick_sensor("update_lick_threshold_right")
        )
        self.rig.reset_lick_sensor.clicked.connect(
            lambda: self.lick_sensor("reset_lick_sensor")
        )
        self.rig.pause_experiment.clicked.connect(lambda: self.pause_experiment())
        self.rig.stop_experiment.clicked.connect(lambda: self.stop_experiment())
        self.rig.close_experiment.clicked.connect(lambda: self.close_experiment())
        self.summary.okay.clicked.connect(lambda: self.save_summary())

    ###################################################################################################
    # GUI Functions
    def set_rig_configuration(self, prefs={}):
        try:
            hardware = prefs.get('HARDWARE')
            self.rig.lick_threshold_left.setValue(hardware.Arduino.Primary.lick.threshold_left)
            self.rig.lick_threshold_right.setValue(hardware.Arduino.Primary.lick.threshold_right)
        except EOFError:
            pass

    def initialize_plots(
        self,
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
            [[(v, str(v)) for v in self.coherences]]
        )
        # Total Trial Plot
        self.rig.trial_distribution.setTitle("Total Trials", color="r", size="10pt")
        self.rig.trial_distribution.setXRange(0, len(self.coherences))
        self.rig.trial_distribution.setInteractive(False)
        self.rig.trial_distribution.setLabel("left", "Trials")
        self.rig.trial_distribution.setLabel("bottom", "Coherence")
        self.rig.trial_distribution.showGrid(x=False, y=True, alpha=0.6)
        ticks = [list(zip(range(len(self.coherences)), list(self.coherences)))]
        self.rig.trial_distribution.getAxis("bottom").setTicks(ticks)
        # Reaction Time Plot
        self.rig.rt_distribution.setTitle("Reaction Times", color="r", size="10pt")
        self.rig.rt_distribution.setXRange(-100, 100)
        self.rig.rt_distribution.setInteractive(False)
        self.rig.rt_distribution.setLabel("left", "Reaction Time")
        self.rig.rt_distribution.setLabel("bottom", "Coherence")
        self.rig.rt_distribution.showGrid(x=False, y=True, alpha=0.6)
        self.rig.rt_distribution.getAxis("bottom").setTicks(
            [[(v, str(v)) for v in self.coherences]]
        )

    def start_experiment(self):
        self.state = "RUNNING"
        # starting session clock
        self.session_clock = {
            "start": time.time(),
            "display": 0,
            "pause": 0,
            "timer": QtCore.QTimer(),
            "end": None,
        }
        self.session_timer.timeout.connect(lambda: self.update_session_clock())
        self.session_timer.start(1000)
        # starting camera
        if not self.video_device.isOpened():
            print("Error: Could not open camera.")
        self.camera_timer.timeout.connect(self.update_video_image)
        self.camera_timer.start(30)

    def start_session_clock(self):
        self.session_timer.timeout.connect(lambda: self.update_session_clock())
        self.session_timer.start(1000)

    def update_session_clock(self):
        self.session_display_clock = (
            time.time() - self.session_clock["start"] - self.session_clock["pause"]
        )
        self.rig.session_timer.display(int(self.session_display_clock))

    def stop_session_clock(self):
        self.session_timer.stop()

    def update_video_image(self):
        try:
            # Read a frame from the camera
            ret, frame = self.video_device.read()
            if ret:
                # Convert the frame to RGB format
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Convert the frame to a QImage
                image = QtGui.QImage(
                    frame.data,
                    frame.shape[1],
                    frame.shape[0],
                    QtGui.QImage.Format_RGB888,
                )

                # Display the image on the label
                self.rig.video_stream.setPixmap(QtGui.QPixmap.fromImage(image))
        except:
            self.session_timer.stop()

    # def start_trial_clock(self, trial_start_time=time.time()):
    #     self.session_timer.timeout.connect(lambda: self.update_trial_clock(trial_start_time))
    #     self.trial_timer.start(10)

    # def stop_trial_clock(self):
    #     self.trial_timer.stop()

    # def update_trial_timer(self, trial_start_time):
    #     self.session_display_clock = time.time() - trial_start_time
    #     self.rig.session_timer.display(int(self.session_display_clock))

    def reward(self, message: str):
        self.forward_signal(
            {
                "to": self.rig_id,
                "key": "EVENT",
                "value": {
                    "key": "HARDWARE",
                    "value": {"key": message, "value": self.rig.reward_volume.value()},
                },
            }
        )

    def lick_sensor(self, message: str):
        """Function to modify lick sensor properties

        Args:
            message (str): _description_
        """
        temp_val = None
        if message == "update_lick_threshold_left":
            temp_val = round(self.rig.lick_threshold_left.value(), 3)
        elif message == "update_lick_threshold_right":
            temp_val = round(self.rig.lick_threshold_right.value(), 3)

        self.forward_signal(
            {
                "to": self.rig_id,
                "key": "EVENT",
                "value": {
                    "key": "HARDWARE",
                    "value": {"key": message, "value": temp_val},
                },
            }
        )

    def pause_experiment(self):
        """
        If session is not paused, pause it and send the signal to terminal.
        If session is paused, resume it and send the corresponding singal to termianl.
        """
        if self.state == "RUNNING":
            self.forward_signal(
                {"to": self.rig_id, "key": "EVENT", "value": {"key": "PAUSE"}}
            )
            self.rig.pause_experiment.setStyleSheet("background-color: green")
            self.rig.pause_experiment.setText("Resume")
            self.state = "PAUSED"
            self.pause_time = time.time()
        elif self.state == "PAUSED":
            self.forward_signal(
                {"to": self.rig_id, "key": "EVENT", "value": {"key": "RESUME"}}
            )
            self.rig.pause_experiment.setStyleSheet("background-color: rgb(255,170,0)")
            self.rig.pause_experiment.setText("Pause")
            self.state = "RUNNING"
            self.session_clock["pause"] = time.time() - self.pause_time

    def stop_experiment(self):
        """End task after current trial finishes"""
        self.forward_signal({"to": self.rig_id, "key": "STOP", "value": None})
        self.state = "STOPPED"
        self.stop_session_clock()

    def show_summary_window(self, value):
        # TODO: implement function to show on summery window
        """Show summary window with summarized data"""
        summary_data = (
            time.ctime(self.session_clock["start"])
            + "\n\n"
            + time.ctime(self.session_clock["end"])
            + "\n\n"
            + str(value["trial_counters"]["valid"])
            + " ("
            + ", ".join(str(int(i)) for i in value["plots"]["total_trial_distribution"] if i!=0.0)
            + ")"
            + "\n\n"
            + str(round(value["plots"]["running_accuracy"][-1][1]*100))
            + "% ("
            + ", ".join(str(round(i,2)) for i in value["plots"]["psychometric_function"] if np.isnan(i) == False)
            + ")"
            + "\n\n"
            + " ("
            + ", ".join(str(round(i,2)) for i in value["plots"]["reaction_time_distribution"] if np.isnan(i) == False)
            + ")"
            + "\n\n"
            + str(value["trial_counters"]["incorrect"])
            + "/"
            + str(value["trial_counters"]["attempt"])
            + ";   "
            + str(value["trial_counters"]["noresponse"])
            + "/"
            + str(value["trial_counters"]["attempt"])
            + "\n\n"
            + str(int(float(self.rig.total_reward.text())))
            + " ul @ "
            + str(self.rig.reward_volume.value())
            + " ul"
        )

        self.summary.summary_data.setText(summary_data)
        self.summary_window.show()

    def save_summary(self):
        # TODO: implement method to save summary calculations to designated folders
        if (
            self.summary.baseline_weight.toPlainText() == ""
            or self.summary.start_weight.toPlainText() == ""
            or self.summary.end_weight.toPlainText() == ""
        ):
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Forgot to Enter one of the weights")
            msg.setWindowTitle("Error")
            msg.exec_()
        else:
            # TODO: Save summary
            self.rig.close_experiment.show()
            self.summary_window.hide()

    def close_experiment(self):
        """Task has ended but waiting to trial to end to close session"""
        try:
            self.video_device.release()
            self.video_device.destroyAllWindows()
        except:
            pass
        self.forward_signal({"to": "main_gui", "key": "KILL", "value": None})

    ###################################################################################################
    # Outgoing communication
    def forward_signal(self, message):
        message["rig_id"] = self.rig_id
        self.comm_from_taskgui.emit(message)

    ###################################################################################################
    # Incoming communication
    def update_gui(self, value):
        if "state" in value.keys():
            if value["state"] == "RUNNING":
                pass

        if "trial_counters" in value.keys():
            self.update_trials(value["trial_counters"])

        if "stimulus_pars" in value.keys():
            self.update_stimulus(value["stimulus_pars"])

        if "plots" in value.keys():
            self.update_plots(value["plots"])

        if "reward_volume" in value.keys():
            self.rig.reward_volume.setValue(value["reward_volume"])

        if "total_reward" in value.keys():
            try:
                self.rig.total_reward.setText(str(round(value["total_reward"],2)))
            except:
                self.rig.total_reward.setText(str(value["total_reward"]))

        # Close session and Task GUI
        if "TRIAL_END" in value.keys() and self.state == "STOPPED":
            self.session_clock["end"] = time.time()
            self.session_clock["timer"].stop()
            self.show_summary_window(value)

    def update_trials(self, value):
        self.rig.attempt_trials.setText(str(value["attempt"]))
        self.rig.valid_trials.setText(str(value["valid"]))
        self.rig.correct_trials.setText(str(value["correct"]))
        self.rig.incorrect_trials.setText(str(value["incorrect"]))
        self.rig.noresponse_trials.setText(str(value["noresponse"]))

    def update_stimulus(self, value):
        self.rig.current_stimulus.setText(str(value["coherence"]))

    def update_plots(self, value):
        # updating running accuracy
        try:
            self.rig.accuracy_plot.plot(
                x=list(list(zip(*value["running_accuracy"]))[0]),
                y=list(list(zip(*value["running_accuracy"]))[1]),
                pen=None,
                symbol="o",
                symbolPen="w",
                symbolBrush=0.2,
                name="Accuracy",
                clear=True,
            )
        except:
            pass

        # updating psychometric function
        try:
            coh, psych = [], []
            for i, y in enumerate(value["psychometric_function"]):
                if str(y) != "nan":
                    coh.append(self.coherences[i])
                    psych.append(y)
            self.rig.psychometric_plot.plot(
                x=coh,
                y=psych,
                pen="g",
                symbol="o",
                symbolPen="g",
                symbolBrush=0.2,
                name="Psych",
                clear=True,
            )
        except:
            pass

        # updating total distribution
        try:
            self.rig.trial_distribution.clear()
            bargraph = pg.BarGraphItem(
                x=np.arange(len(self.coherences)),
                height=value["total_trial_distribution"],
                width=0.6,
                brush="w",
            )
            self.rig.trial_distribution.addItem(bargraph)
        except:
            pass

        # updating reaction time distribution
        try:
            coh, rt_dist = [], []
            for i, y in enumerate(value["reaction_time_distribution"]):
                if str(y) != "nan":
                    coh.append(self.coherences[i])
                    rt_dist.append(y)
            self.rig.rt_distribution.plot(
                x=coh,
                y=rt_dist,
                pen="w",
                symbol="o",
                symbolPen="w",
                symbolBrush=0.2,
                name="RT",
                clear=True,
            )
        except:
            pass


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = TaskGUI()
    window.show()
    window.start_experiment()
    sys.exit(app.exec_())

