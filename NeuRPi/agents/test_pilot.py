import logging
import multiprocessing as mp
import threading

import sys
from NeuRPi.prefs import config
from NeuRPi.loggers.logger import init_logger
from NeuRPi.networking import Message, Net_Node, Pilot_Station


class Pilot:

    logger = None

    # Events for thread handling
    running = None
    stage_block = None
    file_block = None
    quitting = None

    # networking
    node = None
    networking = None

    def __init__(self, warn_defaults=True):

        self.name = prefs.get("NAME")
        if prefs.get("LINEAGE") == "CHILD":
            self.child = True
            self.parentid = prefs.get("PARENTID")
        else:
            self.child = False
            self.parentid = "T"

        self.logger = init_logger(self)
        self.logger.debug("pilot logger initialized")

        # Locks, etc. for threading
        self.running = threading.Event()  # Are we running a task?
        self.stage_block = threading.Event()  # Are we waiting on stage triggers?
        self.file_block = threading.Event()  # Are we waiting on file transfer?
        self.quitting = threading.Event()
        self.quitting.clear()

        # initialize listens dictionary
        self.listens = {
            "START": self.l_start,
            "STOP": self.l_stop,
            "PARAM": self.l_param,
            "CHECK": self.l_checking,
        }

        # initialize station and node
        self.networking = Pilot_Station()
        self.networking.start()
        self.node = Net_Node(
            id="_{}".format(self.name),
            upstream=self.name,
            port=int(prefs.get("MSGPORT")),
            listens=self.listens,
            instance=False,
        )
        self.logger.debug("pilot networking initialized")

        # set and update state
        self.state = "IDLE"  # or 'Running'
        self.update_state()

        # handshake on initialization
        self.ip = self.networking.get_ip()

    def update_state(self):
        pass

    def l_start(self):
        pass

    def l_stop(self):
        pass

    def l_param(self):
        pass

    def l_checking(self):
        pass


def main():
    config.NAME = "rig_2"
    # a = Pilot()
    # prefs.set(key="NAME", val="rig_2")
    # prefs.save_prefs()
    # print(2)
    # a.quitting.wait(timeout=1)
    # sys.exit()


if __name__ == "__main__":
    main()
