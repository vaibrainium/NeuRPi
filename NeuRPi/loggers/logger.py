import inspect
import logging
import os
import re
import typing
import warnings
from dataclasses import dataclass
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Literal

from rich.logging import RichHandler

from NeuRPi.prefs import prefs

LOGLEVELS = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

_INIT_LOCK = Lock()  # type: Lock
_LOGGERS = []  # type: list


def init_logger(instance=None, module_name=None, class_name=None, object_name=None) -> logging.Logger:

    # --------------------------------------------------
    # gather variables
    # --------------------------------------------------

    if instance is not None:
        # get name of module_name without prefixed autopilot
        # eg passed autopilot.hardware.gpio.Digital_In -> hardware.gpio
        # filtering leading 'autopilot' from string

        module_name = instance.__module__
        if "__main__" in module_name:
            # awkward workaround to get module name of __main__ run objects
            mod_obj = inspect.getmodule(instance)
            try:
                mod_suffix = inspect.getmodulename(inspect.getmodule(instance).__file__)
                module_name = ".".join([mod_obj.__package__, mod_suffix])
            except AttributeError:
                # when running interactively or from a plugin, __main__ does not have __file__
                module_name = "__main__"

        module_name = re.sub("^NeuRPi.", "", module_name)
        # module_name = "log." + module_name

        class_name = instance.__class__.__name__

        if hasattr(instance, "id"):
            object_name = str(instance.id)
        elif hasattr(instance, "name"):
            object_name = str(instance.name)
        else:
            object_name = None

        # --------------------------------------------------
        # check if logger needs to be made, or exists already
        # --------------------------------------------------
    elif not any((module_name, class_name, object_name)):
        raise ValueError("Need to either give an object to create a logger for, or one of module_name, class_name, or object_name")

    # get name of logger to get
    logger_name_pieces = [v for v in (module_name, class_name, object_name) if v is not None]
    logger_name = ".".join(logger_name_pieces)

    # trim __ from logger names, linux don't like to make things like that
    # re.sub(r"^\_\_")

    # --------------------------------------------------
    # if new logger must be made, make it, otherwise just return existing logger
    # --------------------------------------------------

    # use a lock to prevent loggers from being double-created, just to be extra careful
    with globals()["_INIT_LOCK"]:

        # check if something starting with module_name already exists in loggers
        MAKE_NEW = False
        if not any([test_logger == module_name for test_logger in globals()["_LOGGERS"]]):
            MAKE_NEW = True

        if MAKE_NEW:
            parent_logger = logging.getLogger(module_name)
            try:
                loglevel = getattr(logging, prefs.get("LOGLEVEL"))
            except:
                loglevel = "INFO"
            parent_logger.setLevel(loglevel)

            # make formatter that includes name
            log_formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s]: %(message)s")

            ## file handler
            # base filename is the module_name + '.log
            base_filename = Path(prefs.get("LOGDIR") + module_name + ".log")

            fh = _file_handler(base_filename)
            fh.setLevel(loglevel)
            fh.setFormatter(log_formatter)
            parent_logger.addHandler(fh)

            # rich logging handler for stdout
            parent_logger.addHandler(_rich_handler())

            # if our parent is the rootlogger, disable propagation to avoid printing to stdout
            if isinstance(parent_logger.parent, logging.RootLogger):
                parent_logger.propagate = False

            ## log creation
            globals()["_LOGGERS"].append(module_name)
            parent_logger.debug(f"parent, module-level logger created: {module_name}")

        logger = logging.getLogger(logger_name)
        if logger_name not in globals()["_LOGGERS"]:
            # logger.addHandler(_rich_handler())
            logger.debug(f"Logger created: {logger_name}")
            globals()["_LOGGERS"].append(logger_name)

    return logger


def _rich_handler() -> RichHandler:
    rich_handler = RichHandler(rich_tracebacks=True, markup=True)
    rich_formatter = logging.Formatter(
        "[bold green]\[%(name)s][/bold green] %(message)s",
        datefmt="[%y-%m-%dT%H:%M:%S]",
    )
    rich_handler.setFormatter(rich_formatter)
    return rich_handler


def _file_handler(base_filename: Path) -> RotatingFileHandler:
    # if directory doesn't exist, try to make it
    if not base_filename.parent.exists():
        base_filename.parent.mkdir(parents=True, exist_ok=True)

    try:
        fh = RotatingFileHandler(
            str(base_filename),
            mode="a",
            maxBytes=int(prefs.get("LOGSIZE")),
            backupCount=int(prefs.get("LOGNUM")),
        )
    except PermissionError as e:
        # catch permissions errors, try to chmod our way out of it
        try:
            for mod_file in Path(base_filename).parent.glob(f"{Path(base_filename).stem}"):
                os.chmod(mod_file, 0o777)
                warnings.warn(f"Couldnt access {mod_file}, changed permissions to 0o777")

            fh = RotatingFileHandler(
                base_filename,
                mode="a",
                maxBytes=int(prefs.get("LOGSIZE")),
                backupCount=int(prefs.get("LOGNUM")),
            )
        except Exception as f:
            raise PermissionError(f"Couldnt open logfile {base_filename}, and couldnt chmod our way out of it.\n" + "-" * 20 + f"\ngot errors:\n{e}\n\n{f}\n" + "-" * 20)
    return fh


# def _file_handler(base_filename: Path) -> RotatingFileHandler:
#     # if directory doesn't exist, try to make it
#     if not base_filename.parent.exists():
#         base_filename.parent.mkdir(parents=True, exist_ok=True)

#     fh = RotatingFileHandler(
#         str(base_filename), mode="a", maxBytes=int(20 * (2**20)), backupCount=int(4)
#     )
#     return fh
