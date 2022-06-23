import sys
import os
# getting the name of the directory
# where the this file is present.
current = os.path.dirname(os.path.realpath(__file__))
# Getting the parent directory name
# where the current directory is present.
parent = os.path.dirname(current)
# adding the parent directory to
# the sys.path.
sys.path.append(parent)


from tasks.task import Task
from tasks.behavior import Behavior
import numpy as np
import itertools
import tables
import threading
import typing
from typing import Literal
from collections import OrderedDict as odict
# from pydantic import Field
import datetime
from scipy.stats import pearson3


class DynamicCoherences(Task):
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

    STAGE_NAMES = ["fixation", "stimulus", "reinforcement", "intertrial"]

    # List of needed parameters, returned data and data format
    TASK_PARAMS = odict()

    TASK_PARAMS['stimulus'] = {'_coherences':         {'tag'  : 'List of all coherences used in study',
                                                       'type' : 'list',
                                                       'value': [100, 72, 36, 18, 9, 0]},
                               'coherence_level':     {'tag'  : 'Level of difficulty for current block',
                                                       'type' : 'int',
                                                       'value': 1},
                               'repeats_per_block':   {'tag'  : 'Number of repeats of each coherences per block',
                                                       'type' : 'int',
                                                       'value': 3}
                               }
    TASK_PARAMS['bias'] = {'active_correction': {'tag'            : 'Repeat threshold',
                                                 'type'           : 'int',
                                                 'threshold'      : 100},
                           'passive_correction': {'tag'           : 'Repeat threshold and window',
                                                 'type'           : 'int',
                                                  'threshold'     : 100,
                                                  'rolling_window': 10
                                                  }
                           }
    TASK_PARAMS['timings'] = {'fixation': {'tag'   : 'Mean fixation time in ms',
                                           'type'  : 'int',
                                           'value' : 500},
                              'stimulus': {'tag'   : 'Max stimulus time in ms',
                                           'type'  : 'int',
                                           'value'  : 10000},
                              'intertrial': {'tag' : 'Inter-trial interval in ms',
                                             'type': 'int',
                                             'mean':500}
                              }
    TASK_PARAMS['feedback'] = {'correct': {'visual': {'tag': 'Visual feedback for correct trial',
                                           'type'  : 'tuple'},
                               'audio': {'tag'     : 'Audio feedback for correct trial',
                                         'type'    : 'tuple'},
                               'time': {'tag'      : 'Temporal delay feedback in ms',
                                        'type'     : 'int'}
                             },
                 'incorrect': {'visual': {'tag'    : 'Visual feedback for correct trial',
                                          'type'   : 'tuple'},
                               'audio': {'tag'     : 'Audio feedback for correct trial',
                                         'type'    : 'tuple'},
                               'time': {'tag'      : 'Temporal delay feedback in ms',
                                        'type'     : 'int'}
                               },
                 'noresponse': {'visual': {'tag'   : 'Visual feedback for correct trial',
                                           'type'  : 'tuple'},
                                'audio': {'tag'    : 'Audio feedback for correct trial',
                                          'type'   : 'tuple'},
                                'time': {'tag'     : 'Temporal delay feedback in ms',
                                         'type'    : 'int'}
                                }
                               }
    TASK_PARAMS['training_type'] = {'value': {0:'Passive-Only', 1:'Active-Passive', 2:'Active-Only'},
                                    'active-passive': {'tag'                : 'Parameters for Active-Passive Training',
                                                       'reaction_time_mu'   : 10,
                                                       'reaction_time_sigma':6,
                                                       'reaction_time_max'  : 60}
                                                       }



    EVENT_FILES = {
        'events': 'event_all.txt'
        ''
    }


    class TrialData(tables.IsDescription):
        trial_num = tables.Int32Col()
        target = tables.StringCol(1)
        response = tables.StringCol(1)
        correct = tables.Int32Col()
        correction = tables.Int32Col()
        RQ_timestamp = tables.StringCol(26)
        DC_timestamp = tables.StringCol(26)
        bailed = tables.Int32Col()


    def __init__(self, stage_block=None, rolling_perf=None, **kwargs):

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
            current_trial (int): If starting at nonzero trial number, which?
            stim_light (bool): Should the LED be turned blue while the stimulus is playing?
            **kwargs:
        """
        super(DynamicCoherences, self).__init__()

        # Get configuration for this task -> self.config
        self.get_configuration(path='conf', filename='rdk')
        self.init_hardware()

        # Event locks, triggers
        self.stage_block = stage_block
        self.trigger = {}

        # Initializing managers
        self.trial_manager = TrialManager(DynamicCoherences.TASK_PARAMS)
        self.behavior_manager = Behavior(hardwares=self.hw, trigger=self.trigger, stage_block=self.stage_block)

        # Variable parameters
        self.current_stage = None  # Keeping track of stages so other asynchronous callbacks can execute accordingly
        self.target = None
        self.response = None
        self.bailed = None
        self.correct = None
        self.correction_trial = None

        # We make a list of the variables that need to be reset each trial so it's easier to do so
        self.resetting_variables = [self.stimulus, self.response, self.response_time]

        # This allows us to cycle through the task by just repeatedly calling self.stages.next()
        stage_list = [self.fixation, self.stimulus, self.reinforcement, self.intertrial]
        self.num_stages = len(stage_list)
        self.stages = itertools.cycle(stage_list)



    def fixation(self, *args, **kwargs):
        """
        Stage 0: Fixation time, making sure no trigger is set during fixation times.

        Returns:
            data (dict):
            {

            }
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.current_stage = 0

        # Set triggers, set display and start timer
        self.fixation_time = DynamicCoherences.TASK_PARAMS['timings']['fixation_time']['value']
        self.triggers = {'type': 'NoGO', 'time': self.fixation_time}
        # ''' Send Signal to Display Manager'''
        self.behavior_manager.response_block.set()

        # Get current trial properties
        if not self.correction_trial:
            self.current_trial = next(self.trial_counter)
        self.trial_manager.next_trial(self.correction_trial)

        data = {
            'DC_timestamp': datetime.datetime.now().isoformat(),
            'trial_num': self.current_trial,
        }
        return data


    def stimulus(self, *args, **kwargs):
        """
        Stage 1: Show stimulus and wait for response trigger on target/distractor input

        Returns:
            data (dict):
            {

            }
        """

        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.current_stage = 1

        # Set triggers, set display and start timer
        if DynamicCoherences.TASK_PARAMS['training_type']  < 2:
            self.stimulus_time = DynamicCoherences.TASK_PARAMS['training_type']['active-passive']['reaction_time_mean'] + \
                            (pearson3.rvs(0.6, size=1) * 1.5)
        else:
            self.stimulus_time = DynamicCoherences.TASK_PARAMS['timings']['stimulus_time']['value']
        self.triggers = {'type': 'GO', 'time': self.stimulus_time}
        # ''' Send Signal to Display Manager'''
        self.behavior_manager.response_block.set()
        self.stage_block.wait()
        self.response, self.response_time = self.behavior_manager.response, self.behavior_manager.response_time

        data = {
            'DC_timestamp': datetime.datetime.now().isoformat(),
            'trial_num': self.current_trial,
        }
        return data

    def reinforcement(self, *args, **kwargs):
        """
        Stage 2: Evaluate choice and deliver reinforcement (reward/punishment) and respective intertrial interval

        Returns:
            data (dict):
            {

            }
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.current_stage = 2

        # Checking if trial was correct
        if np.isnan(self.response):    # Invalid Trial
            self.correction_trial = 1
        elif self.stimlus['target'] != self.response:  # Incorrect Trial
            self.correction_trial = 1
        elif self.stimlus['target'] == self.response:  # Correct Trial
            self.correction_trial = 0
            self.correct = 1
            if self.response == -1:     # Left Correct
                pass
            elif self.response == 1:    # Right Correct
                pass


        # Setting intertrial interval in ms
        self.ITI = 1


        data = {
            'DC_timestamp': datetime.datetime.now().isoformat(),
            'trial_num': self.current_trial,
        }
        self.stage_block.set()
        return data

    def intertrial(self, *args, **kwargs):
        """
        Stage 3: Inter-trial Interval.

        Returns:
            data (dict):
            {

            }
        """
        # Clear the event lock -> defaults to event: false
        self.stage_block.clear()
        self.current_stage = 3

        # Setting timer to trigger stage_block event after defined inter-trial interval (self.ITI)
        threading.Timer(self.ITI / 1000., self.stage_block.set).start()

        self.trial_manager.update_EOT()

        data = {
            'DC_timestamp': datetime.datetime.now().isoformat(),
            'trial_num': self.current_trial,
            'TRIAL_END': True
        }
        self.stage_block.set()
        return data




class TrialManager():
    def __init__(self, TASK_PARAMS):
        self.schedule_counter = 0
        self.TASK_PARAMS = TASK_PARAMS
        self.get_full_coherences()

        # Setting session parameters
        self.rolling_bias = np.zeros(self.TASK_PARAMS['bias']['passive_correction']['rolling_window']) # Initializing at no bias
        self.rolling_bias_index = 0


    # RT = np.zeros(len(App['Coherences']));RT[:]=np.NaN
    # psych_Right = np.zeros(len(App['Coherences']));
    # psych_Left = np.zeros(len(App['Coherences']));
    # psych = np.zeros(len(App['Coherences'])) + 0.5;     # chance performance
    # tottrl_X = list(range(len(App['Coherences'])))
    # tottrl_Y = np.zeros(len(App['Coherences']));
    # RT_Y = np.zeros(len(App['Coherences']));
    # Bias = 0      # Initiating for active bias correction at 0
    # rolling_5minTrials = 0
    # rolling_5minTimer = time.time()
    # previous_attempts = 0



    def get_full_coherences(self):
        """
        Generates full direction-wise coherence array from input coherences list.

        Returns:
            full_coherences (list): List of all direction-wise coherences with adjustment for zero coherence (remove duplicates).
            coh_to_xrange (dict): Mapping dictionary from coherence level to corresponding x values for plotting of psychometric function
        """
        coherences = np.array(self.TASK_PARAMS['stimulus']['_coherences']['value'])
        self.full_coherences = sorted(np.concatenate([coherences,-coherences]))
        if 0 in coherences:     # If current full coherence contains zero, then remove one copy to avoid 2x 0 coh trials
            self.full_coherences.remove(0)
        self.coh_to_xrange = {coh: i for i, coh in enumerate(self.full_coherences)}   # mapping active coherences to x values for plotting purposes
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
        coherences = np.array(self.TASK_PARAMS['stimulus']['_coherences']['value'])
        coherence_level = self.TASK_PARAMS['stimulus']['coherence_level']['value']
        repeats_per_block = self.TASK_PARAMS['stimulus']['repeats_per_block']['value']
        active_coherences = sorted(np.concatenate([coherences[:coherence_level], -coherences[:coherence_level]]))    # Signed coherence
        if 0 in active_coherences:
            active_coherences.remove(0)  # Removing one zero from the list
        self.coh_to_xactive = {key: self.coh_to_xrange[key] for key in active_coherences}  # mapping active coherences to active x values for plotting purposes
        self.trials_schedule = active_coherences * repeats_per_block    # Making block of Reps(3) trials per coherence

        # Active bias correction block by having unbiased side appear more
        for _, coh in enumerate(coherences[:coherence_level]):
            if coh > self.TASK_PARAMS['bias']['active_correction']['value']:
                self.trials_schedule.remove(coh*self.rolling_bias)    # Removing high coherence from biased direction (-1:left; 1:right)
                self.trials_schedule.append(-coh*self.rolling_bias)   # Adding high coherence from unbiased direction.

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
        if correction_trial and self.stimulus['coh'] > self.TASK_PARAMS['bias']['passive_correction']['threshold']:
            # Drawing incorrect trial from normal distribution with high prob to direction
            temp_bias = np.sign(np.random.normal(np.mean(self.rolling_Bias), 0.5))
            self.stimulus['coh'] = int(-temp_bias) * np.abs(self.stimulus['coh'])  # Repeat probability to opposite side of bias

        else:
            # Generate new trial schedule if at the end of schedule
            if self.schedule_counter == 0 or self.schedule_counter == len(self.trials_schedule):
                self.graduation_check()
                self.generate_trials_schedule()

            self.stimulus = {'coh': self.trials_schedule[self.schedule_counter] + np.random.choice([-1e-2, 1e-2]), # Adding small randon coherence to distinguish 0.01 vs -0.01 coherence direction
                         'target': np.sign(self.stimulus['coh'])
                         }
            self.schedule_counter += 1  # Incrementing within trial_schedule counter
        # return self.stimulus

    def update_EOT(self):
        """
        Updating end of trial parameters such as psychometric function, chronometric function, total trials, rolling_perf
        bias, rolling_bias
        """

    def graduation_check(self):
        pass




if __name__ == '__main__':
    import numpy as np

    task = DynamicCoherences()


    while True:
        level = input("Enter new coherence level at will")
        if level:
            DynamicCoherences.TASK_PARAMS['stimulus']['coherence_level']['value'] = int(level)

        task.trial_manager.next_trial()



# # Threading timer example
# from threading import Timer, Event
# from time import time
#
# start = time()
# a = Event()
# a.clear()
# def print_hello():
#     print("Hello in print", time() - start)
#
#
# print("Hello First", time() - start)
# Timer(5.0, a.set).start()
# print_hello()
# print("Hello Second", time() - start)
# a.wait()
# print("Hello Last", time() - start)