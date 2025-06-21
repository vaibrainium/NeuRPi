import sys
import time
from pathlib import Path

# import cv2
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets, uic
from pyqtgraph import exporters

from neurpi.utils import code_to_str

# Get the absolute path to the UI files
_current_dir = Path(__file__).parent
Ui_rig, rigclass = uic.loadUiType(str(_current_dir / "rdk_rig.ui"))
Ui_summary, summaryclass = uic.loadUiType(str(_current_dir / "summary.ui"))
camera_index = 0


class TaskGUI(rigclass):
    tabActiveStateChanged = QtCore.pyqtSignal(bool)

    comm_to_taskgui = QtCore.pyqtSignal(dict)
    comm_from_taskgui = QtCore.pyqtSignal(dict)

    def __init__(self, rig_id=None, session_info=None, subject=None):
        super().__init__()
        self.rig_gui_active = False
        # Load GUIs
        self.rig_id = rig_id
        self.subject = subject
        self.protocol = session_info.protocol
        self.experiment = session_info.experiment
        self.configuration = session_info.configuration

        self.summary_data = None

        # main rig window
        try:
            self.rig = Ui_rig()
            self.rig.setupUi(self)
            self.rig.close_experiment.hide()
            self.rig.subject_id.setText(f"Subject ID: {self.subject.id}")
            self.rig.age.setText(f"Age: {(self.subject.age)}")
            self.rig.baseline_weight.setText(
                f"% Baseline Weight: {self.subject.prct_weight!s}%",
            )
            self.rig.protocol.setText(f"Protocol: {code_to_str(self.protocol)}")
            self.rig.experiment.setText(f"Experiment: {code_to_str(self.experiment)}")
            self.rig.configuration.setText(
                f"Configuration: {code_to_str(self.configuration)}",
            )
        except Exception as e:
            print(e)
            print("Error: Could not load rig UI.")
            sys.exit(1)

        # summary dialogue
        self.summary_window = QtWidgets.QDialog()
        self.summary = Ui_summary()
        self.summary.setupUi(self.summary_window)
        self.summary_window.raise_()
        self.summary.close.hide()
        # Camera
        # self.video_device = cv2.VideoCapture(camera_index)
        # Rig parameter variables
        self.session_clock = {
            "start": 0,
            "display": 0,
            "pause": 0,
            "timer": QtCore.QTimer(),
            "end": None,
        }
        self.pause_time = None
        self.session_start_time = None
        self.session_display_clock = None
        self.session_pause_time = 0
        self.session_timer = QtCore.QTimer()
        self.trial_timer = QtCore.QTimer()
        self.video_device = None  # cv2.VideoCapture(camera_index)
        self.camera_timer = QtCore.QTimer()
        self.trial_clock = None
        self.stopped = False
        self.state = "IDLE"

        # Task parameter variables
        self.coherences = [-100, -72, -36, -18, -9, 0, 9, 18, 36, 72, 100]
        self.valid_trial_vector = np.array([])
        self.accuracy_vector = np.array([])
        self.outcome_vector = np.array([])

        self.initialize_plots()

        # Setting up gui intearaction connections
        self.tabActiveStateChanged.connect(self.handleTabActiveStateChange)

        self.comm_to_taskgui.connect(self.update_gui)
        self.rig.reward_left.clicked.connect(lambda: self.hardware("reward_left"))
        self.rig.reward_right.clicked.connect(lambda: self.hardware("reward_right"))
        self.rig.reward_volume.valueChanged.connect(
            lambda: self.hardware("update_reward"),
        )
        self.rig.toggle_left_reward.clicked.connect(
            lambda: self.hardware("toggle_left_reward"),
        )
        self.rig.toggle_right_reward.clicked.connect(
            lambda: self.hardware("toggle_right_reward"),
        )

        self.rig.flash_led_left.clicked.connect(lambda: self.hardware("flash_led_left"))
        self.rig.flash_led_center.clicked.connect(
            lambda: self.hardware("flash_led_center"),
        )
        self.rig.flash_led_right.clicked.connect(
            lambda: self.hardware("flash_led_right"),
        )
        self.rig.toggle_led_left.clicked.connect(
            lambda: self.hardware("toggle_led_left"),
        )
        self.rig.toggle_led_right.clicked.connect(
            lambda: self.hardware("toggle_led_right"),
        )

        self.rig.led_and_reward_left.clicked.connect(
            lambda: self.hardware("led_and_reward_left"),
        )
        self.rig.led_and_reward_right.clicked.connect(
            lambda: self.hardware("led_and_reward_right"),
        )

        self.rig.lick_threshold_left.valueChanged.connect(
            lambda: self.lick_sensor("update_lick_threshold_left"),
        )
        self.rig.lick_threshold_right.valueChanged.connect(
            lambda: self.lick_sensor("update_lick_threshold_right"),
        )
        self.rig.reset_lick_sensor.clicked.connect(
            lambda: self.lick_sensor("reset_lick_sensor"),
        )
        self.rig.pause_experiment.clicked.connect(self.pause_experiment)
        self.rig.stop_experiment.clicked.connect(self.stop_experiment)
        self.rig.close_experiment.clicked.connect(self.close_experiment)
        self.summary.okay.clicked.connect(self.hide_summary)
        self.summary.close.clicked.connect(self.close_summary)

    ###################################################################################################
    # GUI Functions
    def handleTabActiveStateChange(self, isActive):
        # This method will be called when the tab's activation state changes
        if isActive:
            self.rig_gui_active = True
            self.start_active_gui_methods()
            # print(f"Tab {self.rig_id} is now active.")
        else:
            self.rig_gui_active = False
            self.stop_active_gui_methods()
            # print(f"Tab {self.rig_id} is now inactive.")

    def set_rig_configuration(self, prefs={}):
        try:
            hardware = prefs.get("HARDWARE")
            self.rig.lick_threshold_left.setValue(
                hardware.Arduino.Primary.lick.threshold_left,
            )
            self.rig.lick_threshold_right.setValue(
                hardware.Arduino.Primary.lick.threshold_right,
            )
        except EOFError:
            pass

    def initialize_plots(self):
        # Accuracy plots
        self.rig.accuracy_plot.setTitle("Accuracy Plot", color="r", size="10pt")
        self.rig.accuracy_plot.setYRange(0, 100)
        self.rig.accuracy_plot.setInteractive(False)
        self.rig.accuracy_plot.setLabel("left", "Accuracy")
        self.rig.accuracy_plot.setLabel("bottom", "Trial No")
        self.rig.accuracy_plot.showGrid(x=False, y=True, alpha=0.6)
        self.accuracy_trace_plot = self.rig.accuracy_plot.plot()
        self.correct_trace_plot = self.rig.accuracy_plot.plot()
        self.incorrect_trace_plot = self.rig.accuracy_plot.plot()
        # Psychometric plots
        self.rig.psychometric_plot.setTitle(
            "Psychometric Function",
            color="r",
            size="10pt",
        )
        self.rig.psychometric_plot.setXRange(-100, 100)
        self.rig.psychometric_plot.setYRange(0, 1)
        self.rig.psychometric_plot.setInteractive(False)
        self.rig.psychometric_plot.setLabel("left", "Proportion of Right Choices")
        self.rig.psychometric_plot.setLabel("bottom", "Coherence")
        self.rig.psychometric_plot.showGrid(x=False, y=True, alpha=0.6)
        self.rig.psychometric_plot.getAxis("bottom").setTicks(
            [[(v, str(v)) for v in self.coherences]],
        )
        self.psychometric_plot = self.rig.psychometric_plot.plot()
        # Total Trial Plot
        self.rig.trial_distribution.setTitle("Total Trials", color="r", size="10pt")
        self.rig.trial_distribution.setXRange(-100, 100)
        self.rig.trial_distribution.setInteractive(False)
        self.rig.trial_distribution.setLabel("left", "Trials")
        self.rig.trial_distribution.setLabel("bottom", "Coherence")
        self.rig.trial_distribution.showGrid(x=False, y=True, alpha=0.6)
        self.rig.trial_distribution.getAxis("bottom").setTicks(
            [[(v, str(v)) for v in self.coherences]],
        )
        self.trial_distribution_plot = self.rig.trial_distribution.plot()
        # Reaction Time Plot
        self.rig.psychometric_plot.getAxis("bottom").setTicks(
            [[(v, str(v)) for v in self.coherences]],
        )
        self.rig.rt_distribution.setTitle("Reaction Times", color="r", size="10pt")
        self.rig.rt_distribution.setXRange(-100, 100)
        self.rig.rt_distribution.setInteractive(False)
        self.rig.rt_distribution.setLabel("left", "Reaction Time")
        self.rig.rt_distribution.setLabel("bottom", "Coherence")
        self.rig.rt_distribution.showGrid(x=False, y=True, alpha=0.6)
        self.rig.rt_distribution.getAxis("bottom").setTicks(
            [[(v, str(v)) for v in self.coherences]],
        )
        self.chronometric_plot = self.rig.rt_distribution.plot()

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
        # self.session_timer.timeout.connect(lambda: self.update_session_clock())
        # self.session_timer.start(1000)

    def start_active_gui_methods(self):
        if self.state != "STOPPED" or self.state != "IDLE":
            self.session_timer.timeout.connect(lambda: self.update_session_clock())
            self.session_timer.start(1000)
        if self.video_device is not None:
            if self.video_device.isOpened():
                self.camera_timer.timeout.connect(self.update_video_image)
                self.camera_timer.start(50)

    def stop_active_gui_methods(self):
        # self.session_timer.timeout.disconnect()
        if self.state != "STOPPED" or self.state != "IDLE":
            self.session_timer.stop()
        if self.video_device is not None:
            self.camera_timer.stop()

    def update_session_clock(self):
        self.session_display_clock = time.time() - self.session_clock["start"] - self.session_clock["pause"]
        self.rig.session_timer.display(int(self.session_display_clock))

    def update_video_image(self):
        pass

    def hardware(self, message: str):
        if "reward" in message:
            value_dict = {"key": message, "value": self.rig.reward_volume.value()}
        elif "flash_led" in message or "toggle" in message:
            value_dict = {"key": message, "value": None}

        self.forward_signal(
            {
                "to": self.rig_id,
                "key": "EVENT",
                "value": {
                    "key": "HARDWARE",
                    "value": value_dict,
                },
            },
        )

    def lick_sensor(self, message: str):
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
            },
        )

    def pause_experiment(self):
        """
        If session is not paused, pause it and send the signal to controller.
        If session is paused, resume it and send the corresponding singal to termianl.
        """
        if self.state == "RUNNING":
            self.forward_signal(
                {"to": self.rig_id, "key": "EVENT", "value": {"key": "PAUSE"}},
            )
            self.rig.pause_experiment.setStyleSheet("background-color: green")
            self.rig.pause_experiment.setText("Resume")
            self.state = "PAUSED"
            self.pause_time = time.time()
            # hide end button
            self.rig.stop_experiment.hide()
        elif self.state == "PAUSED":
            self.forward_signal(
                {"to": self.rig_id, "key": "EVENT", "value": {"key": "RESUME"}},
            )
            self.rig.pause_experiment.setStyleSheet("background-color: rgb(255,170,0)")
            self.rig.pause_experiment.setText("Pause")
            self.state = "RUNNING"
            self.session_clock["pause"] = time.time() - self.pause_time
            # show end button
            self.rig.stop_experiment.show()

    def stop_experiment(self):
        """End task after current trial finishes"""
        self.forward_signal({"to": self.rig_id, "key": "STOP", "value": None})
        self.state = "STOPPED"
        self.stop_active_gui_methods()

    def create_summary_data(self, value):
        self.summary_data = {
            "date": time.strftime(
                "%b-%d-%Y",
                time.localtime(self.session_clock["start"]),
            ),
            "experiment": self.experiment,
            "session": self.subject.session,
            "configuration_used": self.configuration,
            "session_uuid": self.subject.session_uuid,
            "start_time": time.strftime(
                "%H:%M:%S",
                time.localtime(self.session_clock["start"]),
            ),
            "end_time": time.strftime(
                "%H:%M:%S",
                time.localtime(self.session_clock["end"]),
            ),
            "total_reward": int(float(self.rig.total_reward.text())),
            "reward_rate": self.rig.reward_volume.value(),
        }
        # Following variables need not occur in every session
        try:
            self.summary_data["total_attempt"] = value["trial_counters"]["attempt"]
            self.summary_data["total_valid"] = value["trial_counters"]["valid"]
            self.summary_data["total_correct"] = value["trial_counters"]["correct"]
            self.summary_data["total_incorrect"] = value["trial_counters"]["incorrect"]
            self.summary_data["total_noresponse"] = value["trial_counters"]["noresponse"]
            self.summary_data["total_accuracy"] = value["plots"]["running_accuracy"][1]
            self.summary_data["trial_distribution"] = value["plots"]["trial_distribution"]
            self.summary_data["psychometric_function"] = value["plots"]["psychometric_function"]
            self.summary_data["response_time_distribution"] = value["plots"]["response_time_distribution"]
        except:
            # Make them none
            self.summary_data["total_attempt"] = None
            self.summary_data["total_valid"] = None
            self.summary_data["total_correct"] = None
            self.summary_data["total_incorrect"] = None
            self.summary_data["total_noresponse"] = None
            self.summary_data["total_accuracy"] = None
            self.summary_data["trial_distribution"] = None
            self.summary_data["psychometric_function"] = None
            self.summary_data["response_time_distribution"] = None

    def show_summary_window(self, value=None):
        """Show summary window with summarized data"""
        summary_string = (
            f"{time.ctime(self.session_clock['start'])} \n\n"
            f"{time.ctime(self.session_clock['end'])} \n\n"
            f"{self.summary_data['total_valid']} {self.summary_data['trial_distribution']} \n\n"
            f"{self.summary_data['total_accuracy']}% {self.summary_data['psychometric_function']} \n\n"
            f"{self.summary_data['response_time_distribution']} \n\n"
            f"{self.summary_data['total_incorrect']}/{self.summary_data['total_attempt']}; {self.summary_data['total_noresponse']}/{self.summary_data['total_attempt']} \n\n"
            f"{self.summary_data['total_reward']} ul @ {self.summary_data['reward_rate']} ul"
        )

        self.summary.baseline_weight.setText(str(self.subject.baseline_weight))
        self.summary.start_weight.setText(str(self.subject.start_weight))
        self.summary.summary_data.setText(summary_string)
        self.summary.comments.setText(self.rig.notes.toPlainText())
        self.summary_window.show()

    def hide_summary(self):
        if self.summary.baseline_weight.toPlainText() == "" or self.summary.start_weight.toPlainText() == "" or self.summary.end_weight.toPlainText() == "":
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg.setText("Forgot to Enter one of the weights")
            msg.setWindowTitle("Error")
            msg.exec()
        else:
            self.summary_data["baseline_weight"] = float(
                self.summary.baseline_weight.toPlainText(),
            )
            self.summary_data["start_weight"] = float(
                self.summary.start_weight.toPlainText(),
            )
            self.summary_data["end_weight"] = float(
                self.summary.end_weight.toPlainText(),
            )
            self.subject.end_weight = self.summary_data["end_weight"]
            self.summary_data["start_weight_prct"] = round(
                100 * self.summary_data["start_weight"] / self.summary_data["baseline_weight"],
                2,
            )
            self.summary_data["end_weight_prct"] = round(
                100 * self.summary_data["end_weight"] / self.summary_data["baseline_weight"],
                2,
            )
            self.summary_data["comments"] = self.summary.comments.toPlainText()
            self.check_water_requirement()
            self.summary.close.show()

    def close_summary(self):
        self.summary_data["comments"] = self.summary.comments.toPlainText()  # update comments
        self.summary_window.hide()
        self.rig.close_experiment.show()

    def check_water_requirement(self):
        received_water = self.subject.get_today_received_water() + self.summary_data["total_reward"]
        additional_water = 0
        if received_water < 600:
            additional_water = max(additional_water, 600 - received_water)
        if self.summary_data["end_weight_prct"] < 85:
            additional_water = max(
                additional_water,
                ((85 - self.summary_data["end_weight_prct"]) / 100) * self.summary_data["baseline_weight"] * 1000,
            )
        if additional_water > 0:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
            msg.setText(
                f"Did not meet water requirement. Please provide {int(additional_water)} ul of water",
            )
            msg.setWindowTitle("Additional Water")
            msg.exec()
        self.summary_data["additional_water"] = int(additional_water)
        return False

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

        if "block_number" in value.keys():
            self.rig.block_number.setText(str(value["block_number"]))

        if "coherence" in value.keys():
            self.update_stimulus(value["coherence"])

        if "plots" in value.keys():
            if value["is_valid"]:
                self.update_plots(value["plots"])

        if "reward_volume" in value.keys():
            self.rig.reward_volume.setValue(value["reward_volume"])

        if "total_reward" in value.keys():
            self.rig.total_reward.setText(str(round(value["total_reward"], 2)))

        # Close session and Task GUI
        if "TRIAL_END" in value.keys() and self.state == "STOPPED":
            self.session_clock["end"] = time.time()
            self.session_clock["timer"].stop()
            self.create_summary_data(value)

        if "session_files" in value.keys():
            self.show_summary_window(value)
            while not self.rig.close_experiment.isVisible():
                QtWidgets.QApplication.processEvents()
                time.sleep(0.01)

            value["session_files"]["summary"] = self.summary_data
            self.subject.save_files(value["session_files"])
            self.subject.save_history(
                start_weight=self.summary_data["start_weight"],
                end_weight=self.summary_data["end_weight"],
                baseline_weight=self.summary_data["baseline_weight"],
                water_received=self.summary_data["total_reward"],
            )
            self.save_plots()

    def save_plots(self):
        # accuracy plot
        self.rig.task_monitor.setCurrentIndex(0)
        exporter = exporters.ImageExporter(self.rig.accuracy_plot.scene())
        exporter.parameters()["width"] = 800
        exporter.export(self.subject.plots["accuracy"])
        # psychometric plot
        self.rig.task_monitor.setCurrentIndex(1)
        exporter = exporters.ImageExporter(self.rig.psychometric_plot.scene())
        exporter.parameters()["width"] = 800
        exporter.export(self.subject.plots["psychometric"])
        # trial distribution plot
        self.rig.task_monitor.setCurrentIndex(2)
        exporter = exporters.ImageExporter(self.rig.trial_distribution.scene())
        exporter.parameters()["width"] = 800
        exporter.export(self.subject.plots["trials_distribution"])
        # reaction time distribution plot
        self.rig.task_monitor.setCurrentIndex(3)
        exporter = exporters.ImageExporter(self.rig.rt_distribution.scene())
        exporter.parameters()["width"] = 800
        exporter.export(self.subject.plots["rt_distribution"])
        # resetting plot index
        self.rig.task_monitor.setCurrentIndex(0)

    def update_trials(self, value):
        self.rig.attempt_trials.setText(str(value["attempt"]))
        self.rig.valid_trials.setText(str(value["valid"]))
        self.rig.correct_trials.setText(str(value["correct"]))
        self.rig.incorrect_trials.setText(str(value["incorrect"]))
        self.rig.noresponse_trials.setText(str(value["noresponse"]))

    def update_stimulus(self, coherence):
        self.rig.current_stimulus.setText(str(coherence))

    def update_plots(self, value):
        # updating running accuracy
        try:
            self.valid_trial_vector = np.append(
                self.valid_trial_vector,
                value["running_accuracy"][0],
            )
            self.accuracy_vector = np.append(
                self.accuracy_vector,
                value["running_accuracy"][1],
            )
            self.outcome_vector = np.append(
                self.outcome_vector,
                value["running_accuracy"][2],
            )
            correct_idx = np.squeeze(np.argwhere(self.outcome_vector == 1), axis=1)
            if correct_idx.size > 0:
                self.correct_trace_plot.setData(
                    self.valid_trial_vector[correct_idx],
                    self.accuracy_vector[correct_idx],
                    pen=None,
                    symbol="o",
                    symbolPen="g",
                    symbolBrush=0.2,
                    name="Correct",
                )
            incorrect_idx = np.squeeze(np.argwhere(self.outcome_vector == 0), axis=1)
            if incorrect_idx.size > 0:
                self.incorrect_trace_plot.setData(
                    self.valid_trial_vector[incorrect_idx],
                    self.accuracy_vector[incorrect_idx],
                    pen=None,
                    symbol="o",
                    symbolPen="r",
                    symbolBrush=0.2,
                    name="Incorrect",
                )
        except:
            pass

        # updating psychometric function
        try:
            value["psychometric_function"] = {float(k): v for k, v in value["psychometric_function"].items() if not np.isnan(v)}
            coherences, psych = zip(*sorted(value["psychometric_function"].items()))
            if len(coherences) > 0:
                self.psychometric_plot.setData(
                    x=coherences,
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
            value["trial_distribution"] = {float(k): v for k, v in value["trial_distribution"].items() if not np.isnan(v)}
            coherences, trials = zip(*sorted(value["trial_distribution"].items()))
            self.rig.trial_distribution.clear()
            if len(coherences) > 0:
                bargraph = pg.BarGraphItem(
                    x=list(coherences),
                    height=list(trials),
                    width=5,
                    brush="w",
                )
                self.rig.trial_distribution.addItem(bargraph)
        except:
            pass
        # updating reaction time distribution
        try:
            value["response_time_distribution"] = {float(k): v for k, v in value["response_time_distribution"].items() if not np.isnan(v)}
            coherences, rt_dist = zip(
                *sorted(value["response_time_distribution"].items()),
            )
            if len(coherences) > 0:
                self.chronometric_plot.setData(
                    x=coherences,
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
    from omegaconf import OmegaConf

    session_info = {"protocol": "rdk", "experiment": "rdk", "configuration": "test"}
    session_info = OmegaConf.create(session_info)

    subject = {"name": "test", "session": 1, "session_uuid": "test", "prct_weight": 10}
    subject = OmegaConf.create(subject)
    window = TaskGUI(rig_id="Test", session_info=session_info, subject=subject)

    value = {"running_accuracy": [1, 100, 1]}
    window.update_plots(value)
    value = {"running_accuracy": [2, 50, 0]}
    window.update_plots(value)
    value = {"running_accuracy": [3, 66, 1]}
    window.update_plots(value)

    window.show()
    window.start_experiment()
    sys.exit(app.exec())
