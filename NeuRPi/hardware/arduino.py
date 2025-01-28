
from NeuRPi.hardware.hardware import Hardware
import serial

class Arduino(Hardware):
    """
    Metaclass for serial devices such as Arduino, Rotary encoders.

    Arguments:
        port (str): Port name for the serial connection.
        baudrate (int): Baud rate of serial communication.
        timeout (int): Timeout for the connection.

    """

    def __init__(self, name=None, port=None, baudrate=None, timeout=None):
        super(Arduino, self).__init__()

        if name:
            self.name = name
        else:
            self.name = port
        self.group = 'Arduino'

        self.port = port

        if not baudrate:
            self.baudrate = 9600

        self.timeout = timeout
        self.connection = None

    def connect(self):
        """
        Connect to serial hardware at given port with given baudrate and timeout
        """
        try:
            self.connection = serial.Serial(port = self.port, baudrate = self.baudrate, timeout = self.timeout)
            self.is_connected = True
        except:
            raise Exception(f"Cannot connect to provided {self.group} device: {self.name} (at '{self.port}')")

    def read(self):
        """
        Read incoming byte data if available.

        Return:
            message (str): Incoming message after byte decoded
        """
        if self.is_connected:
            message = self.connection.read(self.connection.inWaiting()).decode()
        else:
            raise Warning(f"Please establish hardware connection with {self.group} device: {self.name} (at '{self.port}') before reading")

        return message

    def write(self, message):
        """
        Encode and send serial output to the device
        """
        if self.is_connected:
            if isinstance(message,str):
                self.connection.write(message.encode())
            else:
                try:
                    self.connection.write(str(message).encode())
                except:
                    raise Warning(f"Could not send message to provided {self.group} device: {self.name} (at '{self.port}')")

    def release(self):
        """
        If connection is already established, release the hardware
        """
        try:
            self.connection.close()
            self.is_connected = False
        except:
            raise Warning(f"Could not close connection with {self.group} device: {self.name} (at '{self.port}')")
