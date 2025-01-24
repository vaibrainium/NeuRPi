import datetime
import itertools
import threading
import time

import numpy as np

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
        self.timers = timers
        self.msg_to_stimulus = msg_to_stimulus

        # Event locks, triggers
        self.stage_block = stage_block
        self.response_block = response_block
        self.response_block.clear()

        # Initializing managers
        self.managers = managers

        # Variable parameters
        # Trial variables
        self.trigger = None
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
        self.delay_duration = None
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
        self.abort_trial = False

    def fixation_stage(self):
        # Clear stage block
        self.stage_block.clear()
        self.managers["hardware"].reset_wheel_sensor()
        self.abort_trial = False

        task_args, stimulus_args = {}, {}
        self.choice = np.NaN
        self.response_time = np.NaN

        # Determine stage parameters
        task_args, stimulus_args = self.managers["session"].prepare_fixation_stage()
        print(f'Fixation stage started: {task_args["fixation_duration"]} secs')
        self.trigger = {
            "type": "GO",
            "targets": task_args["response_to_check"],
            "duration": task_args["fixation_duration"],
        }
        # initiate fixation and start monitoring responses
        self.msg_to_stimulus.put(("fixation_epoch", stimulus_args))
        self.timers["trial"] = datetime.datetime.now()
        self.managers["session"].fixation_onset = datetime.datetime.now() - self.timers["session"]
        self.response_block.set()
        self.stage_block.wait()

        if self.choice != 0:  # if subject broke fixation
            self.abort_trial = True
            self.choice = np.NaN
            self.response_time = np.NaN

        # data = {
        #     "DC_timestamp": datetime.datetime.now().isoformat(),
        #     "trial_stage": "fixation_stage",
        #     "subject": self.config.SUBJECT["name"],
        #     "coherence": task_args["signed_coherence"],
        # }
        # return data

    def stimulus_stage(self):
        """
        Stage 1: Show stimulus and wait for response trigger on target/distractor input
        Arguments:
            duration (float): Max stimulus_rt phase duration in secs
            targets (list): Possible responses. [-1: left, 0: center. 1: right, np.NaN: Null]
        """
        self.stage_block.clear()
        task_args, stimulus_args = {}, {}

        if not self.abort_trial:
            task_args, stimulus_args = self.managers["session"].prepare_stimulus_stage()
            print(f'Stimulus stage started: {task_args["coherence"]} coh')
            self.trigger = {
                "type": "GO",
                "targets": task_args["response_to_check"],
                "duration": task_args["stimulus_duration"] - task_args["minimum_viewing_duration"],
            }
            # initiate stimulus
            # set respons_block after minimum viewing time
            self.msg_to_stimulus.put(("stimulus_epoch", stimulus_args))
            threading.Timer(task_args["minimum_viewing_duration"], self.response_block.set).start()
            self.managers["session"].stimulus_onset = datetime.datetime.now() - self.timers["session"]

            self.stage_block.wait()
            self.managers["session"].response_onset = datetime.datetime.now() - self.timers["session"]
            print(f"Responded in {self.response_time} secs with {self.choice} for target: {task_args['target']} with {task_args['coherence']}")
            # data = {
            #     "DC_timestamp": datetime.datetime.now().isoformat(),
            #     "trial_stage": "stimulus_stage",
            #     "response": self.choice,
            #     "response_time": self.response_time,
            # }
        else:
            self.stage_block.set()
            # data = {
            #     "DC_timestamp": datetime.datetime.now().isoformat(),
            #     "trial_stage": "stimulus_stage",
            #     "response": np.NaN,
            #     "response_time": np.NaN,
            # }

        # return data

    def reinforcement_stage(self):
        """
        Stage 2: Evaluate choice and deliver reinforcement (reward/punishment) and decide respective intertrial interval

        """
        # Clear stage block
        self.stage_block.clear()
        task_args, stimulus_args = {}, {}

        task_args, stimulus_args = self.managers["session"].prepare_reinforcement_stage(self.choice, self.response_time)
        # start reinforcement epoch
        self.msg_to_stimulus.put(("reinforcement_epoch", stimulus_args))

        # wait for reinforcement duration then send message to stimulus manager
        threading.Timer(task_args["reinforcement_duration"], self.stage_block.set).start()
        self.managers["session"].reinforcement_onset = datetime.datetime.now() - self.timers["session"]

        # if reward is requested:
        if task_args["trial_reward"]:
            # give reward
            if task_args["reward_side"] == -1:  # reward left
                self.managers["hardware"].reward_left(task_args["trial_reward"])
                self.managers["session"].total_reward += task_args["trial_reward"]
            elif task_args["reward_side"] == 1:  # reward right
                self.managers["hardware"].reward_right(task_args["trial_reward"])
                self.managers["session"].total_reward += task_args["trial_reward"]

        # If fixed reward ratio is requested:
        if task_args.get("FRR_reward") is not None:
            # give reward after some delay
            time.sleep(0.1)
            if stimulus_args.get("play_FRR_audio") is not None:  # play FRR reward stimulus
                self.msg_to_stimulus.put(("play_audio", stimulus_args["play_FRR_audio"]))
            if task_args["reward_side"] == -1:
                self.managers["hardware"].reward_left(task_args["FRR_reward"])
                self.managers["session"].total_reward += task_args["FRR_reward"]
            elif task_args["reward_side"] == 1:
                self.managers["hardware"].reward_right(task_args["FRR_reward"])
                self.managers["session"].total_reward += task_args["FRR_reward"]
            print(f"FRR reward given: {task_args['FRR_reward']}")

        # waiting for reinforcement durations to be over
        self.stage_block.wait()
        # data = {
        #     "DC_timestamp": datetime.datetime.now().isoformat(),
        #     "trial_stage": "reinforcement_stage",
        #     "reinfocement_duration": task_args["reinforcement_duration"],
        # }
        # return data

    def intertrial_stage(self, *args, **kwargs):
        """
        Stage 3: Inter-trial Interval.

        """
        # Clear stage block
        self.stage_block.clear()
        task_args, stimulus_args = {}, {}

        task_args, stimulus_args = self.managers["session"].prepare_intertrial_stage()
        print(f'ITI stage started: {task_args["intertrial_duration"]} secs')
        if task_args["intertrial_duration"] > 0:
            # start delay epoch
            self.msg_to_stimulus.put(("intertrial_epoch", stimulus_args))
            # wait for delay duration then send message to stimulus manager
            threading.Timer(task_args["intertrial_duration"], self.stage_block.set).start()
        else:
            self.stage_block.set()
        self.managers["session"].intertrial_onset = datetime.datetime.now() - self.timers["session"]

        self.stage_block.wait()
        data = self.managers["session"].end_of_trial_updates()
        data["DC_timestamp"] = datetime.datetime.now().isoformat()
        data["trial_stage"] = "intertrial_stage"
        data["intertrial_duration"] = task_args["intertrial_duration"]
        data["TRIAL_END"] = True
        return data


if __name__ == "__main__":
    stage_block = threading.Event()
    a = RTTask(stage_block=stage_block)
