import csv
import glob
import os
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from NeuRPi.data_model.subject import Subject as BaseSubject

# TODO: 2. Generate phase graphs
# TODO: 4. Add bias calculation


class Subject(BaseSubject):
    """

    /root
    |--- info - Subjects Biographical information
    |--- history
    |--- data
    |    |--- protocol
    |         |--- experiment
    |             |--- summary
    |                |--- weight
    |                |--- performance
    |                |--- parameters
    |                |--- session_#1
    |                |       |--- trial_data
    |                |       |--- continuous_data
    |                |--- session_#2
    |                |--- ...
    |
    """

    def __init__(
        self,
        session_info=None,
        session_config=None,
    ) -> None:
        super().__init__(session_info.subject_name)
        self.session_config = session_config

        # Initializing subject specific configuration
        self.rig_id = session_info.rig_id
        self.start_weight = session_info.subject_weight
        self.end_weight = None
        self.baseline_weight = self.start_weight if self.history.baseline_weight.empty else self.history.baseline_weight.iloc[-1]
        self.prct_weight = round((self.start_weight / self.baseline_weight * 100), 2)
        self.protocol = session_info.protocol
        self.experiment = session_info.experiment
        self.experiment_dir = Path(self.data_dir, self.protocol, self.experiment)
        self.session = self.get_session_number()
        self.rolling_perf = {}

        # Initializing all directory and files. Currently, hardcoded file names. In future, will take input form external config to determine files
        self.files = {
            # across session
            "summary": str(Path(self.experiment_dir, self.name + "_summary.csv")),
            "rolling_perf": str(Path(self.experiment_dir, "rolling_performance.pkl")),
            # within session
            "trial": str(Path(self.experiment_dir, self.session, self.name + "_trial.csv")),
            "event": str(Path(self.experiment_dir, self.session, self.name + "_event.csv")),
            "lick": str(Path(self.experiment_dir, self.session, self.name + "_lick.csv")),
            "rolling_perf_before": str(Path(self.experiment_dir, self.session, "rolling_perf_before.pkl")),
            "rolling_perf_after": str(Path(self.experiment_dir, self.session, "rolling_perf_after.pkl")),
        }

        self.plots = {
            "accuracy": str(Path(self.experiment_dir, self.session, "accuracy.png")),
            "psychometric": str(Path(self.experiment_dir, self.session, "psychometric.png")),
            "trials_distribution": str(Path(self.experiment_dir, self.session, "trials_distribution.png")),
            "rt_distribution": str(Path(self.experiment_dir, self.session, "rt_distribution.png")),
            # summary plots
            "accu_vs_training": str(Path(self.experiment_dir, "accu_vs_training.png")),
            "accu_vs_weight": str(Path(self.experiment_dir, "accu_vs_weight.png")),
            "attmpt_vs_training": str(Path(self.experiment_dir, "attmpt_vs_training.png")),
            "attmpt_vs_weight": str(Path(self.experiment_dir, "attmpt_vs_weight.png")),
        }

        self.prepare_rolling_perf()

    def get_session_number(self):
        """
        get the last session number and return the next session number in directory where directory is named as day_session.

        """
        sessions = list(self.experiment_dir.glob("*_*/"))
        day, session_idx = 1, 1
        if sessions:
            # finding highest session and when it was created
            for session in sessions:
                if session.is_dir():
                    if day < int(session.name.split("_")[-2]):
                        day = int(session.name.split("_")[-2])
                        session_idx = int(session.name.split("_")[-1])
                    if int(session.name.split("_")[-2]) == day:
                        session_idx = max(session_idx, int(session.name.split("_")[-1]))
            creation_time = Path(self.experiment_dir, f"{day}_{session_idx}").stat().st_ctime

            if time.time() - creation_time > 12 * 60 * 60:  # if created more than 12 hrs ago, increase day
                day += 1
                session_idx = 1
            else:
                session_idx += 1

        return str(day) + "_" + str(session_idx)

    def prepare_rolling_perf(self):
        """
        this method creates a rolling_perforamance database to track subject's perforamance between session for each experiment under each protocol.
        A rolling performance is a dictionary with following keys:
        # full history:
            rolling_window (int): window size for tracking history of each coherence
            history (dict): accuracy history for each coherence over rolling_window
            history_indices (dict): index of each coherence in history
            accuracy (dict): mean accuracy for each coherence
            current_coherence_level (int): current coherence level
            trials_in_current_level (int): number of trials in current coherence level
        # previous session
            total_attempts (int): total number of trials in previous session
            total_reward (fload): total reward in previous session
            reward_volume (float): reward volume for current session


        """
        # If first session, creating
        if self.session == "1_1":
            full_coherences = self.session_config.TASK["stimulus"]["signed_coherences"]["value"]
            current_coherence_level = self.session_config.TASK["rolling_performance"]["current_coherence_level"]
            reward_volume = self.session_config.TASK["rolling_performance"]["reward_volume"]
            rolling_window = self.session_config.TASK["rolling_performance"]["rolling_window"]

            self.rolling_perf = {
                "rolling_window": rolling_window,
                "history": {str(coh): list(np.zeros(rolling_window).astype(int)) for coh in full_coherences},
                "history_indices": {str(coh): 0 for coh in full_coherences},
                "accuracy": {str(coh): 0 for coh in full_coherences},
                "current_coherence_level": current_coherence_level,
                "trials_in_current_level": 0,
                "total_attempts": 0,
                "total_reward": 0,
                "reward_volume": reward_volume,
            }

        else:
            try:
                with open(self.files["rolling_perf"], "rb") as reader:
                    self.rolling_perf = pickle.load(reader)
            except Exception as e:
                print(f"Error importing rolling performance file {e}")

    def initiate_config(self):
        """ "
        Initiating subject and session specific parameters. This dictionary will also be shared with terminal at the end of each trial to update GUI

        Arguments:
            full_coherences (list): array of all coherences included in the task
        """
        subject_config = {
            # Subject and task identification
            "name": self.name,
            "baseline_weight": self.baseline_weight,
            "start_weight": self.start_weight,
            "prct_weight": self.prct_weight,
            "protocol": self.protocol,
            "experiment": self.experiment,
            "session": self.session,
            "session_uuid": self.session_uuid,
            "rolling_perf": self.rolling_perf,
        }
        return subject_config

    def save_files(self, file_dict):
        """
        Save files in a pickle file
        """
        # look if session path directory exists, if not create it
        session_path = Path(self.experiment_dir, self.session)
        session_path.mkdir(parents=True, exist_ok=True)

        try:
            for file_name, file_content in file_dict.items():
                if file_name in ["lick", "event", "trial"]:
                    with open(self.files[file_name], "wb") as file:
                        file.write(file_content)
                elif file_name in ["summary"]:
                    with open(self.files[file_name], "a", newline="") as file:
                        writer = csv.DictWriter(file, fieldnames=file_content.keys())
                        if file.tell() == 0:
                            writer.writeheader()
                        writer.writerow(file_content)
                elif file_name in [
                    "rolling_perf",
                    "rolling_perf_before",
                    "rolling_perf_after",
                ]:
                    file_content = pickle.loads(file_content)
                    with open(self.files[file_name], "wb") as file:
                        pickle.dump(file_content, file)

            self.create_summary_plots()

        except Exception as e:
            print(e)
            pass

    def create_summary_plots(self):
        """
        Create summary plots for the session
        """
        try:
            experiment_summary = pd.read_csv(self.files["summary"], index_col=0)
            # accuracy vs training day
            plt.plot(experiment_summary["session"].str.split("_").str[0], experiment_summary["total_accuracy"], "o", label="Accuracy vs Training Day")
            plt.xlabel("Training Day")
            plt.ylabel("Accuracy")
            plt.title("Accuracy vs Training Day")
            plt.legend()
            plt.ylim([50, 100])
            plt.savefig(self.plots["accu_vs_training"])
            plt.close()
            # accuracy vs weigth
            plt.plot(experiment_summary["start_weight_prct"], experiment_summary["total_accuracy"], "o", label="Accuracy vs Start Weight")
            plt.xlabel("Start Weight")
            plt.ylabel("Accuracy")
            plt.title("Accuracy vs Start Weight")
            plt.legend()
            plt.ylim([50, 100])
            plt.savefig(self.plots["accu_vs_weight"])
            plt.close()
            # attempts vs training
            plt.plot(experiment_summary["session"].str.split("_").str[0], experiment_summary["total_attempt"], "o", label="Attempts vs Start Weight")
            plt.xlabel("Start Weight")
            plt.ylabel("Attempts")
            plt.title("Attempts vs Start Weight")
            plt.legend()
            plt.ylim([0, 1000])
            plt.savefig(self.plots["attmpt_vs_weight"])
            plt.close()
            # attempts vs weigth
            plt.plot(experiment_summary["start_weight_prct"], experiment_summary["total_attempt"], "o", label="Attempts vs Start Weight")
            plt.xlabel("Start Weight")
            plt.ylabel("Attempts")
            plt.title("Attempts vs Start Weight")
            plt.legend()
            plt.ylim([0, 1000])
            plt.savefig(self.plots["attmpt_vs_weight"])
            plt.close()
        except:
            print("Could not save summary plots")

    def save_history(self, start_weight=None, end_weight=None, baseline_weight=None):
        hist_dict = {
            "baseline_weight": baseline_weight if baseline_weight else self.baseline_weight,
            "start_weight": start_weight if start_weight else self.start_weight,
            "end_weight": end_weight if end_weight else self.end_weight,
            "protocol": self.protocol,
            "experiment": self.experiment,
            "session": self.session,
            "rig_id": self.rig_id,
        }
        self.update_history(hist_dict)


if __name__ == "__main__":
    import sys

    from omegaconf import OmegaConf

    session_info = {
        "subject_name": "test",
        "subject_weight": 0,
        "protocol": 0,
        "experiment": 0,
    }

    # convert session_info dict to omegaconf
    session_info = OmegaConf.create(session_info)

    a = Subject(session_info=session_info)
    b = 0