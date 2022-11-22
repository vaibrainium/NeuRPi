import logging
import threading

from NeuRPi.loggers.logger import init_logger
from NeuRPi.networking import Message, Net_Node, Pilot_Station
from NeuRPi.utils.configs import get_configuration

global net_config

config = get_configuration(directory="../config/", filename="setup_config.yaml")
net_config = config.NETWORKING


from NeuRPi.utils import configs


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

        self.name = "rig_1"
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
            port=MSGPORT,
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


if __name__ == "__main__":
    a = Pilot()
