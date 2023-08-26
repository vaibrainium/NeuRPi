import csv
import datetime
import itertools
import queue
import threading
import time

import numpy as np
import tables
from scipy.stats import pearson3

from NeuRPi.tasks.trial_construct import TrialConstruct


class RTTask(TrialConstruct):
    """
    Two-alternative force choice task for random dot motion tasks
    **Stages**
    * **fixation** - fixation time for baseline
    * **stimulus** - Stimulus display
    * **reinforcement** - deliver reward/punishment
    * **intertrial** - waiting period between two trials

    Attributes:
        stim: Current stimulus (coherence)
        target ("L","R"): Correct response
        distractor ("L", "R"): Incorrect response
        response ("L", "R"): Response to discrimination
        correct (0, 1): Current trial was correct/incorrect
        correction_trial (bool): If using correction trial was
        trial_counter (from itertools.count): What is the currect trial was
        discrim_playiong (bool): In the stimulus playing?
        bailed (0, 1): Invalid trial
        current_stage (int): As each is reached, update for asynchronous event reference
    """

    def __init__(
        self,
        stage_block,
        response_block,
        response_queue,
        msg_to_stimulus,
        managers,
        config,
        timers,
        **kwargs,
    ):
        """
        Args:
            stage_block (:class:`threading.Event`): Signal when task stages complete.
            rollling_perf (dict): Dictionary for keeping track of rolling performance over multiple sessions.
            stim (dict): Stimuli like::
                "sitm": {
                    "L": [{"type": "Tone", ...}],
                    "R": [{"type": "Tone", ...}]
                }
            reward (float): duration of solenoid open in ms
            req_reward (bool): Whether to give a water reward in the center port for requesting trials
            punish_stim (bool): Do a white noise punishment stimulus
            punish_dur (float): Duration of white noise in ms
            correction (bool): Should we do correction trials?
            correction_pct (float):  (0-1), What proportion of trials should randomly be correction trials?
            bias_mode (False, "thresholded_linear"): False, or some bias correction type (see :class:`.managers.Bias_Correction` )
            bias_threshold (float): If using a bias correction mode, what threshold should bias be corrected for?
            stim_light (bool): Should the LED be turned blue while the stimulus is playing?
            **kwargs:
        """
        super(RTTask, self).__init__(
            stage_block=stage_block,
            response_block=response_block,
            response_queue=response_queue,
            msg_to_stimulus=msg_to_stimulus,
        )

        self.config = config
        self.subject_config = self.config.SUBJECT
        self.timers = timers
        self.msg_to_stimulus = msg_to_stimulus

        # Event locks, triggers
        self.stage_block = stage_block
        self.response_block = response_block

        # Initializing managers
        self.managers = managers
        

        # Variable parameters
        # Trial variables
        self.trigger = None
        self.stimulus_pars = None
        self.target = None
        self.choice = None
        self.correct = None
        self.valid = None
        self.correction_trial = 0
        # Durations
        self.fixation_duration = None
        self.min_viewing_duration = None
        self.response_time = None
        self.reinforcement_duration = None
        self.intertrial_duration = None

        # This allows us to cycle through the task by just repeatedly calling self.stages.next()
        stage_list = [
            self.fixation_stage,
            self.stimulus_stage,
            self.reinforcement_stage,
            self.intertrial_stage,
        ]
        self.num_stages = len(stage_list)
        self.stages = itertools.cycle(stage_list)

    def fixation_stage(self):
        # Clear stage block
        self.stage_block.clear()

        # resetting variables at the start of trial
        self.stimulus_pars = np.NaN
        self.choice = np.NaN
        self.response_time = np.NaN

        # Determine stage parameters
        targets = [np.NaN]
        self.fixation_duration = self.managers["session"].get_fixation_duration() #self.config.TASK["timings"]["fixation"]["value"]
        self.trigger = {
            "type": "FIXATE_ON",
            "targets": targets,
            "duration": self.fixation_duration,
        }
        stimulus_arguments = {}
        # initiate fixation and start monitoring responses
        self.msg_to_stimulus.put(("fixation_epoch", stimulus_arguments))
        self.timers["trial"] = datetime.datetime.now()
        self.response_block.set()

        # Get current trial properties
        self.subject_config["counters"]["attempt"] += 1
        if not self.correction_trial:
            self.subject_config["counters"]["valid"] += 1

        self.stimulus_pars = self.managers["session"].next_trial(self.correction_trial)
        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_stage": "fixation_stage",
            "subject": self.subject_config["name"],
            "stimulus_pars": self.stimulus_pars,
        }
        return data

    def stimulus_stage(self):
        """
        Stage 1: Show stimulus and wait for response trigger on target/distractor input
        Arguments:
            duration (float): Max stimulus_rt phase duration in secs
            targets (list): Possible responses. [-1: left, 0: center. 1: right, np.NaN: Null]
        """
        # Clear stage block
        self.stage_block.clear()
        # Determine stage parameters
        self.min_viewing_duration, self.duration = self.managers["session"].get_stimulus_duration() #self.config.TASK["timings"]["stimulus"]["min_viewing"]
        stimulus_arguments = self.stimulus_pars
        targets = [-1, 1]
        print(f"Passive Trial Duration is {self.duration}")
        self.trigger = {
            "type": "GO",
            "targets": targets,
            "duration": self.duration - self.min_viewing_duration,
        }

        # initiate stimulus and start monitoring responses
        self.msg_to_stimulus.put(("stimulus_epoch", stimulus_arguments))
        # set respons_block after minimum viewing time
        threading.Timer(self.min_viewing_duration, self.response_block.set).start()

        self.stage_block.wait()
        self.choice = self.response
        self.response_time = (
            self.response_time + self.min_viewing_duration
        )
        print(
            f"Responded with {self.choice} in {self.response_time} secs for target: {self.stimulus_pars['target']}"
        )

        self.stage_block.wait()
        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_stage": "response_stage",
            "choice": self.choice,
            "response_time": self.response_time,
        }
        return data

    def reinforcement_stage(self):
        """
        Stage 2: Evaluate choice and deliver reinforcement (reward/punishment) and decide respective intertrial interval

        """
        # Clear stage block
        self.stage_block.clear()
        # Evaluate trial outcome and determine stage parameters
        stimulus_arguments = {}

        #TODO: pass choice and response time info to session manager to determince reinforcement parameters
        
        # determine valid/invalid and correct/incorrect variables based on performance
        if np.isnan(self.choice):
            valid, correct = 0, 0
            if self.config.TASK["training_type"]["value"] < 2: # if passive training
                correct = 1
        elif self.stimulus_pars["target"] == self.choice:
            valid, correct = 1, 1
            if self.correction_trial:
                valid = 0
        elif self.stimulus_pars["target"] != self.choice:
            valid, correct = 1, 0
            if self.correction_trial:
                valid = 0


        if np.isnan(self.choice):
            if not self.correction_trial:
                self.subject_config["counters"]["noresponse"] += 1
            stimulus_arguments["outcome"] = "invalid"
            self.valid = 0
            self.correct = 0
            # If active training
            if self.config.TASK["training_type"]["value"] == 2:
                self.reinforcement_duration = self.managers["session"].get_reinforcement_duration(outcome="invalid")

            # If passive training
            else:
                self.correct = 1
                if self.stimulus_pars["target"] == -1:  # Left Correct
                    self.managers["hardware"].reward_left(
                        self.subject_config["reward_volume"] * 0.5
                    )
                elif self.stimulus_pars["target"] == 1:  # Right Correct
                    self.managers["hardware"].reward_right(
                        self.subject_config["reward_volume"] * 0.5
                    )
                self.subject_config["total_reward"] += (
                    self.subject_config["reward_volume"] * 0.5
                )

                self.reinforcement_duration = self.managers["session"].get_reinforcement_duration(outcome="correct")
                self.intertrial_duration = self.managers["session"].get_intertrial_duration(outcome="correct")

                # Entering must respond phase
                self.trigger = {
                    "type": "MUST_GO",
                    "targets": [self.stimulus_pars["target"]],
                    "duration": self.reinforcement_duration,
                }
                self.response_block.set()

        # If incorrect trial
        elif self.stimulus_pars["target"] != self.choice:
            if not self.correction_trial:
                self.subject_config["counters"]["incorrect"] += 1
                self.valid = 1
            else:
                self.valid = 0
            stimulus_arguments["outcome"] = "incorrect"
            self.correct = 0

            self.reinforcement_duration = self.managers["session"].get_reinforcement_duration(outcome="incorrect")
            self.intertrial_duration = self.managers["session"].get_intertrial_duration(
                outcome="incorrect", response_time=self.response_time)

        # If correct trial
        elif self.stimulus_pars["target"] == self.choice:
            if not self.correction_trial:
                self.subject_config["counters"]["correct"] += 1
                self.valid = 1
            else: 
                self.valid = 0
            self.correct = 1
            stimulus_arguments["outcome"] = "correct"
            if self.stimulus_pars["target"] == -1:  # Left Correct
                self.managers["hardware"].reward_left(self.subject_config["reward_volume"])
            elif self.stimulus_pars["target"] == 1:  # Right Correct
                self.managers["hardware"].reward_right(
                    self.subject_config["reward_volume"]
                )
            self.subject_config["total_reward"] += self.subject_config["reward_volume"]
            
            self.reinforcement_duration = self.managers["session"].get_reinforcement_duration(outcome="correct")
            self.intertrial_duration = self.managers["session"].get_intertrial_duration(outcome="correct")

            # Entering must respond phase
            self.trigger = {
                "type": "MUST_GO",
                "targets": [self.stimulus_pars["target"]],
                "duration": self.reinforcement_duration,
            }
            self.response_block.set()

        # Starting reinforcement
        self.msg_to_stimulus.put(("reinforcement_epoch", stimulus_arguments))
        threading.Timer(self.reinforcement_duration, self.stage_block.set).start()

        self.stage_block.wait()
        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_stage": "reinforcement_stage",
            "reward_volume": self.subject_config["reward_volume"],
            "reinfocement_duration": self.reinforcement_duration,
            "intertrial_duration": self.intertrial_duration,
        }
        return data

    def intertrial_stage(self, *args, **kwargs):
        """
        Stage 3: Inter-trial Interval.

        """
        # Clear stage block
        self.stage_block.clear()
        # Setting parametes
        arguments = {}
        duration = self.intertrial_duration
        # Starting intertrial interval
        self.msg_to_stimulus.put(("intertrial_epoch", arguments))
        threading.Timer(duration, self.stage_block.set).start()

        # if not correction trial -> perform end of trial analysis
        if not self.correction_trial and not np.isnan(self.choice):
            self.managers["session"].update_EOT(
                self.choice, self.response_time, self.correct
            )

        # log EOT
        self.end_of_trial()
        plots = {
            "running_accuracy": list(self.subject_config["running_accuracy"]),
            "psychometric_function": list(self.subject_config["psych"]),
            "total_trial_distribution": list(self.subject_config["trial_distribution"]),
            "reaction_time_distribution": list(
                self.subject_config["response_time_distribution"]
            ),
        }
        # If incorrect or no response, set correction to be true
        if self.correct and not np.isnan(self.choice):
            self.correction_trial = 0
        else:
            self.correction_trial = 1

        self.stage_block.wait()
        # if correct trial wait for reward consumption
        if self.correct:
            self.must_respond_block.wait()

        data = {
            "DC_timestamp": datetime.datetime.now().isoformat(),
            "trial_stage": "intertrial_stage",
            "trial_counters": self.subject_config["counters"],
            "total_reward": self.subject_config["total_reward"],
            "plots": plots,
            "TRIAL_END": True,
        }
        return data

    def end_of_trial(self):
        # Write trial parameters
        with open(self.config.FILES["trial"], "a+", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    self.subject_config["counters"]["attempt"],
                    self.subject_config["counters"]["valid"],
                    self.correction_trial,
                    self.stimulus_pars["coherence"],
                    self.choice,
                    self.valid,
                    self.correct,
                    round(self.subject_config["reward_volume"], 2),
                    self.fixation_duration,
                    self.min_viewing_duration,
                    self.response_time,
                    self.reinforcement_duration,
                    self.intertrial_duration,
                ]
            )


if __name__ == "__main__":
    stage_block = threading.Event()
    a = RTTask(stage_block=stage_block)
