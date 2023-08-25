import csv
import glob
import os
import queue
import re
import threading
import time
import typing
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union

import pandas as pd
import yaml

from NeuRPi.loggers.logger import init_logger
from NeuRPi.prefs import prefs


class Subject:
    """
    Class for managing each subject's data in experiment.

    Creates and stores trial data for subject with structure:

        /root
        |--- info - Subjects Biographical information
        |--- history
        |--- data
        |    |--- protocol
        |         |--- experiment
        |             |---

    Attributes:
        name (str): Subject ID
        dir (str): Path to data file
        running (bool): Indicator if subject is currently running or not
    """

    def __init__(
        self,
        name: str,
        dir: Optional[Path] = None,
    ):
        self.name = name
        self._info = None
        self._history = None

        self.session = None
        self._session_uuid = str(uuid.uuid4())  # generate uniquely addressable uuid

        if dir:
            self.dir = Path(dir, self.name)
        else:
            self.dir = Path(prefs.get("DATADIR"), self.name)
        self.data_dir = Path(self.dir, "data")

        try:
            self.existing_subject = self.dir.exists()
            self.import_subject_biography()
        except FileNotFoundError:
            raise FileNotFoundError("Subject or root files not found")

    ############################ context manager for files ############################
    @contextmanager
    def file_context(self, file_name: str, mode: str = "r"):
        """
        Context manager for opening files in subject directory.

        Args:
            file_name (str): Name of file to open
            mode (str): File mode

        Returns:
            file: Open file
        """
        with open(Path(self.dir, file_name), mode) as file:
            yield file

    def import_subject_biography(self):
        # read from yaml files
        try:
            with self.file_context("info.yaml", "r") as file:
                self._info = yaml.safe_load(file)
            with self.file_context("history.csv", "r") as file:
                self._history = pd.read_csv(file)
        except FileNotFoundError:
            print("No subject info found")

    ############################ subject properties ############################
    @property
    def info(self):
        return self._info

    @property
    def history(self):
        return self._history

    ########################## subject properties ##########################
    @property
    def session_uuid(self) -> str:
        return self._session_uuid

    ########################

    def update_history(self, hist_dict: dict) -> None:
        """
        Updates subject history file with new session information.

        Args:
            hist_dict (dict): Dictionary containing session information.
                must contain keys: baseling_weight, start_weight, end_weight, protocol, experiment, session
        """
        try:
            hist_dict["date"] = hist_dict.get(
                "date", time.strftime("%Y-%m-%d %H:%M:%S")
            )
            hist_dict["session_uuid"] = hist_dict.get("session_uuid", self.session_uuid)

            new_row = pd.DataFrame([hist_dict]).reindex(columns=self.history.columns)
            if self.history.columns.equals(new_row.columns):
                self._history = pd.concat([a.history, new_row], ignore_index=True)
                with open(Path(self.dir, "history.csv"), "w", newline="") as file:
                    self._history.to_csv(file, index=False, lineterminator=None)
            else:
                raise ValueError(
                    "History dict does not contain all required keys from history file"
                )
        except AttributeError:
            raise AttributeError("Subject history could not be updated")


if __name__ == "__main__":
    name = "tes0t"
    a = Subject(name)
    if not a.existing_subject:
        a.create_subject({"name": name})

    new_line = {
        "baseling_weight": 0,
        "start_weight": 0,
        "end_weight": 0,
        "protocol": 0,
        "experiment": 0,
        "session": 0,
    }

    a.update_history(new_line)
    print(a.dir)
