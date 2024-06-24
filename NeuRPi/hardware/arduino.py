import time

import serial

from NeuRPi.hardware.hardware import Hardware


class Arduino(Hardware):
    """
    Metaclass for serial devices such as Arduino, Rotary encoders.

    Arguments:
        port (str): Port name for the serial connection.
        baudrate (int): Baud rate of serial communication.
        timeout (int): Timeout for the connection.

    """

    def __init__(self, name=None, port=None, baudrate=None, timeout=None, group="Arduino"):
        super(Arduino, self).__init__()
        self.name = name if name else port
        self.port = port
        self.baudrate = baudrate if baudrate else 9600
        self.timeout = timeout if timeout else False
        self.connection = None

    def connect(self):
        """
        Connect to serial hardware at given port with given baudrate and timeout
        """
        try:
            self.connection = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
            self.is_connected = True
            # self.reset()
        except:
            raise Exception(f"Cannot connect to provided {self.group} device: {self.name} (at '{self.port}')")

    def reset(self):
        # Resetting Teensy
        self.connection.write((str(0) + "reset").encode("utf-8"))
        # time.sleep(1)
        # self.connection.flushInput()
        # # Close the serial port before resetting the Teensy
        # self.connection.close()
        # # Reopen the serial port after the Teensy has reset
        # self.connection.open()

        self.connection.setDTR(False)
        time.sleep(1)
        self.connection.setDTR(True)

    def read(self):
        """
        Read incoming byte data if available.

        Return:
            message (str): Incoming message after byte decoded
        """
        if self.is_connected:
            # message = self.connection.readline(self.connection.inWaiting()).decode().strip()
            try:
                message = self.connection.readline().decode("utf-8").strip()
            except:
                message = self.connection.readline().strip()
            return message
        else:
            raise Warning(f"Please establish hardware connection with {self.group} device: {self.name} (at '{self.port}') before reading")

    def write(self, message):
        """
        Encode and send serial output to the device
        """
        if self.is_connected:
            if isinstance(message, str):
                message = message + "\n"
                self.connection.write(message.encode("utf-8"))
            else:
                try:
                    message = str(message) + "\n"
                    self.connection.write(str(message).encode("utf-8"))
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
