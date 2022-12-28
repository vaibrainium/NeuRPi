from NeuRPi.hardware.arduino import Arduino
from NeuRPi.hardware.hardware import Hardware
from NeuRPi.hardware.gpio import GPIO

class HardwareManager(Arduino, GPIO):
    """
    Hardware Manager for RDK protocol
    """

    def __init__(self, config = None):
        """
        Arguments:
            config (dict): Dictionary of configuration for task. ALl hardware must be inserted in HARDWARE sub-dictionary.
        """
        self.calibration = 0
        self.hardware = {}
        self.config = config
        self.init_hardware()

    def init_hardware(self):
        """
        Initialize all hardware required by the task. Defined in HARDWARE dictionary in configuration file.
        """
        for group, container in self.config.HARDWARE.items():
            if group == 'Arduino':
                for name, properties in container.items():
                    connect = properties['connection']
                    exec(f"""self.hardware['{name}'] = Arduino(name='{name}', port='{connect['port']}', baudrate = {connect['baudrate']}, timeout={connect['timeout']})""")
                    exec(f"""self.hardware['{name}'].connect()""")

    def close_hardware(self):
        raise Warning('TODO: Not Implemented')

    def read_licks(self):
        """
        Function to detect if there's an incoming signal. If so, decode the signal to lick direction and retunrn
        Returns:
            lick (int): Lick direction.
                        {1: Left Spout Licked,
                         -2: Left Spout Free
                         1: Right Spout Licked,
                         2: Right Spout Free}
        """
        lick = None
        message = self.hardware['Primary'].read()
        if message:
            lick = int(message) - 3
        return lick

    def reward_left(self, volume):
        """
        Dispense 'volume' of Reward to Left spout

        Arguments:
            volume (float): Amount of reward to be given in ml

        """
        open_time = self.vol_to_dur(volume)
        # raise Warning("Reward delivery needs to be implemented")

    def reward_right(self, volume):
        """
        Dispense 'volume' of Reward to Right spout

        Arguments:
            volume (float): Amount of reward to be given in ml

        """
        open_duration = self.vol_to_dur(volume)
        # raise Warning("Reward delivery needs to be implemented")

    def vol_to_dur(self, volume):
        """
        Converting volume of reward to ms

        Arguments:
            volume (float): Amount of reward to be given in ml
        """
        open_duration = self.calibration * volume
        return open_duration

    def reward_caliberation(self):
        """
        Method to calibrate reward.
        """
        self.calibration = 30
        raise Warning("TODO: Not Implemented")

    def open_reward_indefinitely(self, spout):
        """
        Open reward spout indefinitely for priming purposes.
        Arguments:
            spout (str): 'Left','Right' or 'Center'
        """
        if spout == 'Left':
            raise Warning("TODO: Not Implemented")
        elif spout == 'Right':
            raise Warning("TODO: Not Implemented")
        elif spout == 'Center':
            raise Warning("TODO: Not Implemented")
        else:
            raise Exception("Incorrect spout provided. Please provide from the following list: \n 'Left': For left spout"
                            " \n 'Right': For right spout \n 'Center': For center spout")

    def close_reward_indefinitely(self, spout):
        """
        Close reward spout indefinitely for priming purposes.
        Arguments:
            spout (str): 'Left','Right' or 'Center'
        """
        if spout == 'Left':
            raise Warning("TODO: Not Implemented")
        elif spout == 'Right':
            raise Warning("TODO: Not Implemented")
        elif spout == 'Center':
            raise Warning("TODO: Not Implemented")
        else:
            raise Exception(
                "Incorrect spout provided. Please provide from the following list: \n 'Left': For left spout"
                " \n 'Right': For right spout \n 'Center': For center spout")




if __name__ == '__main__':
    a = HardwareManager()
    print(2)