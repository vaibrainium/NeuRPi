import csv
import pickle

import numpy as np


class SessionManager:
	"""
	Class for managing session structure i.e., trial sequence, graduation, and session level summary.
	"""

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
		self.random_generator_seed = None
		self.is_correction_trial = False
		self.is_repeat_trial = False
		self.signed_coherence = None
		self.target = None
		self.choice = None
		self.response_time = None
		self.valid = None
		self.outcome = None
		self.full_reward_volume = self.config.SUBJECT["rolling_perf"]["reward_volume"]
		self.update_reward_volume()
		self.trial_reward = None  # reward given on current trial
		self.total_reward = 0  # total reward given in session
		self.fixation_duration = None
		self.stimulus_duration = None
		self.minimum_viewing_duration = self.config.TASK["epochs"]["stimulus"]["min_viewing"]
		self.maximum_viewing_duration = self.config.TASK["epochs"]["stimulus"]["max_viewing"]
		self.knowledge_of_results_duration = self.config.TASK["epochs"]["reinforcement"]["knowledge_of_results"]["duration"]
		self.reinforcement_duration = None
		self.intertrial_duration = None
		# stage onset variables
		self.fixation_onset = None
		self.stimulus_onset = None
		self.response_onset = None
		self.reinforcement_onset = None
		self.intertrial_onset = None
		# behavior dependent function
		self.fixation_duration_function = self.config.TASK["epochs"]["fixation"]["duration"]
		self.reinforcement_duration_function = self.config.TASK["epochs"]["reinforcement"]["duration"]
		self.intertrial_duration_function = self.config.TASK["epochs"]["intertrial"]["duration"]
		self.must_consume_reward = self.confic.TASK["reward"]["must_consume"]
		# initialize session variables
		self.full_coherences = self.config.TASK["stimulus"]["signed_coherences"]["value"]
		self.active_coherences = self.full_coherences  # self.config.TASK["stimulus"]["active_coherences"]["value"]
		self.active_coherence_indices = [np.where(self.full_coherences == value)[0][0] for value in self.active_coherences]
		self.coh_to_xrange = {coh: i for i, coh in enumerate(self.full_coherences)}
		# trial block
		self.block_schedule = []
		self.trials_in_block = 0
		self.repeats_per_block = self.config.TASK["stimulus"]["repeats_per_block"]["value"]
		self.schedule_structure = self.config.TASK["stimulus"]["schedule_structure"]["value"]
		# bias
		self.rolling_bias_index = 0
		self.bias_window = self.config.TASK["bias_correction"]["bias_window"]
		self.rolling_bias = np.zeros(self.bias_window)
		self.passive_bias_correction_threshold = self.config.TASK["bias_correction"]["passive"]["coherence_threshold"]
		self.in_active_bias_correction_block = False
		self.active_bias_correction_probability = self.config.TASK["bias_correction"]["active"]["correction_strength"]
		self.active_bias_correction_threshold = self.config.TASK["bias_correction"]["active"]["abs_bias_threshold"]
		# plot variables
		self.plot_vars = {
			"running_accuracy": [],
			"chose_right": {int(coh): 0 for coh in self.full_coherences},
			"chose_left": {int(coh): 0 for coh in self.full_coherences},
			"psych": {int(coh): np.NaN for coh in self.full_coherences},
			"trial_distribution": {int(coh): 0 for coh in self.full_coherences},
			"response_time_distribution": {int(coh): np.NaN for coh in self.full_coherences},
		}

		# list of all variables needed to be reset every trial
		self.trial_reset_variables = [
			self.random_generator_seed,
			self.signed_coherence,
			self.target,
			self.choice,
			self.response_time,
			self.valid,
			self.outcome,
			self.trial_reward,
			# time related dynamic variables
			self.fixation_duration,
			self.stimulus_duration,
			self.reinforcement_duration,
			self.intertrial_duration,
			# epoch onsets
			self.fixation_onset,
			self.stimulus_onset,
			self.response_onset,
			self.reinforcement_onset,
			self.intertrial_onset,
		]

	####################### pre-session methods #######################
	def update_reward_volume(self):
		if self.config.TASK["reward"].get(["volume"]) is not None:
			self.full_reward_volume = self.config.TASK["reward"]["volume"]
		else:
			self.full_reward_volume = 4

	####################### trial epoch methods #######################
	def prepare_fixation_stage(self):
		stage_task_args, stage_stimulus_args = {}, {}
		# resetting trial variables
		for var in self.trial_reset_variables:
			var = None
		# updating random generator seed
		self.random_generator_seed = np.random.randint(0, 1000000)
		# updating trial parameters
		self.prepare_trial_variables()
		# get fixation duration
		self.fixation_duration = self.fixation_duration_function()
		# prepare args
		stage_stimulus_args = ({},)
		stage_task_args = {"fixation_duration": self.fixation_duration, "response_to_check": [-1, 1], "signed_coherence": self.signed_coherence}
		return stage_task_args, stage_stimulus_args

	def prepare_stimulus_stage(self):
		stage_task_args, stage_stimulus_args = {}, {}
		stage_stimulus_args = {
			"coherence": self.signed_coherence,
			"seed": self.random_generator_seed,
			"audio_stim": "onset_tone",
		}
		self.stimulus_duration = self.maximum_viewing_duration
		response_to_check = [-1, 1]

		stage_task_args = {
			"coherence": self.signed_coherence,
			"target": self.target,
			"stimulus_duration": self.stimulus_duration,
			"minimum_viewing_duration": self.minimum_viewing_duration,
			"response_to_check": response_to_check,
		}
		return stage_task_args, stage_stimulus_args

	def prepare_reinforcement_stage(self, choice, response_time):
		"""
		Prepares the reinforcement stage based on the choice and response time.

		Parameters:
		- choice: The choice made during the trial.
		- response_time: The time taken to make the response.

		Returns:
		- A tuple containing stage task arguments and stage stimulus arguments.
		"""
		# Initialize arguments
		stage_task_args, stage_stimulus_args = {}, {}
		self.choice = choice
		self.response_time = response_time

		# Determine trial reward and reinforcement duration and set stage stimulus arguments
		if np.isnan(self.choice):
			self.outcome = "invalid"
			self.trial_reward = 0
			self.reinforcement_duration = self.reinforcement_duration_function["invalid"](self.response_time)
			stage_stimulus_args["outcome"] = "invalid"
		elif self.choice == 0:
			self.outcome = "noresponse"
			self.trial_reward = 0
			self.reinforcement_duration = self.reinforcement_duration_function["noresponse"](self.response_time)
			stage_stimulus_args["outcome"] = "noresponse"
		elif self.choice == self.target:
			self.outcome = "correct"
			self.trial_reward = self.full_reward_volume
			self.reinforcement_duration = self.reinforcement_duration_function["correct"](self.response_time)
			stage_stimulus_args["outcome"] = "correct"
		elif self.choice != self.target:
			self.outcome = "incorrect"
			self.trial_reward = 0
			self.reinforcement_duration = self.reinforcement_duration_function["incorrect"](self.response_time)
			stage_stimulus_args["outcome"] = "incorrect"

		# Set stage task arguments
		stage_task_args = {
			"reinforcement_duration": self.reinforcement_duration,
			"trial_reward": self.trial_reward,
			"reward_side": self.target,
			"FRR_reward": None,
		}
		if self.knowledge_of_results_duration:
			stage_task_args["flash_led"] = {"direction": self.target, "duration": self.knowledge_of_results_duration}

		if self.must_consume_reward and self.trial_reward > 0:
			stage_task_args["wait_for_consumption"] = True

		return stage_task_args, stage_stimulus_args

	def prepare_intertrial_stage(self):
		stage_task_args, stage_stimulus_args = {}, {}
		self.intertrial_duration = self.intertrial_duration_function[self.outcome](self.response_time, self.signed_coherence)

		if self.must_consume_reward and self.trial_reward > 0:
			stage_task_args["wait_for_consumption"] = True
		stage_task_args = {"intertrial_duration": self.intertrial_duration}
		return stage_task_args, stage_stimulus_args

	######################### trial-stage methods #########################
	def prepare_trial_variables(self):
		if (not self.is_correction_trial) & ((not self.in_active_bias_correction_block) & (np.abs(np.nanmean(self.rolling_bias)) >= self.active_bias_correction_threshold)):
			self.in_active_bias_correction_block = True
			correction_direction = -np.sign(np.nanmean(self.rolling_bias))
			self.rolling_bias = np.zeros(self.bias_window)

			self.trials_in_block = 0
			self.generate_active_correction_block_schedule(correction_direction, prob=self.active_bias_correction_probability)
			self.signed_coherence = self.block_schedule[self.trials_in_block]
			self.target = int(np.sign(self.signed_coherence + np.random.choice([-1e-2, 1e-2])))
			self.trials_in_block += 1  # incrementing within block counter

		else:
			if (not self.is_correction_trial) and (not self.is_repeat_trial):  # if not correction trial
				# is this start of new trial block?
				if self.trial_counters["attempt"] == 0 or self.trials_in_block == len(self.block_schedule):
					self.in_active_bias_correction_block = False  # resetting active bias correction block
					self.trials_in_block = 0
					self.generate_block_schedule()
				self.signed_coherence = self.block_schedule[self.trials_in_block]
				self.target = int(np.sign(self.signed_coherence + np.random.choice([-1e-2, 1e-2])))
				self.trials_in_block += 1  # incrementing within block counter
				self.trial_counters["correction"] = 0  # resetting correction counter
			else:
				if self.is_repeat_trial:
					# repeat same stimulus on repeat trial
					pass
				else:
					# drawing repeat trial with direction from a normal distribution with mean of against rolling bias
					self.target = int(np.sign(np.random.normal(-np.mean(self.rolling_bias) * 2, 0.4)))
					# Repeat probability to opposite side of bias
					self.signed_coherence = self.target * np.abs(self.signed_coherence)
					print(f"Rolling choices: {self.rolling_bias} with mean {np.mean(self.rolling_bias)} \n" f"Passive bias correction with: {self.signed_coherence}")
					# increment correction trial counter
					self.trial_counters["correction"] += 1

	def generate_block_schedule(self):
		self.block_schedule = np.repeat(self.active_coherences, self.repeats_per_block)
		if self.schedule_structure == "interleaved":
			self.block_schedule = self.shuffle_seq(self.block_schedule)

	def generate_active_correction_block_schedule(self, correction_direction, prob):
		""" Generate a block of trials with a mix of correction and non-correction trials with 100% coherence"""
		block_length = self.get_active_trial_block_length()

		correction_coherence = 100
		num_correction = int(block_length * prob)
		num_noncorrection = block_length - num_correction
		self.block_schedule = correction_coherence * np.concatenate([np.full(num_correction, correction_direction), np.full(num_noncorrection, -correction_direction)])
		np.random.shuffle(self.block_schedule)

	def get_active_trial_block_length(self):
		values = np.arange(7,14)
		lambda_val = 1.0
		probabilities = np.exp(-lambda_val * (values - 4))
		probabilities /= probabilities.sum()
		chosen_value = np.random.choice(values, p=probabilities)
		return chosen_value

	def shuffle_seq(self, sequence, max_repeat=3):
		"""Shuffle sequence so that no more than max_repeat consecutive elements have same sign"""
		for i in range(len(sequence) - max_repeat + 1):
			subsequence = sequence[i : i + max_repeat]
			if len(set(np.sign(subsequence))) == 1:
				temp_block = sequence[i:]
				np.random.shuffle(temp_block)
				sequence[i:] = temp_block
		return sequence

	####################### between-trial methods #######################

	def end_of_trial_updates(self):
		"""function to finalize current trial and set parameters for next trial"""
		# codify trial outcome
		if self.outcome == "correct":
			self.outcome = 1
		elif self.outcome == "incorrect":
			self.outcome = 0
		elif self.outcome == "noresponse" or self.outcome == "invalid":
			self.outcome = np.NaN

		self.trial_counters["attempt"] += 1

		# function to finalize current trial and set parameters for next trial
		next_trial_vars = {"is_correction_trial": False, "is_repeat_trial": False}
		if self.in_active_bias_correction_block:
			self.valid = False
			next_trial_vars["is_correction_trial"] = False
			if self.outcome != 1:
				next_trial_vars["is_repeat_trial"] = True

		else:
			if self.outcome == 1:
				if not self.is_correction_trial:
					self.valid = True
					self.trial_counters["valid"] += 1
					self.trial_counters["correct"] += 1
				else:
					self.valid = False
				next_trial_vars["is_correction_trial"] = False

			elif self.outcome == 0:
				if not self.is_correction_trial:
					self.valid = True
					self.trial_counters["valid"] += 1
					self.trial_counters["incorrect"] += 1
				else:
					self.valid = False
				# Determine if a correction trial is needed based on signed coherence
				next_trial_vars["is_correction_trial"] = np.abs(self.signed_coherence) > self.passive_bias_correction_threshold

			elif np.isnan(self.outcome):
				self.valid = False
				if self.is_correction_trial:
					next_trial_vars["is_correction_trial"] = True

				if self.choice == 0:
					self.trial_counters["noresponse"] += 1
					if np.abs(self.signed_coherence) > self.passive_bias_correction_threshold:
						next_trial_vars["is_correction_trial"] = True
						next_trial_vars["is_repeat_trial"] = True
				else:
					next_trial_vars["is_repeat_trial"] = True

		# write trial data to file
		self.write_trial_data_to_file()
		self.is_correction_trial = next_trial_vars["is_correction_trial"]
		self.is_repeat_trial = next_trial_vars["is_repeat_trial"]

		# if valid update trial variables and send data to terminal
		if self.valid:
			# update rolling bias
			self.rolling_bias[self.rolling_bias_index] = self.choice
			self.rolling_bias_index = (self.rolling_bias_index + 1) % self.bias_window
			# update plot parameters
			if self.choice == -1:
				# computing left choices coherence-wise
				self.plot_vars["chose_left"][self.signed_coherence] += 1
			elif self.choice == 1:
				# computing right choices coherence-wise
				self.plot_vars["chose_right"][self.signed_coherence] += 1

			tot_trials_in_coh = self.plot_vars["chose_left"][self.signed_coherence] + self.plot_vars["chose_right"][self.signed_coherence]

			# update running accuracy
			if self.trial_counters["correct"] + self.trial_counters["incorrect"] > 0:
				self.plot_vars["running_accuracy"] = [
					self.trial_counters["valid"],
					round(self.trial_counters["correct"] / self.trial_counters["valid"] * 100, 2),
					self.outcome,
				]
			# update psychometric array
			self.plot_vars["psych"][self.signed_coherence] = round(self.plot_vars["chose_right"][self.signed_coherence] / tot_trials_in_coh, 2)

			# update total trial array
			self.plot_vars["trial_distribution"][self.signed_coherence] += 1

			# update reaction time array
			if np.isnan(self.plot_vars["response_time_distribution"][self.signed_coherence]):
				self.plot_vars["response_time_distribution"][self.signed_coherence] = round(self.response_time, 2)
			else:
				self.plot_vars["response_time_distribution"][self.signed_coherence] = round(
					(((tot_trials_in_coh - 1) * self.plot_vars["response_time_distribution"][self.signed_coherence]) + self.response_time) / tot_trials_in_coh,
					2,
				)

		trial_data = {
			"is_valid": self.valid,
			"trial_counters": self.trial_counters,
			"reward_volume": round(self.full_reward_volume, 2),
			"trial_reward": round(self.trial_reward, 2) if self.trial_reward is not None else None,
			"total_reward": round(self.total_reward, 2),
			"plots": {
				"running_accuracy": self.plot_vars["running_accuracy"],
				"psychometric_function": self.plot_vars["psych"],
				"trial_distribution": self.plot_vars["trial_distribution"],
				"response_time_distribution": self.plot_vars["response_time_distribution"],
			},
		}
		return trial_data

	def write_trial_data_to_file(self):
		data = {
			"idx_attempt": self.trial_counters["attempt"],
			"idx_valid": self.trial_counters["valid"],
			"idx_correction": self.trial_counters["correction"],
			"is_correction_trial": self.is_correction_trial,
			"is_repeat_trial": self.is_repeat_trial,
			"in_active_bias_correction_block": self.in_active_bias_correction_block,
			"signed_coherence": self.signed_coherence,
			"target": self.target,
			"choice": self.choice,
			"response_time": self.response_time,
			"is_valid": self.valid,
			"outcome": self.outcome,
			"trial_reward": self.trial_reward,
			"fixation_duration": self.fixation_duration,
			"stimulus_duration": self.stimulus_duration,
			"reinforcement_duration": self.reinforcement_duration,
			"intertrial_duration": self.intertrial_duration,
			"fixation_onset": self.fixation_onset,
			"stimulus_onset": self.stimulus_onset,
			"response_onset": self.response_onset,
			"reinforcement_onset": self.reinforcement_onset,
			"intertrial_onset": self.intertrial_onset,
			"stimulus_seed": self.random_generator_seed,
		}
		with open(self.config.FILES["trial"], "a+", newline="") as file:
			writer = csv.DictWriter(file, fieldnames=data.keys())
			if file.tell() == 0:
				writer.writeheader()
			writer.writerow(data)

	def end_of_session_updates(self):
		self.config.SUBJECT["rolling_perf"]["reward_volume"] = self.full_reward_volume
		self.config.SUBJECT["rolling_perf"]["total_attempts"] = self.trial_counters["attempt"]
		self.config.SUBJECT["rolling_perf"]["total_reward"] = self.total_reward
		with open(self.config.FILES["rolling_perf_after"], "wb") as file:
			pickle.dump(self.config.SUBJECT["rolling_perf"], file)
		with open(self.config.FILES["rolling_perf"], "wb") as file:
			pickle.dump(self.config.SUBJECT["rolling_perf"], file)
		print("SAVING EOS FILES")


if __name__ == "__main__":
	import config

	full_coherences = config.TASK["stimulus"]["signed_coherences"]["value"]
	reward_volume = config.TASK["rolling_performance"]["reward_volume"]
	rolling_window = config.TASK["rolling_performance"]["rolling_window"]
	rolling_perf = {
		"rolling_window": rolling_window,
		"history": {int(coh): list(np.zeros(rolling_window).astype(int)) for coh in full_coherences},
		"history_indices": {int(coh): 49 for coh in full_coherences},
		"accuracy": {int(coh): 0 for coh in full_coherences},
		# "current_coherence_level": current_coherence_level,
		"trials_in_current_level": 0,
		"total_attempts": 0,
		"total_reward": 0,
		"reward_volume": reward_volume,
	}

	config.SUBJECT = {
		# Subject and task identification
		"name": "test",
		"baseline_weight": 20,
		"start_weight": 19,
		"prct_weight": 95,
		"protocol": "random_dot_motion",
		"experiment": "rt_directional_training",
		"session": "1_1",
		"session_uuid": "XXXX",
		"rolling_perf": rolling_perf,
	}

	sm = SessionManager(config)

	sm.prepare_fixation_stage()
	print(sm.block_schedule)

	sm.prepare_stimulus_stage()
	sm.prepare_reinforcement_stage(1, 3)
	print(f"Outcome: {sm.outcome}")

	sm.prepare_intertrial_stage()

	sm.end_of_trial_updates()
	print(f"Outcome: {sm.outcome}")

	sm.prepare_fixation_stage()
	print(f"Is correction Trial: {sm.is_correction_trial}")
