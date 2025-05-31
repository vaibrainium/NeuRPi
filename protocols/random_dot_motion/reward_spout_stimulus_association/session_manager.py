import csv
import pickle
from collections import deque

import numpy as np


class SessionManager:
	"""Class for managing session structure i.e., trial sequence, graduation, and session level summary."""

	def __init__(self, config):
		self.config = config

		# initialize trial variables
		# counters
		self.trial_counters = {
			"attempt": 0,
			"valid": 0,
			"correct": 0,
			"incorrect": 0,
			"noresponse": 0,
			"correction": 0,
		}

		# trial parameters
		self.trial_reward = self.config.TASK["reward"].get("volume", 4)
		self.kor_duration = self.config.TASK["knowledge_of_results"]["duration"]
		self.kor_mode = self.config.TASK["knowledge_of_results"]["mode"]
		self.intertrial_duration = self.config.TASK["intertrial"]["duration"]

		self.bias_window = self.config.TASK["bias_correction"]["window"]
		self.rolling_bias = deque(maxlen=self.bias_window)
		self.rolling_bias.extend([0] * self.bias_window)

		self.bias = 0
		self.switch_threshold = self.config.TASK["bias_correction"]["threshold"]
		self.responses_to_check = [-1, 1]
		self.total_reward = 0


	####################### trial epoch methods #######################
	def prepare_trial_vars(self):
		self.responses_to_check = [-1, 1]
		if np.abs(self.bias) > self.switch_threshold:
			self.responses_to_check = [-np.sign(self.bias)]

	def prepare_reinforcement_stage(self, choice):
		self.choice = choice
		self.rolling_bias.append(self.choice)

		self.bias = np.nanmean(self.rolling_bias)
		stage_task_args = {
			"trial_reward": self.trial_reward,
			"intertrial_duration": self.intertrial_duration,
			"reinforcer_mode": self.kor_mode,
			"reinforcer_direction": self.choice,
			"duration": self.kor_duration,
		}
		stage_stimulus_args = {"coherence": self.choice*100}
		return stage_task_args, stage_stimulus_args

	####################### between-trial methods #######################

	def end_of_trial_updates(self):
		"""Function to finalize current trial and set parameters for next trial."""
		self.trial_counters["attempt"] += 1


		# write trial data to file
		self.write_trial_data_to_file()


		trial_data = {
			"trial_counters": self.trial_counters,
			"choice": self.choice,
			"reward_volume": self.trial_reward,
			"total_reward": self.total_reward,
		}

		return trial_data

	def write_trial_data_to_file(self):
		data = {
			"idx_attempt": self.trial_counters["attempt"],
			"choice": self.choice,
			"trial_reward": self.trial_reward,
			"intertrial_duration": self.intertrial_duration,
			"kor_duration": self.kor_duration,
		}
		with open(self.config.FILES["trial"], "a+", newline="") as file:
			writer = csv.DictWriter(file, fieldnames=data.keys())
			if file.tell() == 0:
				writer.writeheader()
			writer.writerow(data)

	def end_of_session_updates(self):
		self.config.SUBJECT["rolling_perf"]["reward_volume"] = self.trial_reward
		self.config.SUBJECT["rolling_perf"]["total_attempts"] = self.trial_counters["attempt"]
		self.config.SUBJECT["rolling_perf"]["total_reward"] = self.total_reward
		with open(self.config.FILES["rolling_perf_after"], "wb") as file:
			pickle.dump(self.config.SUBJECT["rolling_perf"], file)
		with open(self.config.FILES["rolling_perf"], "wb") as file:
			pickle.dump(self.config.SUBJECT["rolling_perf"], file)
		print("SAVING EOS FILES")
