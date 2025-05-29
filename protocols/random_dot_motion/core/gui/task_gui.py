import sys
import time
import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets, uic
from pyqtgraph import exporters
from typing import Any, Dict, Optional

Ui_rig, rigclass = uic.loadUiType("protocols/random_dot_motion/core/gui/rdk_rig.ui")
Ui_summary, summaryclass = uic.loadUiType("protocols/random_dot_motion/core/gui/summary.ui")
camera_index = 0

def code_to_str(var: str) -> str:
    """Convert code variable to display string."""
    return str.title(var.replace("_", " "))

def str_to_code(var: str) -> str:
    """Convert display string to code variable."""
    return var.replace(" ", "_").lower()

class TaskGUI(rigclass):
    tabActiveStateChanged = QtCore.pyqtSignal(bool)
    comm_to_taskgui = QtCore.pyqtSignal(dict)
    comm_from_taskgui = QtCore.pyqtSignal(dict)

    def __init__(self, rig_id=None, session_info=None, subject=None):
        super().__init__()
        self.rig_gui_active = False
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
            self.rig.subject_id.setText(self.subject.name)
            self.rig.age.setText(str(self.subject.age))
            self.rig.baseline_weight.setText(str(self.subject.prct_weight))
            self.rig.protocol.setText(code_to_str(self.protocol))
            self.rig.experiment.setText(code_to_str(self.experiment))
            self.rig.configuration.setText(code_to_str(self.configuration))
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
        self.video_device = None
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

        # GUI interaction connections
        self.tabActiveStateChanged.connect(self.handleTabActiveStateChange)
        self.comm_to_taskgui.connect(self.update_gui)
        self.rig.reward_left.clicked.connect(lambda: self.hardware("reward_left"))
        self.rig.reward_right.clicked.connect(lambda: self.hardware("reward_right"))
        self.rig.reward_volume.valueChanged.connect(lambda: self.hardware("update_reward"))
        self.rig.toggle_left_reward.clicked.connect(lambda: self.hardware("toggle_left_reward"))
        self.rig.toggle_right_reward.clicked.connect(lambda: self.hardware("toggle_right_reward"))
        self.rig.flash_led_left.clicked.connect(lambda: self.hardware("flash_led_left"))
        self.rig.flash_led_center.clicked.connect(lambda: self.hardware("flash_led_center"))
        self.rig.flash_led_right.clicked.connect(lambda: self.hardware("flash_led_right"))
        self.rig.toggle_led_left.clicked.connect(lambda: self.hardware("toggle_led_left"))
        self.rig.toggle_led_right.clicked.connect(lambda: self.hardware("toggle_led_right"))
        self.rig.led_and_reward_left.clicked.connect(lambda: self.hardware("led_and_reward_left"))
        self.rig.led_and_reward_right.clicked.connect(lambda: self.hardware("led_and_reward_right"))
        self.rig.lick_threshold_left.valueChanged.connect(lambda: self.lick_sensor("update_lick_threshold_left"))
        self.rig.lick_threshold_right.valueChanged.connect(lambda: self.lick_sensor("update_lick_threshold_right"))
        self.rig.reset_lick_sensor.clicked.connect(lambda: self.lick_sensor("reset_lick_sensor"))
        self.rig.pause_experiment.clicked.connect(self.pause_experiment)
        self.rig.stop_experiment.clicked.connect(self.stop_experiment)
        self.rig.close_experiment.clicked.connect(self.close_experiment)
        self.summary.okay.clicked.connect(self.hide_summary)
        self.summary.close.clicked.connect(self.close_summary)

    # --- GUI Functions ---

    def handleTabActiveStateChange(self, isActive: bool):
        """Handle tab activation state change."""
        self.rig_gui_active = isActive
        if isActive:
            self.start_active_gui_methods()
        else:
            self.stop_active_gui_methods()

    def set_rig_configuration(self, prefs: dict = {}):
        """Set rig configuration from preferences."""
        try:
            hardware = prefs.get("HARDWARE")
            self.rig.lick_threshold_left.setValue(hardware.Arduino.Primary.lick.threshold_left)
            self.rig.lick_threshold_right.setValue(hardware.Arduino.Primary.lick.threshold_right)
        except (AttributeError, EOFError):
            pass

    def initialize_plots(self):
        """Initialize all plots."""
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
        self.rig.psychometric_plot.setTitle("Psychometric Function", color="r", size="10pt")
        self.rig.psychometric_plot.setXRange(-100, 100)
        self.rig.psychometric_plot.setYRange(0, 1)
        self.rig.psychometric_plot.setInteractive(False)
        self.rig.psychometric_plot.setLabel("left", "Proportion of Right Choices")
        self.rig.psychometric_plot.setLabel("bottom", "Coherence")
        self.rig.psychometric_plot.showGrid(x=False, y=True, alpha=0.6)
        self.rig.psychometric_plot.getAxis("bottom").setTicks([[(v, str(v)) for v in self.coherences]])
        self.psychometric_plot = self.rig.psychometric_plot.plot()
        # Total Trial Plot
        self.rig.trial_distribution.setTitle("Total Trials", color="r", size="10pt")
        self.rig.trial_distribution.setXRange(-100, 100)
        self.rig.trial_distribution.setInteractive(False)
        self.rig.trial_distribution.setLabel("left", "Trials")
        self.rig.trial_distribution.setLabel("bottom", "Coherence")
        self.rig.trial_distribution.showGrid(x=False, y=True, alpha=0.6)
        self.rig.trial_distribution.getAxis("bottom").setTicks([[(v, str(v)) for v in self.coherences]])
        self.trial_distribution_plot = self.rig.trial_distribution.plot()
        # Reaction Time Plot
        self.rig.rt_distribution.setTitle("Reaction Times", color="r", size="10pt")
        self.rig.rt_distribution.setXRange(-100, 100)
        self.rig.rt_distribution.setInteractive(False)
        self.rig.rt_distribution.setLabel("left", "Reaction Time")
        self.rig.rt_distribution.setLabel("bottom", "Coherence")
        self.rig.rt_distribution.showGrid(x=False, y=True, alpha=0.6)
        self.rig.rt_distribution.getAxis("bottom").setTicks([[(v, str(v)) for v in self.coherences]])
        self.chronometric_plot = self.rig.rt_distribution.plot()

    def start_experiment(self):
        """Start the experiment and session clock."""
        self.state = "RUNNING"
        self.session_clock = {
            "start": time.time(),
            "display": 0,
            "pause": 0,
            "timer": QtCore.QTimer(),
            "end": None,
        }

    def start_active_gui_methods(self):
        """Start timers and video if not stopped or idle."""
        if self.state not in ("STOPPED", "IDLE"):
            self.session_timer.timeout.connect(self.update_session_clock)
            self.session_timer.start(1000)
        if self.video_device is not None and self.video_device.isOpened():
            self.camera_timer.timeout.connect(self.update_video_image)
            self.camera_timer.start(50)

    def stop_active_gui_methods(self):
        """Stop timers and video if not stopped or idle."""
        if self.state not in ("STOPPED", "IDLE"):
            self.session_timer.stop()
        if self.video_device is not None:
            self.camera_timer.stop()

    def update_session_clock(self):
        """Update the session clock display."""
        self.session_display_clock = time.time() - self.session_clock["start"] - self.session_clock["pause"]
        self.rig.session_timer.display(int(self.session_display_clock))

    def update_video_image(self):
        """Update video image (stub)."""
        pass

    def hardware(self, message: str):
        """Send hardware event."""
        if "reward" in message:
            value_dict = {"key": message, "value": self.rig.reward_volume.value()}
        else:
            value_dict = {"key": message, "value": None}
        self.forward_signal({
            "to": self.rig_id,
            "key": "EVENT",
            "value": {"key": "HARDWARE", "value": value_dict},
        })

    def lick_sensor(self, message: str):
        """Send lick sensor event."""
        temp_val = None
        if message == "update_lick_threshold_left":
            temp_val = round(self.rig.lick_threshold_left.value(), 3)
        elif message == "update_lick_threshold_right":
            temp_val = round(self.rig.lick_threshold_right.value(), 3)
        self.forward_signal({
            "to": self.rig_id,
            "key": "EVENT",
            "value": {"key": "HARDWARE", "value": {"key": message, "value": temp_val}},
        })

    def pause_experiment(self):
        """
        Pause or resume the experiment and update GUI accordingly.
        """
        if self.state == "RUNNING":
            self.forward_signal({"to": self.rig_id, "key": "EVENT", "value": {"key": "PAUSE"}})
            self.rig.pause_experiment.setStyleSheet("background-color: green")
            self.rig.pause_experiment.setText("Resume")
            self.state = "PAUSED"
            self.pause_time = time.time()
            self.rig.stop_experiment.hide()
        elif self.state == "PAUSED":
            self.forward_signal({"to": self.rig_id, "key": "EVENT", "value": {"key": "RESUME"}})
            self.rig.pause_experiment.setStyleSheet("background-color: rgb(255,170,0)")
            self.rig.pause_experiment.setText("Pause")
            self.state = "RUNNING"
            self.session_clock["pause"] = time.time() - self.pause_time
            self.rig.stop_experiment.show()

    def stop_experiment(self):
        """End task after current trial finishes."""
        self.forward_signal({"to": self.rig_id, "key": "STOP", "value": None})
        self.state = "STOPPED"
        self.stop_active_gui_methods()

    def create_summary_data(self, value: dict):
        """Create summary data from session values."""
        self.summary_data = {
            "date": time.strftime("%b-%d-%Y", time.localtime(self.session_clock["start"])),
            "experiment": self.experiment,
            "session": self.subject.session,
            "session_uuid": self.subject.session_uuid,
            "configuration": self.configuration,
            "start_time": time.strftime("%H:%M:%S", time.localtime(self.session_clock["start"])),
            "end_time": time.strftime("%H:%M:%S", time.localtime(self.session_clock["end"])),
            "total_reward": int(float(self.rig.total_reward.text())),
            "reward_rate": self.rig.reward_volume.value(),
        }
        # Optional session variables
        try:
            tc = value["trial_counters"]
            plots = value["plots"]
            self.summary_data.update({
                "total_attempt": tc.get("attempt"),
                "total_valid": tc.get("valid"),
                "total_correct": tc.get("correct"),
                "total_incorrect": tc.get("incorrect"),
                "total_noresponse": tc.get("noresponse"),
                "total_accuracy": plots.get("running_accuracy", [None, None])[1],
                "trial_distribution": plots.get("trial_distribution"),
                "psychometric_function": plots.get("psychometric_function"),
                "response_time_distribution": plots.get("response_time_distribution"),
            })
        except Exception as e:
            # Set all optional fields to None if missing
            for key in [
                "total_attempt", "total_valid", "total_correct", "total_incorrect",
                "total_noresponse", "total_accuracy", "trial_distribution",
                "psychometric_function", "response_time_distribution"
            ]:
                self.summary_data[key] = None

    def show_summary_window(self, value: Optional[dict] = None):
        """Show summary window with summarized data."""
        s = self.summary_data
        summary_string = (
            f"{time.ctime(self.session_clock['start'])} \n\n"
            f"{time.ctime(self.session_clock['end'])} \n\n"
            f"{s['total_valid']} {s['trial_distribution']} \n\n"
            f"{s['total_accuracy']}% {s['psychometric_function']} \n\n"
            f"{s['response_time_distribution']} \n\n"
            f"{s['total_incorrect']}/{s['total_attempt']}; {s['total_noresponse']}/{s['total_attempt']} \n\n"
            f"{s['total_reward']} ul @ {s['reward_rate']} ul"
        )
        self.summary.baseline_weight.setText(str(self.subject.baseline_weight))
        self.summary.start_weight.setText(str(self.subject.start_weight))
        self.summary.summary_data.setText(summary_string)
        self.summary_window.show()

    def hide_summary(self):
        """Hide summary window after validating weights."""
        if any(
            self.summary.baseline_weight.toPlainText() == "",
            self.summary.start_weight.toPlainText() == "",
            self.summary.end_weight.toPlainText() == "",
        ):
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText("Forgot to Enter one of the weights")
            msg.setWindowTitle("Error")
            msg.exec_()
            return
        self.summary_data["baseline_weight"] = float(self.summary.baseline_weight.toPlainText())
        self.summary_data["start_weight"] = float(self.summary.start_weight.toPlainText())
        self.summary_data["end_weight"] = float(self.summary.end_weight.toPlainText())
        self.subject.end_weight = self.summary_data["end_weight"]
        self.summary_data["start_weight_prct"] = round(100 * self.summary_data["start_weight"] / self.summary_data["baseline_weight"], 2)
        self.summary_data["end_weight_prct"] = round(100 * self.summary_data["end_weight"] / self.summary_data["baseline_weight"], 2)
        self.summary_data["comments"] = self.summary.comments.toPlainText()
        self.check_water_requirement()
        self.summary.close.show()

    def close_summary(self):
        """Close the summary window and update comments."""
        self.summary_data["comments"] = self.summary.comments.toPlainText()
        self.summary_window.hide()
        self.rig.close_experiment.show()

    def check_water_requirement(self) -> bool:
        """Check if water requirement is met and show message if not."""
        received_water = self.subject.get_today_received_water() + self.summary_data["total_reward"]
        additional_water = 0
        if received_water < 600:
            additional_water = max(additional_water, 600 - received_water)
        if self.summary_data["end_weight_prct"] < 85:
            additional_water = max(
                additional_water,
                ((85 - self.summary_data["end_weight_prct"]) / 100) * self.summary_data["baseline_weight"] * 1000
            )
        if additional_water > 0:
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setText(f"Did not meet water requirement. Please provide {int(additional_water)} ul of water")
            msg.setWindowTitle("Additional Water")
            msg.exec_()
        self.summary_data["additional_water"] = int(additional_water)
        return False

    def close_experiment(self):
        """Task has ended but waiting for trial to end to close session."""
        try:
            self.video_device.release()
            self.video_device.destroyAllWindows()
        except Exception:
            pass
        self.forward_signal({"to": "main_gui", "key": "KILL", "value": None})

    # --- Outgoing communication ---

    def forward_signal(self, message: dict):
        """Emit a message from the task GUI."""
        message["rig_id"] = self.rig_id
        self.comm_from_taskgui.emit(message)

    # --- Incoming communication ---

    def update_gui(self, value: dict):
        """Update GUI based on incoming values."""
        if "state" in value:
            if value["state"] == "RUNNING":
                pass

        if "trial_counters" in value:
            self.update_trials(value["trial_counters"])

        if "block_number" in value:
            self.rig.block_number.setText(str(value["block_number"]))

        if "coherence" in value:
            self.update_stimulus(value["coherence"])

        if "plots" in value and value.get("is_valid", False):
            self.update_plots(value["plots"])

        if "reward_volume" in value:
            self.rig.reward_volume.setValue(value["reward_volume"])

        if "total_reward" in value:
            self.rig.total_reward.setText(str(round(value["total_reward"], 2)))

        # Close session and Task GUI
        if "TRIAL_END" in value and self.state == "STOPPED":
            self.session_clock["end"] = time.time()
            self.session_clock["timer"].stop()
            self.create_summary_data(value)

        if "session_files" in value:
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
        """Save all plots as images."""
        # accuracy plot
        self.rig.TaskMonitor.setCurrentIndex(0)
        exporter = exporters.ImageExporter(self.rig.accuracy_plot.scene())
        exporter.parameters()["width"] = 800
        exporter.export(self.subject.plots["accuracy"])
        # psychometric plot
        self.rig.TaskMonitor.setCurrentIndex(1)
        exporter = exporters.ImageExporter(self.rig.psychometric_plot.scene())
        exporter.parameters()["width"] = 800
        exporter.export(self.subject.plots["psychometric"])
        # trial distribution plot
        self.rig.TaskMonitor.setCurrentIndex(2)
        exporter = exporters.ImageExporter(self.rig.trial_distribution.scene())
        exporter.parameters()["width"] = 800
        exporter.export(self.subject.plots["trials_distribution"])
        # reaction time distribution plot
        self.rig.TaskMonitor.setCurrentIndex(3)
        exporter = exporters.ImageExporter(self.rig.rt_distribution.scene())
        exporter.parameters()["width"] = 800
        exporter.export(self.subject.plots["rt_distribution"])
        # resetting plot index
        self.rig.TaskMonitor.setCurrentIndex(0)

    def update_trials(self, value: dict):
        """Update trial counters in the GUI."""
        self.rig.attempt_trials.setText(str(value["attempt"]))
        self.rig.valid_trials.setText(str(value["valid"]))
        self.rig.correct_trials.setText(str(value["correct"]))
        self.rig.incorrect_trials.setText(str(value["incorrect"]))
        self.rig.noresponse_trials.setText(str(value["noresponse"]))

    def update_stimulus(self, coherence: Any):
        """Update current stimulus display."""
        self.rig.current_stimulus.setText(str(coherence))

    def update_plots(self, value: dict):
        """Update all plots with new data."""
        # updating running accuracy
        try:
            self.valid_trial_vector = np.append(self.valid_trial_vector, value["running_accuracy"][0])
            self.accuracy_vector = np.append(self.accuracy_vector, value["running_accuracy"][1])
            self.outcome_vector = np.append(self.outcome_vector, value["running_accuracy"][2])
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
        except Exception:
            pass

        # updating psychometric function
        try:
            pf = {float(k): v for k, v in value["psychometric_function"].items() if not np.isnan(v)}
            if pf:
                coherences, psych = zip(*sorted(pf.items()))
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
        except Exception:
            pass
        # updating total distribution
        try:
            td = {float(k): v for k, v in value["trial_distribution"].items() if not np.isnan(v)}
            self.rig.trial_distribution.clear()
            if td:
                coherences, trials = zip(*sorted(td.items()))
                bargraph = pg.BarGraphItem(
                    x=list(coherences),
                    height=list(trials),
                    width=5,
                    brush="w",
                )
                self.rig.trial_distribution.addItem(bargraph)
        except Exception:
            pass
        # updating reaction time distribution
        try:
            rtd = {float(k): v for k, v in value["response_time_distribution"].items() if not np.isnan(v)}
            if rtd:
                coherences, rt_dist = zip(*sorted(rtd.items()))
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
        except Exception:
            pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    from omegaconf import OmegaConf

    session_info = {"protocol": "rdk", "experiment": "rdk"}
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
    sys.exit(app.exec_())
