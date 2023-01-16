"""
Independent task class for input and outputs of the trials.
"""


class Hardware:
    """
    Generic class for handling all hardware. Each class will be run on separate thread.
    Must have features:
    connect: Establishing an initial connection with the hardware.
    release: Releasing the connection to the hardware. Making it available for other/new processes.

    Arguments:
        group (str): Hardware group (such as GPIO)
        name (str): Name of the hardware
        type (str): Type of hardware connection. Serial, I2C, or GPIO
        port (str,int): Connection port or pin
    """

    def __init__(self, group=None, name=None, type=None, port=None, **kwargs):
        self.group = None
        self.name = None
        self.type = None
        self.port = None
        self.is_connected = False

    def connect(self):
        """
        Each hardware will have to implement its own connect method.

        If not defined, a warning is given
        """
        raise Exception("Connect method is not overridden by the subclass")

    def release(self):
        """
        Each hardware will have to implement its own release method.

        If not defined, a warning is given
        """
        raise Exception("Release method is not overridden by the subclass")
