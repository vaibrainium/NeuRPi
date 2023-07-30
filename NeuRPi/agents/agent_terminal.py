import importlib
import os
import threading
import time
import typing
from collections import OrderedDict as odict
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from NeuRPi.gui.main_gui import Application
from NeuRPi.loggers.logger import init_logger
from NeuRPi.networking import Message, Net_Node, Terminal_Station
from NeuRPi.prefs import prefs
from NeuRPi.utils.get_config import get_configuration


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
        self.heartbeat_dur = (
            10  # check every n seconds whether our pis are still around
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
            "CHANGE": self.l_change,  # A change was notified from pilot
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

    ################################
    # MESSAGE HANDLING METHOD

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
            print("Cound not update GUI")

    def l_change(self, value):
        """
        Incoming change from pilot.

        `value` should have `subject` and `pilot` field added to dictionary for identifiation.

        """
        pass
        # try:
        #     self.message_to_taskgui(value)
        # except:
        #     print("Cound not update GUI")

    ########################
    # GUI and other functions

    def message_from_taskgui(self, message):
        if message["to"] == "main_gui":
            if message["key"] == "KILL":
                self.remove_rig(message["rig_id"])
        else:
            self.node.send(to=message["to"], key=message["key"], value=message["value"])

    def update_rig_availability(self):
        for i, key in enumerate(self.pilots.keys()):
            display_name = self.code_to_str(key)
            if self.main_gui.experiment_rig.findText(display_name) == -1:
                # Add Rig option to the GUI
                self.main_gui.experiment_rig.addItem(display_name)

    def prepare_experiment(self, task_params):
        
        module_directory = "protocols/" + task_params["task_module"]
        config_directoty = module_directory + "/config"
        phase_config = get_configuration(
            directory=config_directoty, filename=task_params["task_phase"]
        )
        task_params["phase_config"] = phase_config

        subject_module = importlib.import_module(
            f"protocols.{task_params['task_module']}.data_model.subject"
        )
        self.subjects[task_params["subject"]] = subject_module.Subject(
            name=task_params["subject"],
            task_module=task_params["task_module"],
            task_phase=task_params["task_phase"],
            config=task_params["phase_config"],
        )
        task_params["subject_config"] = self.subjects[task_params["subject"]].initiate_config()
        return task_params

    def start_experiment(self):
        task_params = super().start_experiment()
        if task_params:
            if self.pilots[task_params["experiment_rig"]]["state"] == "IDLE":
                # Collect information to pass
                task_params = self.prepare_experiment(task_params)

                # Send message to rig to start
                self.node.send(
                    to=task_params["experiment_rig"], key="START", value=task_params
                )
                # Start Task GUI and updating parameters from rig preferences
                gui_module = importlib.import_module(
                    "protocols." + task_params["task_module"] + ".gui.task_gui"
                )
                self.add_new_rig(
                    id=task_params["experiment_rig"], task_gui=gui_module.TaskGUI, 
                    subject_id=task_params["subject"], task_module=task_params["task_module"],
                    task_phase=task_params["task_phase"]
                )
                self.rigs_gui[task_params["experiment_rig"]].set_rig_configuration(
                    self.pilots[task_params["experiment_rig"]]["prefs"]
                )

                # Waiting for rig to initiate program
                while (
                    not self.pilots[task_params["experiment_rig"]]["state"] == "RUNNING"
                ):
                    pass
                # TODO: Start new rig on new QT thread
                # Run experiment on qt thread

                self.clear_variables()
                self.rigs_gui[task_params["experiment_rig"]].start_experiment()

            else:
                msg = QtWidgets.QMessageBox()
                msg.setIcon(QtWidgets.QMessageBox.Critical)
                msg.setText("Rig already engaged!")
                msg.setWindowTitle("Error")
                msg.exec_()
                return None

    def calibrate_reward(self):
        pilot = super().calibrate_reward()
        print(f" Initiate reward calibration for {pilot}")
        if pilot:
            # Send message to rig to caliberate reward
            self.node.send(
                to=pilot,
                key="EVENT",
                value={"key": "REWARD", "value": "calibrate_reward"},
            )

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
