import csv
import os
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from NeuRPi.data_model.subject import Subject as BaseSubject

#TODO: 1. Add baseline weights
#TODO: 2. Generate phase graphs
#TODO: 3. Add comments and save them
#TODO: 4. Add bias calculation

class Subject(BaseSubject):
    """
    Class for tracking subject parameters and data logging
    """

    def __init__(
        self, name=None, weight=None, task_module=None, task_phase=None, session_config=None
    ) -> None:
        super().__init__(name=name, task_module=task_module, task_phase=task_phase)
        # Initializing subject specific configuration
        self.start_weight = weight
        self.task_module = task_module
        self.task_phase = task_phase
        self.session_config = session_config
        self.rolling_perf = {}

        # Initializing all directory and files. Currently, hardcoded file names. In future, will take input form external config to determine files
        self.files = {
            # across session
            "summary": str(Path(self.dir, self.name + "_summary.csv")),
            "rolling_perf": str(Path(self.dir, "rolling_performance.pkl")),
            "accu_vs_training": str(Path(self.dir, "accu_vs_training.csv")),
            "attmpt_vs_training": str(Path(self.dir, "attmpt_vs_training.csv")),
            "attmpt_vs_weight": str(Path(self.dir, "attmpt_vs_weight.csv")),
            # within session
            "trial": str(Path(self.dir, self.session, self.name + "_trial.csv")),
            "event": str(Path(self.dir, self.session, self.name + "_event.csv")),
            "lick": str(Path(self.dir, self.session, self.name + "_lick.csv")),
            "rolling_perf_before": str(
                Path(self.dir, self.session, "rolling_perf_before.pkl")
            ),
            "rolling_perf_after": str(
                Path(self.dir, self.session, "rolling_perf_after.pkl")
            ),
        }

        self.plots = {
            "accuracy": str(Path(self.dir, self.session, "accuracy.png")),
            "psychometric": str(Path(self.dir, self.session, "psychometric.png")),
            "trials_distribution": str(Path(self.dir, self.session, "trials_distribution.png")),
            "rt_distribution": str(Path(self.dir, self.session, "rt_distribution.png")),
        }

        self.prepare_run()

    def get_full_coherences(self):
        """
        Generates full direction-wise coherence array from input coherences list.
        Returns:
            full_coherences (list): List of all direction-wise coherences with adjustment for zero coherence (remove duplicates).
            coh_to_xrange (dict): Mapping dictionary from coherence level to corresponding x values for plotting of psychometric function
        """
        coherences = np.array(
            self.session_config.TASK["stimulus"]["coherences"]["value"]
        )
        full_coherences = sorted(np.concatenate([coherences, -coherences]))
        if (
            0 in coherences
        ):  # If current full coherence contains zero, then remove one copy to avoid 2x 0 coh trials
            full_coherences.remove(0)
        return full_coherences

    def prepare_run(self):
        "Creating file structure and essential folders"

        full_coherences = (
            self.get_full_coherences()
        )  # self.session_config.TASK["stimulus"]["coherences"]["value"]

        # If first session, creating
        if self.session == "1_1" or os.path.getsize(self.files["rolling_perf"]) <= 0:
            self.rolling_perf = {
                "window": 50,  # rolling window
                "trial_counter_after_4th": 0,  # trial counter for when lower coh (18%) are introduced
                "total_attempts": 0,
                "total_reward": 0,
                "reward_volume": 3,
                "current_coherence_level": 2,
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
            # TODO: Add try error otherwise program is crashing due to system import
            try:
                with open(self.files["rolling_perf"], "rb") as reader:
                    self.rolling_perf = pickle.load(reader)
            except Exception as e:
                print(f"Error importing rolling performance file {e}")

    def initiate_config(self, full_coherences=None):
        """ "
        Initiating subject and session specific parameters. This dictionary will also be shared with terminal at the end of each trial to update GUI

        Arguments:
            full_coherences (list): array of all coherences included in the task
        """
        # If coherences not provided, using default values
        if full_coherences is None:
            full_coherences = (
                self.get_full_coherences()
            )  # self.session_config.TASK["stimulus"]["coherences"]["value"]

        subject_config = {
            # Subject and task identification
            "name": self.name,
            "weight": self.start_weight,
            "task_module": self.task_module,
            "task_phase": self.task_phase,
            "session": self.session,
            "session_uuid": self.session_uuid,
            # Counters
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
            "current_coherence_level": self.rolling_perf["current_coherence_level"],
            "running_accuracy": [[0, 0.5]],
            "psych_right": np.zeros(len(full_coherences)).tolist(),
            "psych_left": np.zeros(len(full_coherences)).tolist(),
            "psych": np.array(np.zeros(len(full_coherences)) + np.NaN).tolist(),
            "trial_distribution": np.zeros(len(full_coherences)).tolist(),
            "response_time_distribution": np.array(
                np.zeros(len(full_coherences)) * np.NaN
            ).tolist(),
            # Within session tracking
            "rolling_bias_window": self.session_config.TASK["bias"][
                "passive_correction"
            ]["rolling_window"],
            "rolling_bias_index": 0,
            "rolling_bias": np.zeros(
                self.session_config.TASK["bias"]["passive_correction"]["rolling_window"]
            ).tolist(),  # initiating at no bias
            # Between session tracking
            "rolling_perf": self.rolling_perf,
        }

        subject_config["reward_volume"] = self.rolling_perf["reward_volume"]
        if 1.5 < subject_config["reward_volume"] < 3:
            # if received less than 700ul of reward on last session, increase reward by 0.1 ul.
            if self.rolling_perf["total_reward"] < 700:
                subject_config["reward_volume"] += 0.1
                # if received less than 500ul of reward on last session, increase reward by another 0.1 ul.
                if self.rolling_perf["total_reward"] < 500:
                    subject_config["reward_volume"] += 0.1
            # if performed more than 200 trials on previous session, decrease reward by 0.1 ul
            if self.rolling_perf["total_attempts"] > 200:
                subject_config["reward_volume"] -= 0.1
            # limiting reward volume between 1.5 and 3
            subject_config["reward_volume"] = np.maximum(
                subject_config["reward_volume"], 1.5
            )
            subject_config["reward_volume"] = np.minimum(
                subject_config["reward_volume"], 3
            )
            subject_config["reward_volume"] = float(subject_config["reward_volume"])

        return subject_config

    def save_files(self, file_dict):
        """
        Save files in a pickle file
        """
        # look if session path directory exists, if not create it
        session_path = Path(self.dir, self.session)
        session_path.mkdir(parents=True, exist_ok=True)


        try:
            for file_name, file_content in file_dict.items():
                if file_name in ["lick", "event", "trial"]:
                    with open(self.files[file_name], "wb") as file:
                        file.write(file_content)
                elif file_name in ["summary", "accu_vs_training", "attmpt_vs_training", "attmpt_vs_weight"]:
                    with open(self.files[file_name], "a", newline="") as file:
                        writer = csv.DictWriter(file, fieldnames=file_content.keys())
                        if file.tell() == 0:
                            writer.writeheader()
                        writer.writerow(file_content)
                elif file_name in ["rolling_perf", "rolling_perf_before", "rolling_perf_after"]:
                    file_content = pickle.loads(file_content)
                    with open(self.files[file_name], "wb") as file:
                        pickle.dump(file_content, file)

        except Exception as e:
            print(e)
            pass

    # def save(self):
    #     """
    #     Save rolling performance in a  pickle file
    #     """
    #     try:
    #         reader = open(self.files["rolling_perf"], "wb")
    #         pickle.dump(self.rolling_perf, reader)
    #         reader.close()
    #     except Exception as e:
    #         print(e)
    #         pass
