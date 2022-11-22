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

import hydra


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


_basedir = Path(os.path.join(os.path.expanduser("~"), "autopilot"))


class Common_Prefs(Autopilot_Pref):
    """
    Prefs common to all autopilot agents
    """


class Directory_Prefs(Autopilot_Pref):
    """
    Directories and paths that define the contents of the user directory.

    In general, all paths should be beneath the `USER_DIR`
    """

    class Config:
        env_prefix = "AUTOPILOT_DIRECTORY_"


class Agent_Prefs(Autopilot_Pref):
    """
    Abstract prefs class for prefs that are specific to agents
    """


class Terminal_Prefs(Agent_Prefs):
    """
    Prefs for the :class:`~autopilot.agents.terminal.Terminal`
    """

    class Config:
        env_prefix = "AUTOPILOT_TERMINAL_"


class Pilot_Prefs(Agent_Prefs):
    """
    Prefs for the :class:`~autopilot.agents.pilot.Pilot`
    """

    class Config:
        env_prefix = "AUTOPILOT_PILOT_"


class Audio_Prefs(Autopilot_Pref):
    """
    Prefs to configure the audio server
    """


class Hardware_Pref(Autopilot_Pref):
    """
    Abstract class for hardware objects,
    """


_DEFAULTS = odict(
    {
        "NAME": {"type": "str", "text": "Agent Name:", "scope": Scopes.COMMON},
        "PUSHPORT": {
            "type": "int",
            "text": "Push Port - Router port used by the Terminal or upstream agent:",
            "default": "5560",
            "scope": Scopes.COMMON,
        },
        "MSGPORT": {
            "type": "int",
            "text": "Message Port - Router port used by this agent to receive messages:",
            "default": "5565",
            "scope": Scopes.COMMON,
        },
        "TERMINALIP": {
            "type": "str",
            "text": "Terminal IP:",
            "default": "192.168.0.100",
            "scope": Scopes.COMMON,
        },
        "LOGLEVEL": {
            "type": "choice",
            "text": "Log Level:",
            "choices": ("DEBUG", "INFO", "WARNING", "ERROR"),
            "default": "WARNING",
            "scope": Scopes.COMMON,
        },
        "LOGSIZE": {
            "type": "int",
            "text": "Size of individual log file (in bytes)",
            "default": 5 * (2**20),  # 5MB
            "scope": Scopes.COMMON,
        },
        "LOGNUM": {
            "type": "int",
            "text": "Number of logging backups to keep of LOGSIZE",
            "default": 4,
            "scope": Scopes.COMMON,
        },
        # 4 * 5MB = 20MB per module
        "CONFIG": {
            "type": "list",
            "text": "System Configuration",
            "hidden": True,
            "scope": Scopes.COMMON,
        },
        "VENV": {
            "type": "str",
            "text": "Location of virtual environment, if used.",
            "scope": Scopes.COMMON,
            "default": str(Path(sys.prefix).resolve())
            if hasattr(sys, "real_prefix") or (sys.base_prefix != sys.prefix)
            else False,
        },
        "AUTOPLUGIN": {
            "type": "bool",
            "text": "Attempt to import the contents of the plugin directory",
            "scope": Scopes.COMMON,
            "default": True,
        },
        "PLUGIN_DB": {
            "type": "str",
            "text": "filename to use for the .json plugin_db that keeps track of installed plugins",
            "default": str(_basedir / "plugin_db.json"),
            "scope": Scopes.COMMON,
        },
        "BASEDIR": {
            "type": "str",
            "text": "Base Directory",
            "default": str(_basedir),
            "scope": Scopes.DIRECTORY,
        },
        "DATADIR": {
            "type": "str",
            "text": "Data Directory",
            "default": str(_basedir / "data"),
            "scope": Scopes.DIRECTORY,
        },
        "SOUNDDIR": {
            "type": "str",
            "text": "Sound file directory",
            "default": str(_basedir / "sounds"),
            "scope": Scopes.DIRECTORY,
        },
        "LOGDIR": {
            "type": "str",
            "text": "Log Directory",
            "default": str(_basedir / "logs"),
            "scope": Scopes.DIRECTORY,
        },
        "VIZDIR": {
            "type": "str",
            "text": "Directory to store Visualization results",
            "default": str(_basedir / "viz"),
            "scope": Scopes.DIRECTORY,
        },
        "PROTOCOLDIR": {
            "type": "str",
            "text": "Protocol Directory",
            "default": str(_basedir / "protocols"),
            "scope": Scopes.DIRECTORY,
        },
        "PLUGINDIR": {
            "type": "str",
            "text": "Directory to import ",
            "default": str(_basedir / "plugins"),
            "scope": Scopes.DIRECTORY,
        },
        "REPODIR": {
            "type": "str",
            "text": "Location of Autopilot repo/library",
            "default": Path(__file__).resolve().parents[1],
            "scope": Scopes.DIRECTORY,
        },
        "CALIBRATIONDIR": {
            "type": "str",
            "text": "Location of calibration files for solenoids, etc.",
            "default": str(_basedir / "calibration"),
            "scope": Scopes.DIRECTORY,
        },
        "PIGPIO": {
            "type": "bool",
            "text": "Launch pigpio daemon on start?",
            "default": True,
            "scope": Scopes.PILOT,
        },
        "PIGPIOMASK": {
            "type": "str",
            "text": "Binary mask controlling which pins pigpio controls according to their BCM numbering, see the -x parameter of pigpiod",
            "default": "1111110000111111111111110000",
            "scope": Scopes.PILOT,
        },
        "PIGPIOARGS": {
            "type": "str",
            "text": "Arguments to pass to pigpiod on startup",
            "default": "-t 0 -l",
            "scope": Scopes.PILOT,
        },
        "PULLUPS": {
            "type": "list",
            "text": "Pins to pull up on system startup? (list of form [1, 2])",
            "scope": Scopes.PILOT,
        },
        "PULLDOWNS": {
            "type": "list",
            "text": "Pins to pull down on system startup? (list of form [1, 2])",
            "scope": Scopes.PILOT,
        },
        "PING_INTERVAL": {
            "type": "float",
            "text": "How many seconds should pilots wait in between pinging the Terminal?",
            "default": 5,
            "scope": Scopes.PILOT,
        },
        "DRAWFPS": {
            "type": "int",
            "text": "FPS to draw videos displayed during acquisition",
            "default": "20",
            "scope": Scopes.TERMINAL,
        },
        "PILOT_DB": {
            "type": "str",
            "text": "filename to use for the .json pilot_db that maps pilots to subjects (relative to BASEDIR)",
            "default": str(_basedir / "pilot_db.json"),
            "scope": Scopes.TERMINAL,
        },
        "TERMINAL_SETTINGS_FN": {
            "type": "str",
            "text": "filename to store QSettings file for Terminal",
            "default": str(_basedir / "terminal.conf"),
            "scope": Scopes.TERMINAL,
        },
        "TERMINAL_WINSIZE_BEHAVIOR": {
            "type": "choice",
            "text": "Strategy for resizing terminal window on opening",
            "choices": ("remember", "moderate", "maximum", "custom"),
            "default": "remember",
            "scope": Scopes.TERMINAL,
        },
        "TERMINAL_CUSTOM_SIZE": {
            "type": "list",
            "text": "Custom size for window, specified as [px from left, px from top, width, height]",
            "default": [0, 0, 1000, 400],
            "depends": ("TERMINAL_WINSIZE_BEHAVIOR", "custom"),
            "scope": Scopes.TERMINAL,
        },
        "LINEAGE": {
            "type": "choice",
            "text": "Are we a parent or a child?",
            "choices": ("NONE", "PARENT", "CHILD"),
            "scope": Scopes.LINEAGE,
        },
        "CHILDID": {
            "type": "list",
            "text": "List of Child ID:",
            "default": [],
            "depends": ("LINEAGE", "PARENT"),
            "scope": Scopes.LINEAGE,
        },
        "PARENTID": {
            "type": "str",
            "text": "Parent ID:",
            "depends": ("LINEAGE", "CHILD"),
            "scope": Scopes.LINEAGE,
        },
        "PARENTIP": {
            "type": "str",
            "text": "Parent IP:",
            "depends": ("LINEAGE", "CHILD"),
            "scope": Scopes.LINEAGE,
        },
        "PARENTPORT": {
            "type": "str",
            "text": "Parent Port:",
            "depends": ("LINEAGE", "CHILD"),
            "scope": Scopes.LINEAGE,
        },
    }
)
"""
Ordered Dictionary containing default values for prefs.

An Ordered Dictionary lets the prefs be displayed in gui elements in a predictable order, but prefs are stored in ``prefs.json`` in
alphabetical order and the 'live' prefs used during runtime are stored in :data:`._PREFS`

Each entry should be a dict with the following structure::

    "PREF_NAME": {
        "type": (str, int, bool, choice, list) # specify the appropriate GUI input, str or int are validators, 
        choices are a 
            # dropdown box, and lists allow users to specify lists of values like "[0, 1]"
        "default": If possible, assign default value, otherwise None
        "text": human-readable text that described the pref
        "scope": to whom does this pref apply? see :class:`.Scopes`
        "depends": name of another pref that needs to be supplied/enabled for this one to be enabled (eg. don't set sampling rate of audio server if audio server disabled)
            can also be specified as a tuple like ("LINEAGE", "CHILD") that enables the option when prefs[depends[0]] == depends[1]
        "choices": If type=="choice", a tuple of available choices.
    }
"""

_WARNED = []
"""
Keep track of which prefs we have warned about getting defaults for
so we don't warn a zillion times
"""


def get(key: typing.Union[str, None] = None):
    """
    Get a pref!

    If a value for the given ``key`` can't be found, prefs will attempt to

    Args:
        key (str, None): get pref of specific ``key``, if ``None``, return all prefs

    Returns:
        value of pref (type variable!), or ``None`` if no pref of passed ``key``
    """

    # if nothing is requested of us, return everything
    if key is None:
        if using_manager:
            return globals()["_PREFS"]._getvalue()
        else:
            return globals()["_PREFS"].copy()

    else:
        # check for deprecation
        dep_notice = globals()["_DEFAULTS"].get(key, {}).get("deprecation", None)
        if dep_notice is not None:
            warnings.warn(dep_notice, FutureWarning)

        # try to get the value from the prefs manager
        try:
            # if it's a directory and it doesn't exist, try and make it
            if (
                globals()["_DEFAULTS"].get(key, {}).get("scope", False)
                == Scopes.DIRECTORY
            ):
                try:
                    path = Path(globals()["_PREFS"][key]).resolve()
                    if not path.exists():
                        path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    warnings.warn(
                        f"prefs {key} was a directory, but a directory couldnt be created. got exception {e}"
                    )
            return globals()["_PREFS"][key]

        # if none exists...
        except KeyError:
            # try to get a default value
            try:
                default_val = globals()["_DEFAULTS"][key]["default"]
                if os.getenv("AUTOPILOT_WARN_DEFAULTS"):
                    if key not in globals()["_WARNED"]:
                        globals()["_WARNED"].append(key)
                        warnings.warn(
                            f"Returning default prefs value {key} : {default_val} (ideally this shouldnt happen and everything should be specified in prefs",
                            DefaultPrefWarning,
                        )
                return default_val

            # if you still can't find a value, None is an unambiguous signal for pref not set
            # (no pref is ever None)
            except KeyError:
                return None


def set(key: str, val):
    """
    Set a pref!

    Note:
        Whenever a pref is set, the prefs file is automatically updated -- prefs are system-durable!!

        (specifically, whenever the module-level ``_INITIALIZED`` value is set to True, prefs are saved to file to
        avoid overwriting before loading)

    Args:
        key (str): Name of pref to set
        val: Value of pref to set (prefs are not type validated against default types)
    """
    globals()["_PREFS"][key] = val
    if using_manager:
        initialized = globals()["_INITIALIZED"].value
    else:
        initialized = globals()["_INITIALIZED"]

    if initialized and "pytest" not in sys.modules:
        save_prefs()


def save_prefs(prefs_fn: str = None):
    """
    Dump prefs into the ``prefs_fn`` .json file

    Args:
        prefs_fn (str, None): if provided, pathname to ``prefs.json`` otherwise resolve ``prefs.json`` according the
        to the normal methods....
    """
    if prefs_fn is None:
        try:
            prefs_fn = str(Path(get("BASEDIR")) / "prefs.json")
        except KeyError:
            raise RuntimeError(
                "Asked to save prefs without BASEDIR being set -- indicative of prefs being saved "
                "before initialized"
            )

    # take lock for access to prefs file
    with globals()["_LOCK"]:
        with open(prefs_fn, "w") as prefs_f:
            if using_manager:
                save_prefs = globals()["_PREFS"]._getvalue()
            else:
                save_prefs = globals()["_PREFS"].copy()
            json.dump(save_prefs, prefs_f, indent=4, separators=(",", ": "))


def init(fn=None):
    """
    Initialize prefs on autopilot start.

    If passed dict of prefs or location of prefs.json, load and use that

    Otherwise

    - Look for the autopilot wayfinder ``~/.autopilot`` file that tells us where the user directory is
    - look in default location ``~/autopilot/prefs.json``

    Todo:

        This function may be deprecated in the future -- in its current form it serves to allow the sorta janky launch
        methods in the headers/footers of autopilot/agents/pilot.py and autopilot/agents/terminal.py that will eventually
        be transformed into a unified agent framework to make launching easier. Ideally one would be able to just
        import prefs without having to explicitly initialize it, but we need to formalize the full launch process
        before we make the full lurch to that model.

    Args:
        fn (str, dict): a path to `prefs.json` or a dictionary of preferences
    """
    if isinstance(fn, str):
        with open(fn, "r") as pfile:
            prefs = json.load(pfile)
    elif isinstance(fn, dict):
        prefs = fn
    elif fn is None:
        # try to load from default location
        autopilot_wayfinder = os.path.join(os.path.expanduser("~"), ".autopilot")
        if os.path.exists(autopilot_wayfinder):
            with open(autopilot_wayfinder, "r") as wayfinder_f:
                fn = os.path.join(wayfinder_f.read(), "prefs.json")
        else:
            fn = os.path.join(os.path.expanduser("~"), "autopilot", "prefs.json")

        if not os.path.exists(fn):
            # tried to load defaults, return quietly
            return

        with open(fn, "r") as pfile:
            prefs = json.load(pfile)

    # Get the current git hash
    if prefs.get("REPODIR", False):
        try:
            prefs["HASH"] = git_version(prefs.get("REPODIR"))
        except Exception as e:
            prefs["HASH"] = ""
            warnings.warn(
                f"git hash for repo could not be found! will not be able to keep good provenance! got exception: \n{e}"
            )
    else:
        warnings.warn("REPODIR is not set in prefs.json, cant get git hash!!!")

    # FIXME: This 100% should not happen here and should happen in the relevant hardware classes.
    # Load any calibration data
    if prefs.get("BASEDIR", False):
        cal_path = os.path.join(prefs["BASEDIR"], "port_calibration_fit.json")
        cal_raw = os.path.join(prefs["BASEDIR"], "port_calibration.json")

        if os.path.exists(cal_path):
            try:
                with open(cal_path, "r") as calf:
                    cal_fns = json.load(calf)
                prefs["PORT_CALIBRATION"] = cal_fns
            except json.decoder.JSONDecodeError:
                warnings.warn(
                    f"calibration file was malformed. Renaming to avoid using in the future"
                )
                os.rename(cal_path, cal_path + ".bak")
        elif os.path.exists(cal_raw):
            # aka raw calibration results exist but no fit has been computed
            try:
                luts = compute_calibration(path=cal_raw, do_return=True)
                with open(cal_path, "w") as calf:
                    json.dump(luts, calf)
                prefs["PORT_CALIBRATION"] = luts
            except json.decoder.JSONDecodeError:
                warnings.warn(
                    f"processed calibration file was malformed. Renaming to avoid using in the future"
                )
                os.rename(cal_raw, cal_raw + ".bak")

    ###########################

    global _PREFS

    for k, v in prefs.items():
        # globals()[k] = v
        _PREFS[k] = v

    # also store as a dictionary so other modules can have one if they want it
    # globals()['__dict__'] = prefs
    if using_manager:
        initialized = globals()["_INITIALIZED"].value = True
    else:
        initialized = globals()["_INITIALIZED"] = True


def add(param, value):
    """
    Add a pref after init

    Args:
        param (str): Allcaps parameter name
        value: Value of the pref
    """
    globals()[param] = value

    global _PREFS
    _PREFS[param] = value


# Return the git revision as a string
def git_version(repo_dir):
    """
    Get the git hash of the current commit.

    Stolen from `numpy's setup <https://github.com/numpy/numpy/blob/master/setup.py#L70-L92>`_

    and linked by ryanjdillon on `SO <https://stackoverflow.com/a/40170206>`_


    Args:
        repo_dir (str): directory of the git repository.

    Returns:
        unicode: git commit hash.
    """

    def _minimal_ext_cmd(cmd):
        # type: (list[str]) -> str
        # construct minimal environment
        env = {}
        for k in ["SYSTEMROOT", "PATH"]:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        # LANGUAGE is used on win32
        env["LANGUAGE"] = "C"
        env["LANG"] = "C"
        env["LC_ALL"] = "C"
        out = subprocess.Popen(cmd, stdout=subprocess.PIPE, env=env).communicate()[0]
        return out

    out = _minimal_ext_cmd(["git", "-C", repo_dir, "rev-parse", "HEAD"])
    GIT_REVISION = out.strip().decode("ascii")

    return GIT_REVISION


def compute_calibration(path=None, calibration=None, do_return=False):
    """

    Args:
        path:
        calibration:
        do_return:

    Returns:

    """
    # FIXME: UGLY HACK - move this function to another module
    import pandas as pd
    from scipy.stats import linregress

    if not calibration:
        # if we weren't given calibration results, load them
        if path:
            open_fn = path
        else:
            open_fn = "/usr/autopilot/port_calibration.json"

        with open(open_fn, "r") as open_f:
            calibration = json.load(open_f)

    luts = {}
    for port, samples in calibration.items():
        sample_df = pd.DataFrame(samples)
        # TODO: Filter for only most recent timestamps

        # volumes are saved in mL because of how they are measured, durations are stored in ms
        # but reward volumes are typically in the uL range, so we make the conversion
        # by multiplying by 1000
        line_fit = linregress(
            (sample_df["vol"] / sample_df["n_clicks"]) * 1000.0, sample_df["dur"]
        )
        luts[port] = {"intercept": line_fit.intercept, "slope": line_fit.slope}

    # write to file, overwriting any previous
    if do_return:
        return luts

    else:
        # do write
        lut_fn = os.path.join(globals()["BASEDIR"], "port_calibration_fit.json")
        with open(lut_fn, "w") as lutf:
            json.dump(luts, lutf)


def clear():
    """
    Mostly for use in testing, clear loaded prefs (without deleting prefs.json)

    (though you will probably overwrite prefs.json if you clear and then set another pref so don't use this except in testing probably)
    """
    global _PREFS
    global _PREF_MANAGER
    if using_manager:
        _PREFS = _PREF_MANAGER.dict()
    else:
        _PREFS = {}


#######################3

if using_manager:
    if not _INITIALIZED.value:
        init()
else:
    if not _INITIALIZED:
        init()

_COMPATIBILITY_MAP = {}


def get_configuration(directory=None, filename=None):
    """
    Getting configuration from respective config.yaml file.

    Arguments:
        directory (str): Path to configuration directory relative to root directory (as Protocols/../...)
        filename (str): Specific file name of the configuration file
    """
    hydra.initialize(version_base=None, config_path=directory)
    return hydra.compose(filename, overrides=[])
