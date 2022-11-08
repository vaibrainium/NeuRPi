import csv
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union

import pandas as pd

import NeuRPi
from NeuRPi.logger.logger import init_logger


class DataLogger:
    """
    Writes data into file if file already exists.
    If not, create new file and strore data
    """

    def __init__(
        self,
        name: str = None,
        dir: Optional[Path] = None,
        file: Optional[Path] = None,
    ):

        if file:
            file = Path(file)
            if not name:
                name = file.stem
        else:
            if not name or not dir:
                raise FileNotFoundError("Need to pass a name and directory path")
            file = dir / (name + ".csv")

        self._lock = threading.Lock()
        self.logger = init_logger(self)
        self.name = name
        self.file = file

    def create_file(self, headers: list):
        """
        Create csv file with provided name and headers
        """
        with open(self.file, "x") as csvfile:
            file_handle = csv.DictWriter(
                csvfile, fieldnames=headers, lineterminator="\n"
            )
            file_handle.writeheader()

    def read_file(self):
        """
        Reads file if exists and returns content as a pandas dataframe
        """
        if not self.file.exists():
            self.logger.warning(
                "Subject file {str(self.file)} does not exist! Please create new file"
            )
        dataframe = pd.DataFrame()
        try:
            dataframe = pd.read_csv(self.file)
        except:
            self.logger.warning("Could not read subject file {str(self.file)}")

        return dataframe

    def write_file(self, data, mode: str = "a"):
        """
        Write into file with one of the following mode. Default mode is append.

        Character	Mode	Description
        r:	Read (default)	Open a file for read only
        w:	Write	Open a file for write only (overwrite)
        a:	Append	Open a file for write only (append)
        r+:	Read+Write	open a file for both reading and writing
        x:	Create	Create a new file
        """

        if not self.file.exists():
            self.logger.warning(
                "Subject file {str(self.file)} does not exist! Please create new file"
            )

        with self._lock:
            try:
                # writing to csv file
                with open(self.file, mode) as csvfile:
                    if isinstance(data, list):
                        csvwriter = csv.writer(csvfile)
                    elif isinstance(data, dict):
                        csvwriter = csv.DictWriter(
                            csvfile, fieldnames=list(data.keys())
                        )

                    # writing the data rows
                    csvwriter.writerows(data)

            except BaseException:
                self.logger.error("Could not write to Subject file {str(self.file)}")
            finally:
                csvfile.flush()
                csvfile.close()
