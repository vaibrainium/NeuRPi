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
        |    |--- task_module
        |         |--- task_phase
        |             |--- summary
        |                |--- weight
        |                |--- performance
        |                |--- parameters
        |             |--- session_#1
        |             |       |--- trial_data
        |             |       |--- continuous_data
        |             |--- session_#2
        |             |--- ...
        |

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

        if dir:
            self.dir = Path(dir, self.name)
        else:
            self.dir = Path(prefs.get("DATADIR"), self.name)

        self.logger = init_logger(self)

        self._session_uuid = None
        self._info = None
        self._history = None

    ############################ context manager for files ############################
    @contextmanager
    def open_file(self, file_name: str, mode: str = "r"):
        """
        Context manager for opening files in subject directory.

        Args:
            file_name (str): Name of file to open
            mode (str): File mode

        Returns:
            file: Open file
        """
        with open(Path(self.dir, file_name), mode) as f:
            yield f

    ######################## initial checks ########################
    def initialize_subject_info(self):
        # read from yaml files
        try:
            with self.open_file("info.yaml", "r") as f:
                self._info = yaml.safe_load(f)
            with self.open_file("history.csv", "r") as f:
                self._history = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.info("No subject info found")

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
        """
        Automatically generated UUID given to each session, regardless of the session number.
        Ensures each session is uniquely addressable in the case of ambiguous session numbers
        (eg. subject was manually promoted or demoted and session number was unable to be recovered,
        so there are multiple sessions with the same number)
        """
        if self._session_uuid is None:
            self._session_uuid = str(uuid.uuid4())
        return self._session_uuid

    ########################

    # def update_weight(self, weight):
    #     pass


if __name__ == "__main__":
    a = Subject("test")
    print(a.dir)
