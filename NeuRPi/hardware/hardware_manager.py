import omegaconf

from NeuRPi.hardware.arduino import Arduino
from NeuRPi.hardware.gpio import GPIO
from NeuRPi.prefs import prefs


class HardwareManager(Arduino, GPIO):
    """
    Hardware Manager for RDK protocol
    """

    def __init__(self):
        """
        Arguments:
            config (dict): Dictionary of configuration for task. ALl hardware must be inserted in HARDWARE sub-dictionary.
        """
        self.hardware = {}
        self.config = omegaconf.OmegaConf.create(prefs.get("HARDWARE"))
        pass

    def init_hardware(self):
        """
        Initialize all hardware required by the rig. Defined in HARDWARE dictionary in configuration file.
        """
        for group, container in self.config.items():
            if group == "Arduino":
                for name, properties in container.items():
                    self.hardware[name] = Arduino(**properties.connection)
                    self.hardware[name].connect()

    def update_config(self):
        prefs.set("HARDWARE", self.config)

    def close_hardware(self):
        """
        Disconnect all hardware required by the rig. Defined in HARDWARE dictionary in configuration file.
        """
        for group, container in self.config.items():
            if group == "Arduino":
                for name, properties in container.items():
                    self.hardware[name] = Arduino(**properties.connection)
                    self.hardware[name].connect()


if __name__ == "__main__":
    a = HardwareManager()
    print(2)
