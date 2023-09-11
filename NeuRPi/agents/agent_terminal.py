import importlib
import os
import threading
import time
import typing
from collections import OrderedDict as odict
from pathlib import Path

from omegaconf import OmegaConf
from PyQt5 import QtCore, QtGui, QtWidgets

from NeuRPi.gui.main_gui import Application
from NeuRPi.loggers.logger import init_logger
from NeuRPi.networking import Message, Net_Node, Terminal_Station
from NeuRPi.prefs import prefs


class Terminal(Application):
    """
    Servert class to initiate and manage all downstream agents.
    """

    def __init__(
        self,
    ):
        super().__init__()

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
            "CHANGE": self.l_change,  # A change was notified from pilot
            "DATA": self.l_data,
            "CONTINUOUS": self.l_data,  # handle continuous data same way as other data
            "STREAM": self.l_data,
            "HANDSHAKE": self.l_handshake,  # a pi is making first contact, telling us its IP
            "SESSION_FILES": self.l_session_files,
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

    ###################### Properties ######################

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
            # self._pilots["rig_2"] = {"ip": "10.155.207.72"}
        return self._pilots

    def new_pilot(
        self,
        name: typing.Optional[str] = None,
        ip: str = "",
        pilot_prefs: typing.Optional[dict] = None,
    ):
        """
        Make a new entry in :attr:`.Terminal.pilots`
        Args:
            ip (str): Optional. if given, stored in db.
            name (str): If None, prompted for a name, otherwise used for entry in pilot DB.
        """
        self._pilots[name] = {
            "ip": ip,
            "prefs": pilot_prefs,
        }

    ################################ inter-object methods ################################
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

    ################################ message handling ################################

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
        # update the pilot button
        self.logger.debug(f"updating pilot state: {value}")
        if value["pilot"] not in self.pilots.keys():
            self.logger.info("Got state info from an unknown pilot, adding...")
            self.new_pilot(name=value["pilot"])

        self.pilots[value["pilot"]]["state"] = value["state"]
        # QT Change
        self.update_rig_availability()

    def l_handshake(self, value):
        """
        Pilot is sending its IP and state on startup.
        If we haven't heard of this pilot before, make a new entry in :attr:`~.Terminal.pilots`

        Args:
            value (dict): dict containing `ip` and `state`
        """

        print("HANDSHAKE RECEIVED from")
        print(value["pilot"])
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
        self.update_rig_availability()

    def l_data(self, value):
        """
        Incoming data from pilot.

        `value` should have `subject` and `pilot` field added to dictionary for identifiation.

        Any key in `value` that matches a column in the subject's trial data table will be saved.

        """
        try:
            self.message_to_taskgui(value)
        except:
            print("Could not update GUI")

    def l_change(self, value):
        """
        Incoming change from pilot.

        `value` should have `subject` and `pilot` field added to dictionary for identifiation.

        """
        pass
        # try:
        #     self.message_to_taskgui(value)
        # except:
        #     print("Could not update GUI")

    def l_session_files(self, value):
        """
        Incoming session files from pilot.

        `value` should have `subject` and `pilot` field added to dictionary for identifiation.

        """
        # with open("lick.csv", "wb") as writer:
        #     writer.write(value["lick"])
        try:
            self.message_to_taskgui(value)
        except Exception as e:
            print("Could not update GUI")
            print(e)

    ######################## GUI related functions ########################
    def code_to_str(self, var: str):
        str_var = var.replace("_", " ")
        str_var = str.title(str_var)
        return str_var

    def str_to_code(self, var: str):
        code_var = var.replace(" ", "_")
        code_var = code_var.lower()
        return code_var

    def message_from_taskgui(self, message):
        if message["to"] == "main_gui":
            if message["key"] == "KILL":
                self.remove_rig(message["rig_id"])
        else:
            self.node.send(to=message["to"], key=message["key"], value=message["value"])

    def update_rig_availability(self):
        for i, key in enumerate(self.pilots.keys()):
            display_name = self.code_to_str(key)
            if self.main_gui.rig_id.findText(display_name) == -1:
                # Add Rig option to the GUI
                self.main_gui.rig_id.addItem(display_name)

    ############################ start experiment functions ############################
    def prepare_session_config(self, session_info):
        """_summary_

        Args:
            session_info (dict): Takes user defined information from GUI and prepares a configuration dictionary to pass to rig

        Returns:
            session_config (OmegaConfdict): Configuration dictionary to pass to rig
        """
        module_path = f"protocols.{session_info.protocol}.{session_info.experiment}.config"
        session_config = importlib.import_module(module_path)

        session_config = importlib.import_module(f"protocols.{session_info.protocol}.{session_info.experiment}.config")
        file_path = Path(
            Path.cwd(),
            Path(f"protocols/{session_info.protocol}/{session_info.experiment}/config.py"),
        )
        with open(file_path, "r") as f:
            string_session_config = f.read()
        return session_config, string_session_config

    def initiate_subject(self, session_info, session_config):
        """
        Initiating subject object and creating file structure for data collection

        Args:
            session_info (dict): Takes user defined information from GUI and prepares a configuration dictionary to pass to rig

        Returns:
            subject (Subject): Subject object

        """
        subject_module = importlib.import_module(f"protocols.{session_info.protocol}.core.data_model.subject")
        self.subjects[session_info.subject_name] = subject_module.Subject(
            session_info=session_info,
            session_config=session_config,
        )
        subject_config = self.subjects[session_info.subject_name].initiate_config()
        return subject_config

    def verify_hardware_requirements(self, session_config):
        """
        Before starting the task, verify that all the hardware requirements to run the task as met
        """
        pass

    def start_experiment(self):
        session_info = self.verify_session_info()
        if session_info:
            if self.pilots[session_info.rig_id]["state"] == "IDLE":
                # Gathering session configuration
                session_config, string_session_config = self.prepare_session_config(session_info)
                # Initializing subject
                subject_config = self.initiate_subject(session_info, session_config)

                self.verify_hardware_requirements(session_config)

                # Send message to rig to start
                self.node.send(
                    to=session_info.rig_id,
                    key="START",
                    value={
                        "session_info": session_info,
                        # python object cannot be sent over network, so converting to string and will convert back to module on rig
                        "session_config": string_session_config,
                        "subject_config": subject_config,
                    },
                    flags={"NOLOG": True},
                )

                # Start Task GUI and updating parameters from rig preferences
                gui_module = importlib.import_module(f"protocols.{session_info.protocol}.core.gui.task_gui")
                self.add_new_rig(
                    id=session_info.rig_id,
                    task_gui=gui_module.TaskGUI,
                    session_info=session_info,
                    subject=self.subjects[session_info.subject_name],
                )
                self.rigs_gui[session_info.rig_id].set_rig_configuration(self.pilots[session_info.rig_id]["prefs"])

                # Waiting for rig to initiate hardware and start session
                while not self.pilots[session_info.rig_id]["state"] == "RUNNING":
                    time.sleep(0.1)

                # self.clear_variables()
                self.rigs_gui[session_info.rig_id].start_experiment()

            else:
                self.critical_message("Rig is not available to start experiment")

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
    app = QtWidgets.QApplication(sys.argv)
    b = Terminal()
    sys.exit(app.exec_())


if __name__ == "__main__":
    import sys

    _TERMINAL = None

    # main()
