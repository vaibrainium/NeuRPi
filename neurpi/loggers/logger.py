"""
Logging utilities for NeuRPi.

This module provides a flexible logging system that can create loggers for modules,
classes, or specific object instances while maintaining a consistent logging format
and hierarchy.
"""

from __future__ import annotations

import inspect
import logging
import re
import warnings
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock
from typing import Any, Literal

from rich.logging import RichHandler

from neurpi.prefs import prefs

# Type definitions
LOGLEVELS = Literal["DEBUG", "INFO", "WARNING", "ERROR"]

# Module-level variables
_INIT_LOCK = Lock()  # Lock to prevent concurrent logger creation
_LOGGERS = []  # List to track created loggers


def init_logger(
    instance: Any | None = None,
    module_name: str | None = None,
    class_name: str | None = None,
    object_name: str | None = None,
) -> logging.Logger:
    """
    Initialize a logger for a module, class, or object.

    This function creates a hierarchical logger based on the provided parameters.
    If an instance is provided, the module, class, and object names are automatically
    extracted from it. Otherwise, at least one of the name parameters must be provided.

    Args:
        instance: The object instance to create a logger for. If provided, other parameters are derived from it.
        module_name: The name of the module for the logger.
        class_name: The name of the class for the logger.
        object_name: The name of the specific object instance.

    Returns:
        A configured Logger instance.    Raises:
        ValueError: If neither instance nor any name parameter is provided.

    """
    # Extract logger name components from instance if provided
    if instance is not None:
        module_name = _extract_module_name(instance)
        class_name = instance.__class__.__name__
        object_name = _extract_object_name(instance)
    elif not any((module_name, class_name, object_name)):
        msg = "Need to either give an object to create a logger for, or one of module_name, class_name, or object_name"
        raise ValueError(msg)

    # Construct the logger name from available components
    logger_name_pieces = [
        v for v in (module_name, class_name, object_name) if v is not None
    ]
    logger_name = ".".join(logger_name_pieces)

    # Create or retrieve the logger
    with _INIT_LOCK:
        # Check if the parent logger needs to be created
        parent_logger_name = module_name
        if parent_logger_name and parent_logger_name not in _LOGGERS:
            _create_parent_logger(parent_logger_name)
            _LOGGERS.append(parent_logger_name)

        # Get or create the requested logger
        logger = logging.getLogger(logger_name)
        if logger_name not in _LOGGERS:
            logger.debug("Logger created: %s", logger_name)
            _LOGGERS.append(logger_name)

    return logger


def _extract_module_name(instance: Any) -> str:
    """Extract the module name from an instance, handling special cases like __main__."""
    module_name = instance.__module__

    if "__main__" in module_name:
        # Handle objects run from __main__
        mod_obj = inspect.getmodule(instance)
        try:
            if mod_obj and hasattr(mod_obj, "__file__") and mod_obj.__file__:
                mod_suffix = inspect.getmodulename(mod_obj.__file__)
                if (
                    mod_suffix
                    and hasattr(mod_obj, "__package__")
                    and mod_obj.__package__
                ):
                    module_name = f"{mod_obj.__package__}.{mod_suffix}"
        except AttributeError:
            # When running interactively or from a plugin, __main__ does not have __file__
            module_name = "__main__"

    # Remove the neurpi prefix for cleaner logger names
    return re.sub("^neurpi.", "", module_name)


def _extract_object_name(instance: Any) -> str | None:
    """Extract a suitable object name from an instance based on its attributes."""
    if hasattr(instance, "id"):
        return str(instance.id)

    if hasattr(instance, "name"):
        return str(instance.name)

    return None


def _create_parent_logger(logger_name: str) -> None:
    """Create a parent logger with file and console handlers."""
    parent_logger = logging.getLogger(logger_name)

    # Configure log level from preferences or environment
    log_level_str = prefs.get("LOGLEVEL") or "INFO"
    try:
        loglevel = getattr(logging, log_level_str)
    except (AttributeError, TypeError):
        loglevel = logging.INFO

    parent_logger.setLevel(loglevel)

    # Add file handler
    log_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s]: %(message)s",
    )

    log_dir = prefs.get("LOGDIR") or "logs/"
    base_filename = Path(log_dir + logger_name + ".log")

    file_handler = _create_file_handler(base_filename)
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(loglevel)
    parent_logger.addHandler(file_handler)

    # Add console handler
    parent_logger.addHandler(_create_rich_handler())

    # Disable propagation to avoid duplicate logging
    if isinstance(parent_logger.parent, logging.RootLogger):
        parent_logger.propagate = False

    parent_logger.debug("Parent logger created: %s", logger_name)


def _create_rich_handler() -> RichHandler:
    """Create a Rich console handler for colorful terminal output."""
    rich_handler = RichHandler(rich_tracebacks=True, markup=True)
    rich_formatter = logging.Formatter(
        r"[bold green]\[%(name)s][/bold green] %(message)s",
        datefmt="[%y-%m-%dT%H:%M:%S]",
    )
    rich_handler.setFormatter(rich_formatter)
    return rich_handler


def _create_file_handler(base_filename: Path) -> RotatingFileHandler:
    """
    Create a rotating file handler for the logger.

    Attempts to create the log directory if it doesn't exist and handles
    permission errors by trying to change file permissions.

    Args:
        base_filename: Path to the log file

    Returns:
        A configured RotatingFileHandler    Raises:
        PermissionError: If the log file cannot be created due to permission issues

    """
    # Create log directory if it doesn't exist
    if not base_filename.parent.exists():
        base_filename.parent.mkdir(parents=True, exist_ok=True)

    # Get log rotation settings from preferences
    log_size = int(prefs.get("LOGSIZE") or 5000000)  # 5MB default
    log_num = int(prefs.get("LOGNUM") or 4)  # 4 backup files default

    try:
        return RotatingFileHandler(
            str(base_filename),
            mode="a",
            maxBytes=log_size,
            backupCount=log_num,
        )
    except PermissionError as e:
        # Try to fix permission issues
        try:
            for mod_file in base_filename.parent.glob(f"{base_filename.stem}*"):
                mod_file_path = Path(mod_file)
                mod_file_path.chmod(0o664)  # More secure permissions: rw-rw-r--
                warnings.warn(
                    f"Couldn't access {mod_file}, changed permissions to 0o664",
                    stacklevel=2,
                )

            return RotatingFileHandler(
                str(base_filename),
                mode="a",
                maxBytes=log_size,
                backupCount=log_num,
            )
        except (OSError, PermissionError) as f:
            error_msg = (
                f"Couldn't open logfile {base_filename}, and couldn't fix permissions.\n"
                + "-" * 20
                + f"\nGot errors:\n{e}\n\n{f}\n"
                + "-" * 20
            )
            raise PermissionError(error_msg) from e
