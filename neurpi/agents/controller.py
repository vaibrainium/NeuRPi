import importlib
import os
import signal
import sys
import threading
import time
import typing
from collections import OrderedDict as odict
from pathlib import Path

from PyQt6 import QtWidgets

from neurpi.gui.main_gui import Application
from neurpi.loggers.logger import init_logger
from neurpi.networking import ControllerStation, Net_Node
from neurpi.prefs import prefs
from neurpi.utils import code_to_str


class Controller(Application):
    """
    Controller class to initiate and manage all downstream agents.
    """

    def __init__(
        self,
    ):
        super().__init__()

        # store instance
        globals()["_CONTROLLER"] = self

        # logging
        self.logger = init_logger(self)
        self.logger.info("Starting controller initialization...")

        # networking
        self.node = None
        self.networking = None
        self.heartbeat_dur = 10
        # data
        self.subjects = {}  # Dict of our open subject objects

        # property private attributes
        self._rigs = None

        # Listen dictionary - which methods to call for different messages
        # Methods are spawned in new threads using handle_message
        self.listens = {
            "STATE": self.l_state,  # A Pi has changed state
            "PING": self.l_ping,  # Someone wants to know if we're alive
            "CHANGE": self.l_change,  # A change was notified from rig
            "DATA": self.l_data,
            "CONTINUOUS": self.l_data,  # handle continuous data same way as other data
            "STREAM": self.l_data,
            "HANDSHAKE": self.l_handshake,  # a pi is making first contact, telling us its IP
            "SESSION_FILES": self.l_session_files,
        }  # Start external communications in own process
        # Has to be after init_network so it makes a new context
        self.logger.info("Initializing networking...")
        self.networking = ControllerStation(self.rigs)
        self.networking.start()
        self.logger.info("Station object initialized")

        self.logger.info("Initializing network node...")
        self.node = Net_Node(
            id="_T",
            upstream="T",
            port=prefs.get("MSGPORT"),
            listens=self.listens,
            instance=False,
        )
        self.logger.info("Net Node initialized")

        # send an initial ping looking for our rigs (non-blocking)
        self.logger.info("Sending initial ping to discover rigs...")
        try:
            self.node.send("T", "INIT")
            self.logger.info("Initial ping sent")
        except Exception as e:
            self.logger.warning("Failed to send initial ping: %s", e)

        self.logger.info("Controller initialization completed")

        # if we don't have any rigs, pop a dialogue to declare one
        if len(self.rigs) == 0:
            # TODO: Implement communication with GUI to add new rig
            pass

    ###################### Properties ######################

    @property
    def rigs(self) -> odict:
        """
        A dictionary mapping rig ID to its attributes, including a list of its subjects assigned to it, its IP, etc.

        Returns:
            dict: like ``self.rigs['rig_id'] = {'subjects': ['subject_0', 'subject_1'], 'ip': '192.168.0.101'}``

        """
        # try to load, if none exists make one
        if self._rigs is None:
            # TODO: get rig file with GUI
            self._rigs = odict()
            # self._rigs["rig_2"] = {"ip": "10.155.207.72"}
        return self._rigs

    def new_rig(
        self,
        name: typing.Optional[str] = None,
        ip: str = "",
        rig_prefs: typing.Optional[dict] = None,
    ):
        """
        Make a new entry in :attr:`.Controller.rigs`
        Args:
            ip (str): Optional. if given, stored in db.
            name (str): If None, prompted for a name, otherwise used for entry in rig DB.
        """
        self._rigs[name] = {
            "ip": ip,
            "prefs": rig_prefs,
        }

    ################################ inter-object methods ################################
    def ping_rig(self, rig):
        self.node.send(rig, "PING")

    def heartbeat(self, once=False):
        """
        Perioducally send an ``INIT`` message that checks the status of connected rigs

        sent with frequency according to :attr:`.Controller.heartbeat_dur`

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
        A rig has changed state, keep track of it.

        Args:
            value (dict): dict containing `state` .

        """
        # update the rig button
        self.logger.debug(f"updating rig state: {value}")
        if value["rig"] not in self.rigs.keys():
            self.logger.info("Got state info from an unknown rig, adding...")
            self.new_rig(name=value["rig"])
        self.rigs[value["rig"]]["state"] = value["state"]
        if value["state"] == "INITIALIZED":
            # Waiting for rig to initiate hardware and start session
            # Only call start_experiment if the rig GUI exists (experiment was started from GUI)
            if value["rig"] in self.rigs_gui:
                self.rigs_gui[value["rig"]].start_experiment()

        # QT Change
        self.update_rig_availability()

    def l_handshake(self, value):
        """
        Rig is sending its IP and state on startup.
        If we haven't heard of this rig before, make a new entry in :attr:`~.Controller.rigs`

        Args:
            value (dict): dict containing `ip` and `state`

        """
        self.logger.info(f"HANDSHAKE RECEIVED: {value}")
        print("HANDSHAKE RECEIVED from")
        print(value["rig"])
        if value["rig"] in self.rigs.keys():
            self.rigs[value["rig"]]["ip"] = value.get("ip", "")
            self.rigs[value["rig"]]["state"] = value.get("state", "")
            self.rigs[value["rig"]]["prefs"] = value.get("prefs", {})
            self.logger.info(f"Updated existing rig: {value['rig']}")
        else:
            self.new_rig(
                name=value["rig"],
                ip=value.get("ip", ""),
                rig_prefs=value.get("prefs", {}),
            )
            self.logger.info(f"Added new rig: {value['rig']}")
        self.update_rig_availability()

    def l_data(self, value):
        """
        Incoming data from rig.

        `value` should have `subject` and `rig` field added to dictionary for identification.

        Any key in `value` that matches a column in the subject's trial data table will be saved.
        """
        try:
            self.message_to_taskgui(value)
        except Exception:
            print("Could not update GUI")

    def l_change(self, value):
        """
        Incoming change from rig.

        `value` should have `subject` and `rig` field added to dictionary for identification.

        """
        # try:
        #     self.message_to_taskgui(value)
        # except:
        #     print("Could not update GUI")

    def l_session_files(self, value):
        """
        Incoming session files from rig.

        `value` should have `subject` and `rig` field added to dictionary for identification.

        """
        try:
            self.message_to_taskgui(value)
        except Exception as e:
            print("Could not update GUI")
            print(e)

    ######################## GUI related functions ########################r

    def message_from_taskgui(self, message):
        if message["to"] == "main_gui":
            if message["key"] == "KILL":
                self.remove_rig(message["rig_id"])
        else:
            self.node.send(to=message["to"], key=message["key"], value=message["value"])

    def update_rig_availability(self):
        for i, key in enumerate(self.rigs.keys()):
            display_name = code_to_str(key)
            if self.main_gui.rig_id.findText(display_name) == -1:
                # Add Rig option to the GUI
                self.main_gui.rig_id.addItem(display_name)

    ############################ start experiment functions ############################
    def prepare_session_config(self, session_info):
        """
        _summary_

        Args:
            session_info (dict): Takes user defined information from GUI and prepares a configuration dictionary to pass to rig

        Returns:
            session_config (OmegaConfdict): Configuration dictionary to pass to rig

        """
        return importlib.import_module(
            f"protocols.{session_info.protocol}.{session_info.experiment}.config.{session_info.configuration}",
        )

    def initiate_subject(self, session_info, session_config):
        """
        Initiating subject object and creating file structure for data collection

        Args:
            session_info (dict): Takes user defined information from GUI and prepares a configuration dictionary to pass to rig

        Returns:
            subject (Subject): Subject object

        """
        subject_module = importlib.import_module(
            f"protocols.{session_info.protocol}.core.data_model.subject",
        )
        self.subjects[session_info.subject_id] = subject_module.Subject(
            session_info=session_info,
            session_config=session_config,
        )
        subject_config = self.subjects[session_info.subject_id].initiate_config()
        return subject_config

    def verify_hardware_requirements(self, session_config):
        """
        Before starting the task, verify that all the hardware requirements to run the task as met
        """
        # TODO: Implement hardware verification on the rig

    def start_experiment(self):
        session_info = self.verify_session_info()
        if session_info:
            if self.rigs[session_info.rig_id]["state"] == "IDLE":
                # Gathering session configuration
                session_config = self.prepare_session_config(session_info)
                # Initializing subject
                subject_config = self.initiate_subject(session_info, session_config)

                self.verify_hardware_requirements(session_config)

                # Send message to rig to start
                self.node.send(
                    to=session_info.rig_id,
                    key="START",
                    value={
                        "session_info": session_info,
                        "subject_config": subject_config,
                    },
                    flags={"NOLOG": True},
                )

                # Start Task GUI and updating parameters from rig preferences
                gui_module = importlib.import_module(
                    f"protocols.{session_info.protocol}.core.gui.task_gui",
                )
                self.add_new_rig(
                    id=session_info.rig_id,
                    task_gui=gui_module.TaskGUI,
                    session_info=session_info,
                    subject=self.subjects[session_info.subject_id],
                )
                self.rigs_gui[session_info.rig_id].set_rig_configuration(
                    self.rigs[session_info.rig_id]["prefs"],
                )
            else:
                self.critical_message("Rig is not available to start experiment")

    def closeEvent(self, event):
        """
        When Closing the Controller Window, close any running subject objects,
        'KILL' our networking object.
        """
        # Save the window geometry, to be optionally restored next time

        # TODO: Check if any subjects are currently running, pop dialog asking if we want to stop

        # Close all subjects files
        for m in self.subjects.values():
            if m.running is True:
                m.stop_run()

        # Stop networking
        # send message to kill networking process        self.node.send(key="KILL")
        time.sleep(0.5)
        self.node.release()
        self.logger.debug("Released net node and sent kill message to station")

        event.accept()


def _cleanup_subjects():
    """Helper function to cleanup subjects"""
    global _CONTROLLER
    if not _CONTROLLER:
        return

    for m in _CONTROLLER.subjects.values():
        if hasattr(m, "running") and m.running is True:
            if hasattr(m, "stop_run"):
                m.stop_run()


def _cleanup_networking():
    """Helper function to cleanup networking"""
    global _CONTROLLER
    if not _CONTROLLER:
        return

    # Stop networking station
    if hasattr(_CONTROLLER, "networking") and _CONTROLLER.networking is not None:
        try:
            _CONTROLLER.networking.send(key="KILL")
            time.sleep(0.2)
            if _CONTROLLER.networking.is_alive():
                _CONTROLLER.networking.terminate()
                _CONTROLLER.networking.join(timeout=1.0)
                if _CONTROLLER.networking.is_alive():
                    print("Force killing networking process...")
                    _CONTROLLER.networking.kill()
        except Exception as e:
            print(f"Error stopping networking: {e}")
            try:
                _CONTROLLER.networking.kill()
            except Exception:
                pass

    # Stop node
    if hasattr(_CONTROLLER, "node") and _CONTROLLER.node is not None:
        try:
            _CONTROLLER.node.send(key="KILL")
            time.sleep(0.2)
            _CONTROLLER.node.release()
        except Exception as e:
            print(f"Error stopping node: {e}")


def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) to gracefully exit the application"""
    print("\nReceived Ctrl+C, shutting down gracefully...")

    try:
        _cleanup_subjects()
        _cleanup_networking()
    except Exception as e:
        print(f"Error during shutdown: {e}")

    # Exit the application
    QtWidgets.QApplication.quit()
    sys.exit(0)


def main():
    # Set virtual environment using relative path
    script_dir = Path(__file__).parent
    venv_path = script_dir.parent.parent / ".venv"  # Go up to NeuRPi root, then to .venv

    if venv_path.exists():
        os.environ["VIRTUAL_ENV"] = str(venv_path)
        os.environ["PATH"] = str(venv_path / "Scripts") + os.pathsep + os.environ.get("PATH", "")
        sys.path.insert(0, str(venv_path / "Lib" / "site-packages"))

    # Add the parent directory to Python path if needed
    sys.path.insert(
        0,
        str(Path(__file__).parent.parent),
    )  # Set the package attribute on the current module when running as __main__

    # Add the project root to the path to ensure protocols can be imported
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    import __main__

    if not hasattr(__main__, "__package__") or __main__.__package__ is None:
        __main__.__package__ = "neurpi.agents"

    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    app = QtWidgets.QApplication(sys.argv)  # Configure prefs for controller mode
    from neurpi.prefs import configure_prefs

    configure_prefs(mode="controller")

    # Store the controller instance globally for signal handler access
    global _CONTROLLER
    _CONTROLLER = Controller()

    sys.exit(app.exec())


if __name__ == "__main__":
    import sys

    _CONTROLLER = None

    main()
