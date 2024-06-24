import os
import threading
import typing
from collections import OrderedDict as odict
from pathlib import Path

from NeuRPi.data_model.subject import Subject
from NeuRPi.loggers.logger import init_logger
from NeuRPi.networking import Message, Net_Node, Terminal_Station
from NeuRPi.prefs import prefs


class Terminal:
    """
    Servert class to initiate and manage all downstream agents.
    """

    def __init__(self):

        # store instance
        globals()["_TERMINAL"] = self

        # networking
        self.node = None
        self.networking = None
        self.heartbeat_dur = 10  # check every n seconds whether our pis are still around

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

        self.logger.info("Terminal Initialized")

        # if we don't have any pilots, pop a dialogue to declare one
        if len(self.pilots) == 0:
            # TODO: Implement communication with GUI to add new pilot
            pass

        ##########################

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
            # TODO: get pilot file with GUI
            self._pilots = odict()
            self._pilots["rig_4"] = {"ip": "10.155.205.81"}
        return self._pilots

    @property
    def subject_list(self) -> list:
        """
        Get a list of all subject IDs

        Returns:
            list: list of subject names in `PROTOCOLDIR` directory

        """
        subjects = []
        for pilot, vals in self.pilots.items():
            subjects.extend(vals["subjects"])

        subjects - list(set(subjects))

        return subjects

    @property
    def protocols(self) -> list:
        """
        List of protocol names available in `PROTOCOLDIR` directory

        Returns:
            list: list of protocol names in `PROTOCOLDIR` directory
        """
        protocols = os.listdir(prefs.get("PROTOCOLDIR"))
        protocols = [os.path.splitext(p)[0] for p in protocols if p.endswith(".json")]
        return protocols

    @property
    def subject_protocol(self) -> dict:
        """
        Returns:
            subject_protocols (dict): a dictionary of subjects: [protocol, step]
        """
        # get subjects and current protocols
        subjects = self.subject_list
        subjects_protocols = {}
        for subject in subjects:
            if subject not in self.subjects.keys():
                self.subjects[subject] = Subject(subject)

            try:
                subjects_protocols[subject] = [
                    self.subjects[subject].protocol.protocol_name,
                    self.subjects[subject].protocol.step,
                ]
            except AttributeError:
                subjects_protocols[subject] = [None, None]
        return subjects_protocols

    ###############################
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

    def toggle_start(self, starting, pilot, subject=None, protocol=None, task_phase=None):
        """
        Start or Stop running the currently selected subject's task. Sends a
        message containing the task information to the concerned pilot.
        Each :class:`Pilot_Panel` is given a lambda function that calls this
        one with the arguments specified See :class:`Pilot_Button`, as it is
        what calls this function.
        Args:
            starting (bool): Does this button press mean we are starting (True)
                or stopping (False) the task?
            pilot: Which Pilot is starting or stopping?
            subject: Which Subject is currently selected?
            protocol: Which task subject will be running on?
            task_phase: What phase of the task subject will be performing?
        """
        # stopping is the enemy of starting so we put them in the same function to learn about each other
        if starting is True:
            # Get Weights
            start_weight, ok = QtWidgets.QInputDialog.getDouble(self, "Set Starting Weight", "Starting Weight:")
            if ok:
                # Ope'nr up if she aint
                if subject not in self.subjects.keys():
                    self.subjects[subject] = Subject(subject, protocol, task_phase)

                self.subjects[subject].update_weights(start=float(start_weight))
                task = self.subjects[subject].prepare_run()
                task["pilot"] = pilot

                self.node.send(to=pilot, key="START", value=task)
                # also let the plot know to start
                self.node.send(to="P_{}".format(pilot), key="START", value=task)

            else:
                # pressed cancel, don't start
                return

        else:
            # Send message to pilot to stop running,
            self.node.send(to=pilot, key="STOP")
            # also let the plot know to start
            self.node.send(to="P_{}".format(pilot), key="STOP")
            # Get Weights
            stop_weight, ok = QtWidgets.QInputDialog.getDouble(self, "Set Stopping Weight", "Stopping Weight:")

            self.subjects[subject].stop_run()
            self.subjects[subject].update_weights(stop=float(stop_weight))

    ################################
    # MESSAGE HANDLING METHOD

    def l_data(self, value):
        """
        Incoming data from pilot.

        `value` should have `subject` and `pilot` field added to dictionary for identifiation.

        Any key in `value` that matches a column in the subject's trial data table will be saved.

        If the subject graduates after receiving this piece of data, stop the current
        task running on the Pilot and send the new one.

        Args:
            value (dict): A dict of field-value pairs to save

        """

        # Save the data pilot has sent us
        subject_name = value["subject"]
        self.subjects[subject_name].save_data(value)

        # if self.subjects[subject_name].did_graduate.is_set() is True:
        #     self.node.send(to=value['pilot'], key="STOP", value={'graduation':True})
        #     self.subjects[subject_name].stop_run()
        #     self.subjects[subject_name]._graduate()
        #     task = self.subjects[subject_name].prepare_run()
        #     task['pilot'] = value['pilot']

        #     # FIXME: Don't hardcode wait time, wait until we get confirmation that the running task has fully unloaded
        #     time.sleep(5)

        #     self.node.send(to=value['pilot'], key="START", value=task)

    def l_ping(self, value):
        # Only our Station object should ever ping us, because
        # we otherwise want it handling any pings on our behalf.

        # self.send_message('ALIVE', value=b'T')
        pass

    def l_state(self, value):
        """
        A Pilot has changed state, keep track of it.

        Args:
            value (dict): dict containing `state` .
        """
        # TODO: If we are stopping, we enter into a cohere state
        # TODO: If we are stopped, close the subject object.
        # TODO: Also tell the relevant dataview to clear

        # update the pilot button
        self.logger.debug(f"updating pilot state: {value}")
        if value["pilot"] not in self.pilots.keys():
            self.logger.info("Got state info from an unknown pilot, adding...")
            self.new_pilot(name=value["pilot"])

        self.pilots[value["pilot"]]["state"] = value["state"]
        # QT Change
        # self.control_panel.panels[value["pilot"]].button.set_state(value["state"])

    def l_handshake(self, value):
        """
        Pilot is sending its IP and state on startup.
        If we haven't heard of this pilot before, make a new entry in :attr:`~.Terminal.pilots`

        Args:
            value (dict): dict containing `ip` and `state`
        """
        if value["pilot"] in self.pilots.keys():
            self.pilots[value["pilot"]]["ip"] = value.get("ip", "")
            self.pilots[value["pilot"]]["state"] = value.get("state", "")
            self.pilots[value["pilot"]]["prefs"] = value.get("prefs", {})

        else:
            self.new_pilot(
                name=value["pilot"],
                ip=value.get("ip", ""),
                pilot_prefs=value.get("prefs", {}),
            )

        # update the pilot button
        if value["pilot"] in self.control_panel.panels.keys():
            self.control_panel.panels[value["pilot"]].button.set_state(value["state"])

    ########################
    # GUI and other functions

    def new_pilot(
        self,
        name: typing.Optional[str] = None,
        ip: str = "",
        pilot_prefs: typing.Optional[dict] = None,
    ):
        """
        Make a new entry in :attr:`.Terminal.pilots` and make appropriate
        GUI elements.
        Args:
            ip (str): Optional. if given, stored in db.
            name (str): If None, prompted for a name, otherwise used for entry in pilot DB.
        """
        pass
        # if name is None:
        #     name, ok = QtWidgets.QInputDialog.getText(self, "Pilot ID", "Pilot ID:")
        #     if not ok or not name:
        #         self.logger.info("Cancel button clicked, not adding new pilot")
        #         return

        # # Warn if we're going to overwrite
        # if name in self.pilots.keys():
        #     self.logger.warning(
        #         f"pilot with id {name} already in pilot db, overwriting..."
        #     )

        # if pilot_prefs is None:
        #     pilot_prefs = {}

        # self.control_panel.add_pilot(name)
        # new_pilot = {name: {"subjects": [], "ip": ip, "prefs": pilot_prefs}}
        # self.control_panel.update_db(new=new_pilot)
        # self.logger.info(f"added new pilot {name}")

    def run(self):
        while True:
            pass

    def closeEvent(self, event):
        """
        When Closing the Terminal Window, close any running subject objects,
        'KILL' our networking object.
        """
        # Save the window geometry, to be optionally restored next time

        # TODO: Check if any subjects are currently running, pop dialog asking if we want to stop

        # Close all subjects files
        for m in self.subjects.values():
            if m.running is True:
                m.stop_run()

        # Stop networking
        # send message to kill networking process
        self.node.send(key="KILL")
        time.sleep(0.5)
        self.node.release()
        self.logger.debug("Released net node and sent kill message to station")

        event.accept()


def main():
    b = Terminal()


if __name__ == "__main__":
    _TERMINAL = None

    main()
