import csv
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from NeuRPi.data_model.subject import Subject as BaseSubject


class Subject(BaseSubject):
    """
    Class for tracking subject parameters and data logging
    """

    def __init__(
        self, name=None, task_module=None, task_phase=None, config=None
    ) -> None:
        super().__init__(name=name, task_module=task_module, task_phase=task_phase)
        # Initializing subject specific configuration
        self.config = config
        self.rolling_perf = {}

        # Initializing all directory and files. Currently, hardcoded file names. In future, will take input form external config to determine files
        self.summary = str(Path(self.dir, self.name + "_summary.csv"))
        self.trial = str(Path(self.dir, self.session, self.name + "_trial.csv"))
        self.event = str(Path(self.dir, self.session, self.name + "_event.csv"))
        self.lick = str(Path(self.dir, self.session, self.name + "_lick.csv"))
        self.rolling_perf_pkl = str(Path(self.dir, "rolling_performance.pkl"))

    def prepare_run(self, full_coherences):
        "Creating file structure and essential folders"

        # If this is a new subject
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

        # If first session, creating
        if self.session == "1_1" or os.path.getsize(self.rolling_perf_pkl) <= 0:
            self.rolling_perf = {
                "window": 50,  # rolling window
                "trial_counter_after_4th": 0,  # trial counter for when lower coh (18%) are introduced
                "total_attempts": 0,
                "total_reward": 0,
                "reward_per_pulse": 3,
                "current_coh_level": 2,
                "index": list(np.zeros(len(full_coherences)).astype(int)),
                "accuracy": list(np.zeros(len(full_coherences))),
            }
            for index, coh in enumerate(full_coherences):
                self.rolling_perf["hist_" + str(coh)] = list(
                    np.zeros(self.rolling_perf["window"])
                )
                self.rolling_perf["accuracy"][index] = np.mean(
                    self.rolling_perf["hist_" + str(coh)]
                )

        else:
            with open(self.rolling_perf_pkl, "wb") as reader:
                self.rolling_perf = pickle.load(reader)

    def initiate_parameters(self, full_coherences):
        """ "
        Initiating subject and session specific parameters. This dictionary will also be shared with terminal at the end of each trial to update GUI

        Arguments:
            full_coherences (list): array of all coherences included in the task
        """
        subject_parameters = {
            "counters": {
                "attempt": 0,
                "valid": 0,
                "correct": 0,
                "incorrect": 0,
                "noresponse": 0,
            },
            # Trial parameters
            "total_reward": 0,
            "passive_bias_correction": True,
            "active_bias_correction": False,
            "bias_replace": 1,
            # Plotting traces
            "current_coh_level": self.rolling_perf["current_coh_level"],
            "running_accuracy": [],
            "psych_right": np.zeros(len(full_coherences)).tolist(),
            "psych_left": np.zeros(len(full_coherences)).tolist(),
            "psych": np.array(np.zeros(len(full_coherences)) + np.NaN).tolist(),
            "trial_distribution": np.zeros(len(full_coherences)).tolist(),
            "response_time_distribution": np.array(
                np.zeros(len(full_coherences)) * np.NaN
            ).tolist(),
            # Within session tracking
            "rolling_bias_window": self.config.TASK.bias.passive_correction.rolling_window,
            "rolling_bias_index": 0,
            "rolling_bias": np.zeros(
                self.config.TASK.bias.passive_correction.rolling_window
            ).tolist(),  # initiating at no bias
        }

        subject_parameters["reward_per_pulse"] = self.rolling_perf["reward_per_pulse"]
        if 1.5 < subject_parameters["reward_per_pulse"] < 3:
            # if received less than 700ul of reward on last session, increase reward by 0.1 ul.
            if self.rolling_perf["total_reward"] < 700:
                subject_parameters["reward_per_pulse"] += 0.1
                # if received less than 500ul of reward on last session, increase reward by another 0.1 ul.
                if self.rolling_perf["total_reward"] < 500:
                    subject_parameters["reward_per_pulse"] += 0.1
            # if performed more than 200 trials on previous session, decrease reward by 0.1 ul
            if self.rolling_perf["total_attempts"] > 200:
                subject_parameters["reward_per_pulse"] -= 0.1

        self.config.SUBJECT = subject_parameters
        return subject_parameters

    def save(self):
        """ "
        Save rolling performance in a  pickle file
        """
        try:
            reader = open(self.rolling_perf_pkl, "wb")
            pickle.dump(self.rolling_Perf, reader)
            reader.close()
        except:
            pass
