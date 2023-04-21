import time

import omegaconf

from NeuRPi.hardware.gpio import GPIO
from NeuRPi.hardware.hardware_manager import HardwareManager as BaseHWManager
from NeuRPi.prefs import prefs


class HardwareManager(BaseHWManager):
    """
    Hardware Manager for RDK protocol
    """

    def __init__(self):
        super(HardwareManager, self).__init__()
        self.init_hardware()
        self._reward_calibration = self.config.Arduino.Primary.reward.caliberation
        self.lick_threshold = self.config.Arduino.Primary.lick.threshold
        self._lick_threshold_left = self.config.Arduino.Primary.lick.threshold_left
        self._lick_threshold_right = self.config.Arduino.Primary.lick.threshold_right
        self.lick_slope = self.config.Arduino.Primary.lick.slope
        pass

    ## Properties of our hardwares
    @property
    def reward_caliberation(self):
        return self._reward_calibration

    @reward_caliberation.setter
    def reward_caliberation(self, value: int):
        self._reward_calibration = value
        self.config.Arduino.Primary.reward.caliberation = value
        prefs.set("HARDWARE", self.config)

    @property
    def lick_threshold(self):
        return self._lick_threshold

    @lick_threshold.setter
    def lick_threshold(self, value: int):
        self._lick_threshold = value
        self.config.Arduino.Primary.lick.threshold = value
        prefs.set("HARDWARE", self.config)
        self.hardware["Primary"].write(str(value) + "update_lick_threshold")

    @property
    def lick_threshold_left(self):
        return self._lick_threshold_left

    @lick_threshold_left.setter
    def lick_threshold_left(self, value: int):
        self._lick_threshold_left = value
        self.config.Arduino.Primary.lick.threshold_left = value
        prefs.set("HARDWARE", self.config)
        self.hardware["Primary"].write(str(value) + "update_lick_threshold_left")

    @property
    def lick_threshold_right(self):
        return self._lick_threshold_right

    @lick_threshold_right.setter
    def lick_threshold_right(self, value: int):
        self._lick_threshold_right = value
        self.config.Arduino.Primary.lick.threshold_right = value
        prefs.set("HARDWARE", self.config)
        self.hardware["Primary"].write(str(value) + "update_lick_threshold_right")

    @property
    def lick_slope(self):
        return self._lick_slope

    @lick_slope.setter
    def lick_slope(self, value: int):
        self._lick_slope = value
        self.config.Arduino.Primary.lick.slope = value
        prefs.set("HARDWARE", self.config)
        self.hardware["Primary"].write(str(value) + "update_lick_slope")

    ## Other useful functions
    def vol_to_dur(self, volume):
        """
        Converting volume of reward to ms

        Arguments:
            volume (float): Amount of reward to be given in ml
        """
        duration = self._reward_calibration * volume
        return int(duration)

    def reward_left(self, volume):
        """
        Dispense 'volume' of Reward to Left spout
        """
        duration = self.vol_to_dur(volume)
        self.hardware["Primary"].write(str(duration) + "reward_left")
        print("Rewarded Left")
        # raise Warning("Reward delivery needs to be implemented")

    def reward_right(self, volume):
        """
        Dispense 'volume' of Reward to Right spout
        """
        duration = self.vol_to_dur(volume)
        self.hardware["Primary"].write(str(duration) + "reward_right")
        print("Rewarded Right")

    def toggle_reward(self, spout):
        """
        Toggle reward spout.
        Arguments:
            spout (str): 'Left','Right' or 'Center'
        """
        if spout == "Left":
            self.hardware["Primary"].write(str(0) + "toggle_left_reward")
        elif spout == "Right":
            self.hardware["Primary"].write(str(0) + "toggle_right_reward")
        elif spout == "Center":
            self.hardware["Primary"].write(str(0) + "toggle_center_reward")
        else:
            raise Exception(
                "Incorrect spout provided. Please provide from the following list: \n 'Left': For left spout"
                " \n 'Right': For right spout \n 'Center': For center spout"
            )

    def start_caliberation_sequence(self, no_pulses=50):
        """
        Instruct arduino to give `no_pulses` on each spout
        """
        self.hardware["Primary"].write(str(no_pulses) + "caliberate_reward")

    def read_licks(self):
        """
        Function to detect if there's an incoming signal. If so, decode the signal to lick direction and retunrn
        Returns:
            lick (int): Lick direction.
                        {-1: Left Spout Licked,
                         -2: Left Spout Free
                         1: Right Spout Licked,
                         2: Right Spout Free}
        """
        lick = None
        message = self.hardware["Primary"].read()
        if message:
            lick = int(float(message)) - 3
        return lick


if __name__ == "__main__":
    a = HardwareManager()
    print(a.lick_threshold, a.lick_threshold_left, a.lick_threshold_right, a.lick_slope)
    while True:
        lick = a.read_licks()
        if lick:
            print(lick)
    print(2)
