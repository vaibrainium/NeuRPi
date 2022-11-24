import multiprocessing as mp
from ctypes import c_bool
from threading import Lock

import hydra
from omegaconf import OmegaConf


def get_configuration(directory, filename):
    hydra.initialize(version_base=None, config_path=directory)
    return hydra.compose(filename, overrides=[])


# _PREFS = get_configuration(directory, filename)
using_manager = False
try:
    _PREF_MANAGER = (
        mp.Manager()
    )  # initializing multiprocess.Manager to store sync variable across processes

    _PREFS = _PREF_MANAGER.dict()  # initialize sync dict

    _INITIALIZED = mp.Value(
        c_bool, False
    )  #  Boolean flag to indicate whether prefs have been initialzied from file

    _LOCK = mp.Lock()  # threading lock to control prefs file access
    using_manager = True

except (EOFError, FileNotFoundError):
    # can't use mp.Manager in ipython and other interactive contexts
    # fallback to just regular old dict
    print("NOT WORKING")
    _PREF_MANAGER = None
    _PREFS = {}
    _INITIALIZED = False
    _LOCK = Lock()


def get(key=None):
    if key is None:
        # if no key provided, return whole dictionary
        if using_manager:
            return globals()["_PREFS"]._getvalue()
        else:
            return globals()["_PREFS"].copy()
    else:
        # try to get value from prefs manager
        return globals()["_DEFAULTS"][key]


def set(key: str, val):
    globals()["_PREFS"][key] = val
    if using_manager:
        initialized = globals()["_INITIALIZED"].value
    else:
        initialized = globals()["_INITIALIZED"]

    if initialized:
        save_prefs()


def save_prefs(prefs_filename: str = None):
    """
    Saves preferences to ``prefs_filename`` .json
    """

    with globals()["_LOCK"]:
        with open(prefs_filename, "w") as f:
            if using_manager:
                temp_prefs = globals()["_PREFS"]._getvalue()
            else:
                temp_prefs = globals()["_PREFS"].copy
            OmegaConf.save(temp_prefs, f)


def init(directory, filename):
    prefs = get_configuration(directory, filename)

    global _PREFS

    for k, v in prefs.items():
        # globals()[k] = v
        _PREFS[k] = v

    if using_manager:
        initialized = globals()["_INITIALIZED"].value = True
    else:
        initialized = globals()["_INITIALIZED"] = True


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


directory = "config/"
filename = "setup_config.yaml"

if using_manager:
    if not _INITIALIZED.value:
        init(directory, filename)
else:
    if not _INITIALIZED:
        init(directory, filename)


print(1)
