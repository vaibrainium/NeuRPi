import threading
import time

from NeuRPi.hardware.hardware_manager import HardwareManager as BaseHWManager
from NeuRPi.prefs import prefs


class HardwareManager(BaseHWManager):
	"""
	Hardware Manager for RDK protocol
	"""

	def __init__(self):
		super(HardwareManager, self).__init__()

		self.hw_update_event = threading.Event()
		self.hw_update_event.clear()

		self.init_hardware()
		self.reset_lick_sensor()

		self._reward_calibration = self.config.Arduino.Primary.reward.calibration
		self._reward_calibration_left = self.config.Arduino.Primary.reward.calibration_left
		self._reward_calibration_right = self.config.Arduino.Primary.reward.calibration_right

		self.lick_threshold_left = self.config.Arduino.Primary.lick.threshold_left
		self.lick_threshold_right = self.config.Arduino.Primary.lick.threshold_right
		self.lick_slope = self.config.Arduino.Primary.lick.slope

	# Properties for reward calibration left/right
	@property
	def reward_calibration_left(self):
		return self._reward_calibration_left

	@reward_calibration_left.setter
	def reward_calibration_left(self, value: int):
		self._reward_calibration_left = value
		self.config.Arduino.Primary.reward.calibration_left = value
		prefs.set("HARDWARE", self.config)

	@property
	def reward_calibration_right(self):
		return self._reward_calibration_right

	@reward_calibration_right.setter
	def reward_calibration_right(self, value: int):
		self._reward_calibration_right = value
		self.config.Arduino.Primary.reward.calibration_right = value
		prefs.set("HARDWARE", self.config)

	def reset_lick_sensor(self):
		self.hardware["Primary"].write("reset_licks,0\n")

	def reset_wheel_sensor(self):
		self.hardware["Primary"].write("reset_wheel,0\n")

	def start_session(self, session_id=0, filename="session"):
		# Send start_session with session_id and filename
		self.hardware["Primary"].write(f"start_session,{session_id}\n")
		time.sleep(0.05)
		self.hardware["Primary"].write(f"{filename}\n")

	def end_session(self, return_file=0):
		self.hardware["Primary"].write(f"end_session,{return_file}\n")
		if return_file:
			return self.hardware["Primary"].read()

	def update_lick_threshold_left(self, value: int):
		self.lick_threshold_left = value
		self.hardware["Primary"].write(f"update_lick_threshold_left,{value}\n")

	def update_lick_threshold_right(self, value: int):
		self.lick_threshold_right = value
		self.hardware["Primary"].write(f"update_lick_threshold_right,{value}\n")

	def reward_left(self, volume):
		duration = int(self._reward_calibration_left * volume)
		self.hardware["Primary"].write(f"reward_left,{duration}\n")
		print(f"Rewarded Left with {volume} ul")

	def reward_right(self, volume):
		duration = int(self._reward_calibration_right * volume)
		self.hardware["Primary"].write(f"reward_right,{duration}\n")
		print(f"Rewarded Right with {volume} ul")

	def read_licks(self):
		timestamp, lick = None, None
		message = self.hardware["Primary"].read()
		if message:
			try:
				# Expect format: "timestamp<TAB>lick"
				timestamp, lick = message.split("\t")
				timestamp = float(timestamp)
				lick = int(lick)
				print(f"Lick detected: {timestamp}, {lick}")
			except Exception:
				pass
		return timestamp, lick

	def read_wheel(self):
		pass

	def flash_led(self, direction, duration=0.1):
		"""
		Function to flash the LED
		Arguments:
			direction (int): -1: 'Left', 1: 'Right' or 0: 'Center'
		"""
		duration = int(duration * 1000)  # Convert to milliseconds
		if direction == -1:
			self.hardware["Primary"].write(f"flash_left_led,{duration}\n")
		elif direction == 1:
			self.hardware["Primary"].write(f"flash_right_led,{duration}\n")
		elif direction == 0:
			self.hardware["Primary"].write(f"flash_center_led,{duration}\n")
		else:
			raise Exception("Incorrect LED provided. Please provide from the following list: \n 'Left': For left LED" " \n 'Right': For right LED \n 'Center': For center LED")

	def start_calibration_sequence(self, num_pulses=50, volume=1):
		"""
		Instruct arduino to give `no_pulses` on each spout
		"""
		# self.hardware["Primary"].write(str(no_pulses) + "calibrate_reward")
		for pulse in range(num_pulses):
			print(pulse)
			self.reward_left(volume)
			time.sleep(0.5)
			self.reward_right(volume)
			time.sleep(0.5)

if __name__ == "__main__":
	a = HardwareManager()
	print("Hardware Manager Initialized")

	# Reward Calibration
	num_pulses = 10
	num_pulses = input("Please input number of pulse:")
	volume_per_pulse = input("Please input volume per pulse:")
	volume_per_pulse = float(volume_per_pulse)
	print(f"Calibration for Left is {a.reward_calibration_left}")
	print(f"Calibration for Right is {a.reward_calibration_right}")
	time.sleep(5)
	a.start_calibration_sequence(int(num_pulses), volume_per_pulse)
