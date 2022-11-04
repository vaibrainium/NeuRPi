import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union

import tables
from NeuRPi.data.logger import init_logger
from NeuRPi.data.models.biography import Biography
from NeuRPi.data.models.protocol import Protocol_Group
from NeuRPi.data.models.subject import (
    Hashes,
    History,
    ProtocolStatus,
    SubjectStructure,
    Weights,
)


class Subject:
    """
    Class for managing each subject's data in experiment.

    Creates a data file for subject with structure:

        /root
        |--- info - Subjects Biographical information
        |--- data
        |    |--- task_name
        |         |--- phase
        |           |--- history
        |                |--- weight
        |                |--- performance
        |                |--- parameters
        |           |--- session_#1
        |           |       |--- trial_data
        |           |       |--- continuous_data
        |           |--- session_#2
        |           |--- ...
        |

    Attributes:
        name (str): Subject ID
        file (str): Path to hdf5 file
        running (bool): Indicator if subject is currently running or not
        data_queue (:class: `queue.Queue`): Queue to dump data while running task
        did_graduate (:class: `threading.Event`): Event used to signal if the subject has graduated the current step
    """

    def __init__(
        self,
        name: str = None,
        dir: Optional[Path] = None,
        file: Optional[Path] = None,
        structure: Subject_Structure = Subject_Structure(),
    ):

        """
        Args:
            name (str): subject ID
            dir (str): path where the .h5 file is located, if `None`, `prefs.get('DATADIR')` is used
            file (str): load a subject from a filename. if `None`, ignored.
            structure (:class:`.Subject_Structure`): Structure to use with this subject.
        """
        pass

        self.structure = structure

        self._lock = threading.Lock()

        # --------------------------------------------------
        # Find subject .h5 file
        # --------------------------------------------------

        if file:
            file = Path(file)
            if not name:
                name = file.stem

        else:
            if not name or not dir:
                raise FileNotFoundError("Need to pass a name and or directory path")
            file = dir / (name + ".h5")

        self.name = name
        self.logger = init_logger(self)
        self.file = file

        if not self.file.exists():
            raise FileNotFoundError(f"Subject file {str(self.file)} does not exist!")

        # make sure we have the expected structure
        with self._h5f() as h5f:
            self.structure.make(h5f)

    @contextmanager
    def _h5f(self, lock: bool = True) -> tables.file.File:
        """
        Context manager for access to hdf5 file.
        Args:
            lock (bool): Lock the file while it is open, only use ``False`` for operations
                that are read-only: there should only ever be one write operation at a time.
        Examples:
            with self._h5f as h5f:
                # ... do hdf5 stuff
        Returns:
            function wrapped with contextmanager that will open the hdf file
        """

        if lock:
            with self._lock:
                try:
                    h5f = tables.open_file(str(self.file), mode="r+")
                    yield h5f
                finally:
                    h5f.flush()
                    h5f.close()

        else:
            try:
                try:
                    h5f = tables.open_file(str(self.file), mode="r")
                except ValueError as error_list:
                    if (
                        "already opened, but not in read-only mode"
                        in error_list.args[0]
                    ):
                        h5f = tables.open_file(str(self.file), mode="r+")
                    else:
                        raise error_list
                yield h5f
            finally:
                h5f.flush()
                h5f.close()
