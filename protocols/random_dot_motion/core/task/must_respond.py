import datetime
import itertools
import queue
import threading

from neurpi.tasks.trial_construct import TrialConstruct


class MustRespond(TrialConstruct):
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

        """
        super(MustRespond, self).__init__(
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
            self.must_respond_stage,
            self.reinforcement_stage,
            self.intertrial_stage,
        ]
        self.num_stages = len(stage_list)
        self.stages = itertools.cycle(stage_list)

    def must_respond_monitor(self, target):
        """
        Making sure that agent responds to target.
        """
        must_respond_success = False
        self.must_respond_block.clear()
        while not must_respond_success:
            try:
                response = self.response_queue.get(block=True)
                if response in target:
                    must_respond_success = True
                    self.clear_queue()
                    self.response_block.clear()
            except queue.Empty:
                pass

        return response

    def response_monitor_loop(self):
        while True:
            self.trigger = None
            self.clear_queue()
            self.must_respond_block.clear()
            self.response_block.wait()
            try:
                if self.trigger["type"] == "MUST_RESPOND":
                    self.choice = self.must_respond_monitor(self.trigger["targets"])
                    self.must_respond_block.set()
            except Exception as e:
                print(e)
                raise Warning(
                    f"Problem with response monitoring for {self.trigger['type']}",
                )

    def fixation_stage(self):
        # Clear stage block
        self.stage_block.clear()

        self.managers["session"].prepare_trial_vars()
        self.timers["trial"] = datetime.datetime.now()
        self.managers["session"].fixation_onset = datetime.datetime.now() - self.timers["session"]

        print(
            f"Current Bias: {self.managers['session'].bias}. Threshold: {self.managers['session'].switch_threshold}",
        )
        self.stage_block.set()

    def must_respond_stage(self):
        """
        Stage 1: Show stimulus and wait for response trigger on target/distractor input
        Arguments:
                duration (float): Max stimulus_rt phase duration in secs
                targets (list): Possible responses. [-1: left, 0: center. 1: right, np.nan: Null]
        """
        self.stage_block.clear()
        print("Waiting for response")
        self.trigger = {
            "type": "MUST_RESPOND",
            "targets": self.managers["session"].responses_to_check,
            "duration": None,
        }
        self.response_block.set()
        self.must_respond_block.wait()
        print(f"Responded to: {self.choice}")
        self.stage_block.set()

    def reinforcement_stage(self):
        """
        Stage 2: Evaluate choice and deliver reinforcement (reward/punishment) and decide respective intertrial interval

        """
        # Clear stage block
        self.stage_block.clear()
        task_args, stimulus_args = self.managers["session"].prepare_reinforcement_stage(self.choice)

        # if stim arg is not empty
        if "LED" in task_args.get("reinforcer_mode", None):
            self.managers["hardware"].flash_led(
                task_args["reinforcer_direction"],
                task_args["duration"],
            )
        if "SCREEN" in task_args.get("reinforcer_mode", None):
            self.msg_to_stimulus.put(("kor_epoch", stimulus_args))
            if task_args.get("duration", None):
                threading.Timer(
                    task_args["duration"],
                    lambda: self.msg_to_stimulus.put(("intertrial_epoch", {})),
                ).start()

        if self.choice == -1:  # left
            self.managers["hardware"].reward_left(task_args["trial_reward"])
            self.managers["session"].total_reward += task_args["trial_reward"]
        elif self.choice == 1:  # right
            self.managers["hardware"].reward_right(task_args["trial_reward"])
            self.managers["session"].total_reward += task_args["trial_reward"]

        if task_args.get("wait_for_consumption", False):
            self.trigger = {
                "type": "MUST_RESPOND",
                "targets": [task_args["reinforcer_direction"]],
                "duration": None,
            }
            self.response_block.set()
        self.stage_block.set()

    def intertrial_stage(self, *args, **kwargs):
        # Clear stage block
        self.stage_block.clear()
        task_args, stimulus_args = {}, {}

        task_args, stimulus_args = self.managers["session"].prepare_intertrial_stage()

        print(f"ITI stage started: {task_args['intertrial_duration']} secs")
        if task_args["intertrial_duration"] > 0:
            # start delay epoch
            if stimulus_args:
                self.msg_to_stimulus.put(("intertrial_epoch", stimulus_args))
            # wait for delay duration then send message to stimulus manager
            threading.Timer(
                task_args["intertrial_duration"],
                self.stage_block.set,
            ).start()
        else:
            self.stage_block.set()
        self.managers["session"].intertrial_onset = datetime.datetime.now() - self.timers["session"]

        if task_args.get("wait_for_consumption", False):
            print("[intertrial_stage] Waiting for must_respond_block")
            self.must_respond_block.wait()

        # reset must_respond_block
        self.must_respond_block.set()
        self.must_respond_block.clear()

        self.stage_block.wait()

        data = self.managers["session"].end_of_trial_updates()
        data["DC_timestamp"] = datetime.datetime.now().isoformat()
        data["trial_stage"] = "intertrial_stage"
        data["TRIAL_END"] = True
        return data


if __name__ == "__main__":
    stage_block = threading.Event()
