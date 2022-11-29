import multiprocessing as mp
from ctypes import c_bool
from pathlib import Path
from threading import Lock

import hydra
from omegaconf import OmegaConf, DictConfig

global _PREF_MANAGER
global _PREFS
global _INITIALIZED
global _LOCK


class Prefs:
    """
    Class to manage configuration files
    """

    def __init__(self, directory=None, filename=None) -> None:

        self.using_manager = False
        self.initialized = False
        self.directory = directory
        self.filename = filename
        self.init_manager()
        self.run()

    def init_manager(self):
        global _PREF_MANAGER
        global _PREFS
        global _INITIALIZED
        global _LOCK

        try:
            _PREF_MANAGER = (
                mp.Manager()
            )  # initializing multiprocess.Manager to store sync variable across processes

            _PREFS = _PREF_MANAGER.dict()  # initialize sync dict

            _INITIALIZED = mp.Value(
                c_bool, False
            )  #  Boolean flag to indicate whether prefs have been initialzied from file

            _LOCK = mp.Lock()  # threading lock to control prefs file access
            self.using_manager = True

        except (EOFError, FileNotFoundError):
            # can't use mp.Manager in ipython and other interactive contexts
            # fallback to just regular old dict
            print("NOT WORKING")
            _PREF_MANAGER = None
            _PREFS = {}
            _INITIALIZED = False
            _LOCK = Lock()

    def import_configuration(self):
        """
        Import saved config file
        """
        hydra.initialize(version_base=None, config_path=self.directory)
        return hydra.compose(self.filename, overrides=[])

    def get(self, key=None):
        """
        Get parameter value
        """
        if key is None:
            # if no key provided, return whole dictionary
            if self.using_manager:
                return globals()["_PREFS"]._getvalue()
            else:
                return globals()["_PREFS"].copy()
        else:
            # try to get value from prefs manager
            return globals()["_PREFS"][key].default

    def set(self, key: str, val):
        """
        Change parameter value
        """
        globals()["_PREFS"][key] = val
        if self.using_manager:
            initialized = globals()["_INITIALIZED"].value
        else:
            initialized = globals()["_INITIALIZED"]

        if initialized:
            self.save_prefs()

    def save_prefs(self, prefs_filename: str = None):
        """
        Saves preferences to ``prefs_filename`` .json
        """

        if not prefs_filename:
            prefs_filename = self.filename

        with globals()["_LOCK"]:
            with open(prefs_filename, "w") as f:
                if self.using_manager:
                    temp_prefs = globals()["_PREFS"]._getvalue()
                else:
                    temp_prefs = globals()["_PREFS"].copy
                OmegaConf.save(temp_prefs, f)

    def run(self):
        """
        Run to Initialize global parameters
        """
        config = self.import_configuration()
        global _PREFS

        for k, v in config.items():
            # globals()[k] = v
            _PREFS[k] = v

        if self.using_manager:
            self.initialized = globals()["_INITIALIZED"].value = True
        else:
            self.initialized = globals()["_INITIALIZED"] = True

    def clear(self):
        """
        Mostly for use in testing, clear loaded prefs (without deleting prefs.json)
        (though you will probably overwrite prefs.json if you clear and then set another pref so don't use this except in testing probably)
        """
        global _PREFS
        global _PREF_MANAGER
        if self.using_manager:
            _PREFS = _PREF_MANAGER.dict()
        else:
            _PREFS = {}


# directory = Path("config")
# prefs = Prefs(directory=directory, filename="networking.yaml")
# print("Network config imported")

global config


@hydra.main(version_base="1.2", config_path="config", config_name="config.yaml")
def import_config(cfg: DictConfig) -> None:

    global config
    config = hydra.utils.instantiate(cfg)
    config.NAME.default = "rig_3"


import_config()
print("Config Imported")
print(config)
