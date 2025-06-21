import importlib
import sys
import threading
import types

from neurpi.loggers.logger import init_logger
from neurpi.networking import Net_Node, RigStation
from neurpi.prefs import prefs


class Rig:
    def __init__(self):
        self.name = prefs.get("NAME")
        self.child = prefs.get("LINEAGE") == "CHILD"
        self.parentid = prefs.get("PARENTID") if self.child else "T"
        self.logger = init_logger(self)
        self.logger.debug("rig logger initialized")

        # Threading and task management
        self.stage_block = threading.Event()
        self.running = threading.Event()
        self.stopping = threading.Event()
        self.stopping.clear()

        # Networking
        self.listens = self._initialize_listens()
        # self._load_plugins(prefs.get("PLUGINS", []))
        self.networking = RigStation()
        self.networking.start()
        self.node = Net_Node(
            id=f"_{self.name}",
            upstream=self.name,
            port=int(prefs.get("MSGPORT")),
            listens=self.listens,
            instance=False,
        )
        self.logger.debug("rig networking initialized")

        # State and session data
        self.state = "IDLE"
        self.update_state()
        self.ip = self.networking.get_ip()
        self._validate_hardware_and_handshake()

        self.task = None
        self._initialize_task_defaults()

    def _initialize_task_defaults(self):
        """Initialize default task-related variables."""
        self.session_info = None
        self.session_config = None
        self.subject_config = None
        self.handware_manager = None
        self.task_manager = None
        self.stimulus_manager = None
        self.display_process = None
        self.modules = None

    def _initialize_listens(self):
        """Define default message handling routes."""
        listens = {
            "START": self.l_start,
            "STOP": self.l_stop,
            "PARAM": self.l_param,
            "EVENT": self.l_event,
        }
        return listens

    def _validate_hardware_and_handshake(self):
        """Check hardware connectivity and perform handshake."""
        if self._verify_hardware_connectivity():
            self.handshake()
            self.logger.debug("Handshake sent")
        else:
            raise TimeoutError(
                "Hardware is not connected. Check connectivity and try again.",
            )

    def _verify_hardware_connectivity(self):
        """Check if all required hardware is connected."""
        # TODO: Placeholder for actual hardware checks
        return True

    def _load_plugins(self, plugin_module_names):
        """
        Load external plugins dynamically and register their handlers.

        Args:
            plugin_module_names (list): List of plugin module names as strings.

        """
        for module_name in plugin_module_names:
            try:
                plugin = importlib.import_module(module_name)
                if hasattr(plugin, "register_handlers"):
                    plugin.register_handlers(self)
                    self.logger.debug(
                        f"Plugin '{module_name}' loaded and handlers registered.",
                    )
                else:
                    self.logger.warning(
                        f"Plugin '{module_name}' does not define 'register_handlers'.",
                    )
            except Exception as e:
                self.logger.exception(f"Failed to load plugin '{module_name}': {e}")

    def handshake(self):
        """Send a handshake message to the controller."""
        hello = {
            "rig": self.name,
            "ip": self.ip,
            "state": self.state,
            "prefs": prefs.get(),
        }
        self.node.send(self.parentid, "HANDSHAKE", value=hello)

    def update_state(self):
        """Send the current state to the controller."""
        self.node.send(self.name, "STATE", self.state, flags={"NOLOG": True})

    ############################### LISTEN FUNCTIONS ########################################
    def register_handler(self, key, handler):
        """
        Register a new handler for the listens dictionary.

        Args:
            key (str): The message type to listen for.
            handler (callable): A callable that will handle the message.

        """
        if not callable(handler):
            raise ValueError(f"Handler for '{key}' must be a callable.")
        self.listens[key] = handler
        self.logger.debug(f"Handler registered for message type: '{key}'")

    def l_start(self, value):
        """Handle task start request from controller."""
        if self.state == "RUNNING" or self.running.is_set():
            self.logger.warning("Task already running. Cannot start new task")
            return

        try:
            self.session_info = value["session_info"]
            self.config = importlib.import_module(f"protocols.{self.session_info.protocol}.{self.session_info.experiment}.config.{self.session_info.configuration}")
            self.config.SUBJECT = value["subject_config"]

            # Import task module and initialize
            task_module = importlib.import_module(
                f"protocols.{self.session_info.protocol}.{self.session_info.experiment}.task",
            )
            self.stage_block.clear()
            self.task = task_module.Task(
                stage_block=self.stage_block,
                config=self.config,
                **value,
            )

            if not self.task.initialize():
                self._handle_task_error("Task initialization failed")
            else:
                self.logger.debug("Task initialized.")
                self.state = "INITIALIZED"
                self.update_state()
                threading.Thread(target=self.run_task, args=(value,)).start()

        except KeyError as e:
            self._handle_task_error(f"Missing required parameter: {e}")
        except Exception as e:
            self._handle_task_error(f"Could not initialize task: {e}")

    def l_stop(self, value):
        """Handle task stop request from controller."""
        self.running.clear()
        self.stopping.set()
        self.state = "IDLE"
        self.update_state()

    def l_param(self, value):
        """Handle parameter update from controller."""
        # TODO: Placeholder for handling parameter updates

    def l_event(self, value):
        """Handle events sent from the controller."""
        key = value.get("key")
        if key == "PAUSE":
            self.running.clear()
            self.state = "PAUSED"
            self.update_state()
        elif key == "RESUME":
            self.running.set()
            self.state = "RUNNING"
            self.update_state()
        elif key == "HARDWARE" and self.task:
            self.task.handle_controller_request(value["value"])

    ############################### SECONDARY FUNCTIONS ########################################
    def convert_str_to_module(self, module_string):
        """
        Convert string to module
        """
        module_name = "session_config"
        session_config = types.ModuleType(module_name)
        exec(module_string, session_config.__dict__)
        return session_config

    def _handle_task_error(self, message):
        """Handle errors during task initialization."""
        self.state = "ERROR"
        self.update_state()
        self.logger.exception(message)

    def run_task(self, value):
        """
        Start running task under new thread
        initiate the task, and progress through each stage of task with `task.stages.next`
        send data to controller after every stage
        waits for the task to clear `stage_block` between stages

        """
        self.logger.debug("Starting task loop")
        self.state = "RUNNING"
        self.running.set()
        self.update_state()

        try:
            while True:
                try:
                    # Task progression
                    data = self._next_stage_data()
                    self.stage_block.wait()
                    self._send_stage_data(data)

                    if self._did_trial_end(data) and not self.running.is_set():
                        if self.stopping.is_set():
                            self._finalize_task()
                            break
                        self.logger.debug("Task paused; waiting for running event.")
                        self.running.wait()

                except StopIteration:
                    self.logger.debug("Task stages exhausted; ending task.")
                    break

        except Exception as e:
            self.logger.exception(f"Error during task execution: {e}")

        finally:
            self._cleanup_task()

    def _next_stage_data(self):
        """Fetch data for the next task stage."""
        data = next(self.task.stages)()
        self.logger.debug("Stage method executed successfully.")
        return data

    def _send_stage_data(self, data):
        """Send data to the controller."""
        if data:
            data.update({"rig": self.name, "subject": self.session_info.subject_id})
            self.node.send("T", "DATA", data)

    def _did_trial_end(self, data):
        """Check if the trial has ended."""
        return isinstance(data, dict) and "TRIAL_END" in data.keys()

    def _finalize_task(self):
        """Finalize the task and send session files."""
        self.stopping.clear()
        self.task.end()
        try:
            session_files = {}
            for file_name, file_path in self.config.FILES.items():
                # Convert Path objects to strings if needed
                file_path_str = str(file_path)

                # Check if file exists before trying to read it
                try:
                    from pathlib import Path

                    if Path(file_path_str).exists():
                        with open(file_path_str, "rb") as f:
                            session_files[file_name] = f.read()
                    else:
                        self.logger.warning(f"Session file {file_name} does not exist at {file_path_str}, skipping")
                        # Create an empty file for missing session files that should exist
                        if file_name in ["lick", "trial"]:
                            session_files[file_name] = b""  # Empty content for missing files
                except Exception as e:
                    self.logger.warning(f"Failed to read session file {file_name} at {file_path_str}: {e}")
                    if file_name in ["lick", "trial"]:
                        session_files[file_name] = b""  # Empty content for failed reads

            value = {
                "rig": self.name,
                "subject": self.session_info.subject_id,
                "session_files": session_files,
            }
            self.node.send("T", "SESSION_FILES", value, flags={"NOLOG": True})
        except Exception:
            self.logger.exception("Failed to send session files to controller.")

    def _cleanup_task(self):
        """Clean up resources after the task ends."""
        self.logger.debug("Stopping task.")
        try:
            del self.task
            self.task = None
        except Exception as e:
            self.logger.exception(f"Error during task cleanup: {e}")
        self.logger.debug("Task stopped.")


def main():
    # Configure prefs for rig mode
    from neurpi.prefs import configure_prefs

    configure_prefs(mode="rig")
    quitting = threading.Event()
    quitting.clear()
    try:
        pi = Rig()
        # handshake is already called during rig initialization

        quitting.wait()

    except KeyboardInterrupt:
        quitting.set()
        sys.exit()


if __name__ == "__main__":
    main()
