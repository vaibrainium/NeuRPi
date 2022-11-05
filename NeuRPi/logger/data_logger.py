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
        mode: str = "r+",
    ):

        self._lock = threading.Lock()

        if file:
            file = Path(file)
            if not name:
                name = file.stem

        else:
            if not name or not dir:
                raise FileNotFoundError("Need to pass a name and directory path")
            file = dir / (name + ".csv")

        self.name = name
        self.logger = init_logger(self)
        self.file = file

        if not self.file.exists():
            self.create_file()
            self.logger.warning(
                "Subject file {str(self.file)} does not exist! Creating new file"
            )

    def create_file(self):
        """
        Create csv file with provided name
        """
        with open(self.file, "x"):
            pass

    def read_file(self):
        pass

    def write_file(self, mode: str = "a"):
        """
        Write into file with one of the following mode. Default mode is append.

        Character	Mode	Description
        r:	Read (default)	Open a file for read only
        w:	Write	Open a file for write only (overwrite)
        a:	Append	Open a file for write only (append)
        r+:	Read+Write	open a file for both reading and writing
        x:	Create	Create a new file
        """
        pass

    # @contextmanager
    # def _csv(self, lock: bool = True):
    #     """
    #     Context manager for access to hdf5 file.
    #     Args:
    #         lock (bool): Lock the file while it is open, only use ``False`` for operations
    #             that are read-only: there should only ever be one write operation at a time.
    #     Examples:
    #         with self._h5f as h5f:
    #             # ... do hdf5 stuff
    #     Returns:
    #         function wrapped with contextmanager that will open the hdf file
    #     """

    #     if lock:
    #         with self._lock:
    #             try:
    #                 h5f = tables.open_file(str(self.file), mode="r+")
    #                 yield h5f
    #             finally:
    #                 h5f.flush()
    #                 h5f.close()

    #     else:
    #         try:
    #             try:
    #                 h5f = tables.open_file(str(self.file), mode="r")
    #             except ValueError as error_list:
    #                 if (
    #                     "already opened, but not in read-only mode"
    #                     in error_list.args[0]
    #                 ):
    #                     h5f = tables.open_file(str(self.file), mode="r+")
    #                 else:
    #                     raise error_list
    #             yield h5f
    #         finally:
    #             h5f.flush()
    #             h5f.close()


if __name__ == "__main__":
    whl_file = DataLogger(Path("data_check"))

    pass
