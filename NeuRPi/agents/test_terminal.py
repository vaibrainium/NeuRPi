import threading
from collections import OrderedDict as odict
from pathlib import Path

from NeuRPi.loggers.logger import init_logger
from NeuRPi.networking import Message, Net_Node, Terminal_Station
from NeuRPi.prefs import prefs


class Terminal:
    def __init__(self) -> None:

        # store instance
        globals()["_TERMINAL"] = self

        # networking
        self.node = None
        self.networking = None
        self.heartbeat_dur = (
            10  # check every n seconds whether our pis are around still
        )

        # data
        self.subjects = {}  # Dict of our open subject objects

        # property private attributes
        self._pilots = None

        # logging
        self.logger = init_logger(self)

        # Listen dictionary - which methods to call for different messages
        # Methods are spawned in new threads using handle_message
        self.listens = {
            "STATE": self.l_state,  # A Pi has changed state
            "PING": self.l_ping,  # Someone wants to know if we're alive
            "DATA": self.l_data,
            "CONTINUOUS": self.l_data,  # handle continuous data same way as other data
            "STREAM": self.l_data,
            "HANDSHAKE": self.l_handshake,  # a pi is making first contact, telling us its IP
        }

        # Start external communications in own process
        # Has to be after init_network so it makes a new context
        self.networking = Terminal_Station(self.pilots)
        self.networking.start()
        self.logger.info("Station object Initialized")

        self.node = Net_Node(
            id="_T",
            upstream="T",
            port=prefs.get("MSGPORT"),
            listens=self.listens,
            instance=False,
        )
        self.logger.info("Net Node Initialized")

        # send an initial ping looking for our pilots
        self.node.send("T", "INIT")

        # start beating ur heart
        # self.heartbeat_timer = threading.Timer(self.heartbeat_dur, self.heartbeat)
        # self.heartbeat_timer.daemon = True
        # self.heartbeat_timer.start()
        # self.heartbeat(once=True)
        self.logger.info("Terminal Initialized")
        ##########################3
        self.run()

    ################
    # Properties

    @property
    def pilots(self) -> odict:
        """
        A dictionary mapping pilot ID to its attributes, including a list of its subjects assigned to it, its IP, etc.

        Returns:
            dict: like ``self.pilots['pilot_id'] = {'subjects': ['subject_0', 'subject_1'], 'ip': '192.168.0.101'}``
        """

        # try to load, if none exists make one
        if self._pilots is None:
            self._pilots = odict()
            self._pilots["rig_4"] = {"ip": "10.155.205.81"}

            # pilot_db_fn = Path(prefs.get("PILOT_DB"))

            # # if pilot file doesn't exist, make blank one
            # if not pilot_db_fn.exists():
            #     self.logger.warning(
            #         f"No pilot_db.json file was found at {pilot_db_fn}, creating a new one"
            #     )
            #     self._pilots = odict()
            #     with open(pilot_db_fn, "w") as pilot_file:
            #         json.dump(self._pilots, pilot_file)

            # # otherwise, try to load it
            # else:
            #     try:
            #         # Load pilots db as ordered dictionary
            #         with open(pilot_db_fn, "r") as pilot_file:
            #             self._pilots = json.load(pilot_file, object_pairs_hook=odict)
            #         self.logger.info(
            #             f"successfully loaded pilot_db.json file from {pilot_db_fn}"
            #         )
            #         self.logger.debug(pformat(self._pilots))
            #     except Exception as e:
            #         self.logger.exception(
            #             (
            #                 f"Exception opening pilot_db.json file at {pilot_db_fn}, got exception: {e}.\n",
            #                 "Not proceeding to prevent possibly overwriting corrupt pilot_db.file",
            #             )
            #         )
            #         raise e

        return self._pilots

    # Listens & inter-object methods
    def ping_pilot(self, pilot):
        self.node.send(pilot, "PING")

    def heartbeat(self, once=False):
        """
        Perioducally send an ``INIT`` message that checks the status of connected pilots

        sent with frequency according to :attr:`.Terminal.heartbeat_dur`

        Args:
            once (bool): if True, do a single heartbeat but don't start a thread to do more.

        """
        self.node.send("T", "INIT", repeat=False, flags={"NOREPEAT": True})

        if not once:
            self.heartbeat_timer = threading.Timer(self.heartbeat_dur, self.heartbeat)
            self.heartbeat_timer.daemon = True
            self.heartbeat_timer.start()

    def l_state(self):
        print(1)

    def l_ping(self):
        pass

    def l_data(self):
        pass

    def l_handshake(self):
        pass

    def run(self):
        while True:
            pass


def main():
    b = Terminal()


if __name__ == "__main__":
    main()
