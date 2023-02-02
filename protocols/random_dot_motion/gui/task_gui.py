import sys
import time

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets, uic

Ui_rig, rigclass = uic.loadUiType("protocols/random_dot_motion/gui/rdk_rig.ui")


class TaskGUI(rigclass):
    comm_to_taskgui = QtCore.pyqtSignal(dict)
    comm_from_taskgui = QtCore.pyqtSignal(dict)

    def __init__(self, rig_id=None):
        super().__init__()
        self.rig_id = rig_id
        self.rig = Ui_rig()
        self.rig.setupUi(self)
        self.rig.close_experiment.hide()

        self.session_timer = QtCore.QTimer()
        self.session_clock = 0
        self.trial_timer = QtCore.QTimer()
        self.trial_clock = 0
        self.paused = False
        self.stopped = False

        self.coherences = [-100, -72, -36, -18, -9, 0, 9, 18, 36, 72, 100]
        self.initialize_plots()
        self.start_session_clock(time.time())
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
        self.rig.pause_experiment.clicked.connect(lambda: self.pause_experiment())
        self.rig.stop_experiment.clicked.connect(lambda: self.stop_experiment())
        self.rig.close_experiment.clicked.connect(lambda: self.close_experiment())

    def reward(self, message: str):
        self.forward_signal(
            {
                "to": self.rig_id,
                "key": "EVENT",
                "value": {
                    "key": "REWARD",
                    "value": {"key": message, "value": self.rig.reward_volume.value()},
                },
            }
        )

    def pause_experiment(self):
        """
        If session is not paused, pause it and send the signal to terminal.
        If session is paused, resume it and send the corresponding singal to termianl.
        """
        if not self.paused:
            self.forward_signal(
                {"to": self.rig_id, "key": "EVENT", "value": {"key": "PAUSE"}}
            )
            self.rig.pause_experiment.setStyleSheet("background-color: green")
            self.rig.pause_experiment.setText("Resume")
            self.paused = True
        else:
            self.forward_signal(
                {"to": self.rig_id, "key": "EVENT", "value": {"key": "RESUME"}}
            )
            self.rig.pause_experiment.setStyleSheet("background-color: rgb(255,170,0)")
            self.rig.pause_experiment.setText("Pause")
            self.paused = False

    def stop_experiment(self):
        self.forward_signal({"to": self.rig_id, "key": "STOP", "value": None})
        self.rig.close_experiment.show()

    def close_experiment(self):
        # Task has ended but waiting to trial to end to close session
        self.stopped = True

    # Outgoing communication
    def forward_signal(self, message):
        message["rig_id"] = self.rig_id
        self.comm_from_taskgui.emit(message)

    # Incoming communication
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

    def start_session_clock(self, session_start_time):
        self.session_timer.timeout.connect(
            lambda: self.update_session_clock(session_start_time)
        )
        self.session_timer.start(1000)

    def stop_session_clock(self):
        self.session_timer.stop()

    def update_session_clock(self, session_start_time):
        self.session_clock = time.time() - session_start_time
        self.rig.session_timer.display(int(self.session_clock))

    def start_trial_clock(self, trial_start_time=time.time()):
        self.session_timer.timeout.connect(
            lambda: self.update_trial_clock(trial_start_time)
        )
        self.trial_timer.start(10)

    def stop_trial_clock(self):
        self.trial_timer.stop()

    def update_trial_timer(self, trial_start_time):
        self.trial_clock = time.time() - trial_start_time
        self.rig.session_timer.display(int(self.session_clock))

    def update_gui(self, value):
        if "trial_counters" in value.keys():
            self.update_trials(value["trial_counters"])

        if "stimulus_pars" in value.keys():
            self.update_stimulus(value["stimulus_pars"])

        if "plots" in value.keys():
            self.update_plots(value["plots"])

        if "total_reward" in value.keys():
            self.rig.total_reward.setText(str(value["total_reward"]))

        # Close session and Task GUI
        if "TRIAL_END" in value.keys() and self.stopped:
            self.forward_signal({"to": "main_gui", "key": "KILL", "value": None})
            self.session_timer = None

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
    sys.exit(app.exec_())
