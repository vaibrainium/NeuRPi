import logging
import typing
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

LOGLEVELS = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


def init_logger(
    instance=None, module_name=None, class_name=None, object_name=None
) -> logging.Logger:
    """
    Initialize a logger
    Loggers are created such that...
    * There is one logger per module (eg. all gpio objects will log to hardware.gpio)
    * If the passed object has a ``name`` attribute, that name will be prefixed to its log messages in the file
    * The loglevel for the file handler and the stdout is determined by ``prefs.get('LOGLEVEL')``, and if none is provided ``WARNING`` is used by default
    * logs are rotated according to ``prefs.get('LOGSIZE')`` (in bytes) and ``prefs.get('LOGNUM')`` (number of backups of ``prefs.get('LOGSIZE')`` to cycle through)
    Logs are stored in ``prefs.get('LOGDIR')``, and are formatted like::
        "%(asctime)s - %(name)s - %(levelname)s : %(message)s"
    Loggers can be initialized either by passing an object to the first ``instance`` argument, or
    by specifying any of ``module_name`` , ``class_name`` , or ``object_name`` (at least one must be specified)
    which are combined with periods like ``module.class_name.object_name``
    Args:
        instance: The object that we are creating a logger for! if None, at least one of ``module, class_name, or object_name`` must be passed
        module_name (None, str): If no ``instance`` passed, the module name to create a logger for
        class_name (None, str): If no ``instance`` passed, the class name to create a logger for
        object_name (None, str): If no ``instance`` passed, the object name/id to create a logger for
    Returns:
        :class:`logging.logger`
    """

    logger = None

    # TODO
    # Create logging file if doesn't exist

    return logger
