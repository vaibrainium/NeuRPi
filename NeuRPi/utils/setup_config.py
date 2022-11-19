import json
import logging
import multiprocessing as mp
import os
import subprocess
import sys
import types
import typing
import warnings
from collections import OrderedDict as odict
from ctypes import c_bool
from enum import Enum, auto
from pathlib import Path
from threading import Lock


class Scopes(Enum):
    """
    Enum that lists available scopes and groups for prefs

    Scope can be an agent type, common (for everyone), or specify some
    subgroup of prefs that should be presented together (like directories)

    COMMON = All Agents
    DIRECTORY = Prefs group for specifying directory structure
    TERMINAL = prefs for Terminal Agents
    Pilot = Prefs for Pilot agents
    LINEAGE = prefs for networking lineage (until networking becomes more elegant ;)
    AUDIO = Prefs for configuring the Jackd audio server


    """

    COMMON = auto()  #: All agents
    TERMINAL = auto()  #: Prefs specific to Terminal Agents
    PILOT = auto()  #: Prefs specific to Pilot Agents
    DIRECTORY = auto()  #: Directory structure
    LINEAGE = auto()  #: Prefs for coordinating network between pilots and children
    AUDIO = auto()  #: Audio prefs..


using_manager = False
if (
    getattr(mp.process.current_process(), "_inheriting", False)
    or os.getenv("AUTOPILOT_NO_PREFS_MANAGER")
    or __file__ == "<input>"
):
    # Check if it's safe to use multiprocessing manager, using the check in multiprocessing/spawn.py:_check_not_importing_main
    # see https://docs.python.org/2/library/multiprocessing.html#windows
    _PREF_MANAGER = None
    _PREFS = {}
    _INITIALIZED = False
    _LOCK = Lock()
else:

    try:
        _PREF_MANAGER = mp.Manager()  # type: typing.Optional[mp.managers.SyncManager]
        """
        The :class:`multiprocessing.Manager` that stores prefs during system operation and makes them available
        and consistent across processes.
        """
        using_manager = True

        _PREFS = _PREF_MANAGER.dict()  # type: mp.managers.SyncManager.dict
        """
        stores a dictionary of preferences that mirrors the global variables.
        """

        _INITIALIZED = mp.Value(c_bool, False)  # type: mp.Value
        """
        Boolean flag to indicate whether prefs have been initialzied from ``prefs.json``
        """

        _LOCK = mp.Lock()  # type: mp.Lock
        """
        :class:`multiprocessing.Lock` to control access to ``prefs.json``
        """

    except (EOFError, FileNotFoundError):
        # can't use mp.Manager in ipython and other interactive contexts
        # fallback to just regular old dict

        _PREF_MANAGER = None
        _PREFS = {}
        _INITIALIZED = False
        _LOCK = Lock()


class prefs:
    def __init__(self, dir=None) -> None:
        # load cofig file
        pass

    def get(self, key: typing.Union[str, None] = None):
        """
        Get config values from config.yaml
        """

    def set(self):
        pass
