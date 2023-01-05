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
import tables

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
        task_module: str,
        task_phase: str,
        dir: Optional[Path] = None,
    ):

        self.name = name

        if dir:
            self.dir = Path(dir)
        else:
            self.dir = Path(prefs.get("DATADIR"), self.name, task_module, task_phase)

        self.logger = init_logger(self)
        # self.init_files()

        self.session = self.get_session()
        self._session_uuid = None

        # if path doesn't exist, create it
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

        # Is the subject currently running?
        # Used to keep the subject object alive, otherwise close files whenever we don't need it
        self.running = False

        # Using threading queut to dump data into a open data files
        self.data_queue = None
        self._thread = None
        self._lock = threading.Lock()

    ############################
    # # Basic preparation functions!
    # def init_files(self):
    #     """
    #     Initializing all directory and files. Currently, hardcoded file names. In future, will take input form external config to determine files

    #     """

    #     # files
    #     self.summary = str(Path(self.dir, self.name + "_summary.csv"))
    #     self.trial = str(Path(self.dir, self.session, self.name + "_trial.csv"))
    #     self.event = str(Path(self.dir, self.session, self.name + "_event.csv"))
    #     self.lick = str(Path(self.dir, self.session, self.name + "_lick.csv"))

    def get_session(self) -> str:
        """
        Method for automated session naming.

        Return:
            str: Session is named as '{day}_{session_no}'

        """
        # Checking for last day session number
        # Finding all folders with current session
        sub_dirs = glob.glob(str(self.dir) + "/*/")
        day = 0
        # Finding max number of current sessions recorded
        for file in sub_dirs:
            num1, num2 = [
                int(i) for i in re.search("(\d*)_" + "(\d*)", file).group(1, 2)
            ]
            day = num1 if num1 > day else day

        # Checking for max number of sessions in a day
        session_no = 0
        for file in sub_dirs:
            num1, num2 = [
                int(i) for i in re.search("(\d*)_" + "(\d*)", file).group(1, 2)
            ]
            session_no = num2 if num2 > session_no else session_no

        # Creating folder
        # If first session under this task_module and task_phase
        if day == 0:
            session = str(day + 1) + "_1"  # Increasing Day
        else:
            # checking if multiple entry on same day

            file_time = os.stat(
                Path(self.dir, str(day) + "_" + str(session_no))
            ).st_ctime
            if (
                time.time() - file_time
            ) / 3600 < 12:  # Was file created today (less than 12 hours ago)?
                session = str(day) + "_" + str(session_no + 1)  # Increasing Version
            else:
                session = str(day + 1) + "_1"  # Increasing Day
        return session

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

    # def prepare_run(self):
    #     """
    #     Prepare the Subject object to receive data while running the task.

    #     spawns :attr:`~.Subject.data_queue` and calls :meth:`~.Subject._data_thread`.

    #     Returns:
    #         Dict: the parameters for the current session, with subject id, current trial, and session number included.
    #     """

    #     task_params = {}
    #     self._session_uuid = None

    #     # spawn thread to accept data
    #     self.data_queue = queue.Queue()
    #     self._thread = threading.Thread(
    #         target=self._data_thread,
    #         args=(self.data_queue, trial_table_path, continuous_group_path),
    #     )
    #     self._thread.start()
    #     self.running = True

    # def stop_run(self):
    #     pass

    # #######################
    # # Data acquisition methods

    # def _data_thread(self, que: queue.Queue, trial_file: str, continuous_file: str):
    #     """
    #     Thread to keep file open and receive data while task is running.

    #     Receives data through ~.Subject.queue as dictionary.

    #     Args:
    #         queue (:class:`queue.Queue`): passed by :meth:`~.Subject.prepare_run` and used by other
    #             objects to pass data to be stored.
    #     """
    #     # start getting data
    #     # stop when 'END' gets put in the queue
    #     for data in iter(queue.get, "END"):
    #         # wrap everything in try because this thread shouldn't carash
    #         try:
    #             if "continuous" in data.keys():
    #                 # cont_tables, cont_rows = self._save_continuous_data(
    #                 #     h5f, data, continuous_group_path, cont_tables, cont_rows
    #                 # )
    #                 # # continue, the rest is for handling trial data
    #                 continue

    #             # if we get trial data, try to sync it
    #             if "trial_num" in data.keys() and "trial_num" in trial_row:
    #                 trial_row = self._sync_trial_row(
    #                     data["trial_num"], trial_row, trial_table
    #                 )
    #                 del data["trial_num"]

    #             self._save_trial_data(data, trial_row, trial_table)

    #         except Exception as e:
    #             # we shouldn't throw any exception in this thread, just log it and move on
    #             self.logger.exception(f"exception in data thread: {e}")

    # def _save_continuous_data(
    #     self,
    #     h5f: tables.File,
    #     data: dict,
    #     continuous_group_path: str,
    #     cont_tables: typing.Dict[str, tables.table.Table],
    #     cont_rows: typing.Dict[str, Row],
    # ) -> typing.Tuple[typing.Dict[str, tables.table.Table], typing.Dict[str, Row]]:
    #     for k, v in data.items():

    #         # if we haven't made a table yet, do it
    #         if k not in cont_tables.keys():
    #             new_cont_table = self._make_continuous_table(
    #                 h5f, continuous_group_path, k, v
    #             )
    #             cont_tables[k] = new_cont_table
    #             cont_rows[k] = new_cont_table.row

    #         cont_rows[k][k] = v
    #         cont_rows[k]["timestamp"] = data.get(
    #             "timestamp", datetime.datetime.now().isoformat()
    #         )
    #         cont_rows[k].append()

    #     return cont_tables, cont_rows
