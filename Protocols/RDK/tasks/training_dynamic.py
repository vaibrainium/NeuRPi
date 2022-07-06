import numpy as np


class TrainingDynamic():
    def __init__(self, TASK_PARAMS):
        self.rolling_Bias = None
        self.coh_to_xactive = None
        self.coh_to_xrange = None
        self.trials_schedule = None
        self.full_coherences = None
        self.schedule_counter = 0
        self.task_pars = TASK_PARAMS
        self.get_full_coherences()

        # Setting session parameters
        self.rolling_bias = np.zeros(self.task_pars.bias.passive_correction.rolling_window)  # Initializing at no bias
        self.rolling_bias_index = 0
        self.stimulus_pars = {}

    def get_full_coherences(self):
        """
        Generates full direction-wise coherence array from input coherences list.
        Returns:
            full_coherences (list): List of all direction-wise coherences with adjustment for zero coherence (remove duplicates).
            coh_to_xrange (dict): Mapping dictionary from coherence level to corresponding x values for plotting of psychometric function
        """
        coherences = np.array(self.task_pars.stimulus._coherences.value)
        self.full_coherences = sorted(np.concatenate([coherences, -coherences]))
        if 0 in coherences:  # If current full coherence contains zero, then remove one copy to avoid 2x 0 coh trials
            self.full_coherences.remove(0)
        self.coh_to_xrange = {coh: i for i, coh in enumerate(
            self.full_coherences)}  # mapping active coherences to x values for plotting purposes
        return self.full_coherences, self.coh_to_xrange

    def generate_trials_schedule(self, *args, **kwargs):
        """
        Generating a block of trial to maintain psudo-random coherence selection with asserting all coherences are shown
        equally.
        Arguments:
        Returns:
            trials_scheduled (list): Schedule for next #(level*repeats) trials with psudo-random shuffling.
            coh_to_xactive (dict): Mapping dictionary from coherence to active x index value for plotting
        """
        # Resetting within trial_schedule counter
        self.schedule_counter = 0

        # Generate array of active signed-coherences based on current coherence level
        coherences = np.array(self.task_pars.stimulus._coherences.value)
        coherence_level = self.task_pars.stimulus.coherence_level.value
        repeats_per_block = self.task_pars.stimulus.repeats_per_block.value
        active_coherences = sorted(
            np.concatenate([coherences[:coherence_level], -coherences[:coherence_level]]))  # Signed coherence
        if 0 in active_coherences:
            active_coherences.remove(0)  # Removing one zero from the list
        self.coh_to_xactive = {key: self.coh_to_xrange[key] for key in
                               active_coherences}  # mapping active coherences to active x values for plotting purposes
        self.trials_schedule = active_coherences * repeats_per_block  # Making block of Reps(3) trials per coherence

        # Active bias correction block by having unbiased side appear more
        for _, coh in enumerate(coherences[:coherence_level]):
            if coh > self.task_pars.bias.active_correction.threshold:
                self.trials_schedule.remove(
                    coh * self.rolling_bias)  # Removing high coherence from biased direction (-1:left; 1:right)
                self.trials_schedule.append(-coh * self.rolling_bias)  # Adding high coherence from unbiased direction.

        np.random.shuffle(self.trials_schedule)
        return self.trials_schedule, self.coh_to_xactive

    def next_trial(self, correction_trial):
        """
        Generate next trial based on trials_schedule. If not correction trial, increament trial index by one.
        If correction trial (passive/soft bias correction), choose next trial as probability to unbiased direction based on rolling bias.
        Arguments:
            correction_trial (bool): Is this a correction trial?
            rolling_bias (int): Rolling bias on last #x trials.
                                Below 0.5 means left bias, above 0.5 mean right bias
        """

        # If correction trial and above passive correction threshold
        if correction_trial:
            if self.stimulus_pars['coherence'] > self.task_pars.bias.passive_correction.threshold:
                # Drawing incorrect trial from normal distribution with high prob to direction
                self.rolling_Bias = 0.5
                temp_bias = np.sign(np.random.normal(np.mean(self.rolling_Bias), 0.5))
                self.stimulus_pars['coherence'] = int(-temp_bias) * np.abs(
                    self.stimulus_pars['coherence'])  # Repeat probability to opposite side of bias

        else:
            # Generate new trial schedule if at the end of schedule
            if self.schedule_counter == 0 or self.schedule_counter == len(self.trials_schedule):
                self.graduation_check()
                self.generate_trials_schedule()
            # Adding small random coherence to distinguish 0.01 vs -0.01 coherence direction
            self.stimulus_pars = {'coherence': self.trials_schedule[self.schedule_counter] + np.random.choice([-1e-2, 1e-2])}
            self.stimulus_pars['target'] = np.sign(self.stimulus_pars['coherence'])
            self.schedule_counter += 1  # Incrementing within trial_schedule counter
        return self.stimulus_pars

    def update_EOT(self):
        """
        Updating end of trial parameters such as psychometric function, chronometric function, total trials, rolling_perf
        bias, rolling_bias
        """

    def graduation_check(self):
        pass