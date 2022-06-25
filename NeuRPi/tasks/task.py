
from itertools import count
# import tables
import threading
from NeuRPi.hardware.arduino import Arduino
import hydra


# If need be, work on multithreading later

class Task(object):
    """
    Meta Class for task:
    Contains global class variables like PARAMS, HARDWARE, STAGE_NAMES, PLOT across objects.
    Within each object has private class variables.

    Attributes:
        PARAMS: Parameters to define task, such as:

            PARAMS = odict()
            PARAMS['reward']        = {'tag: 'Reward Duration (ms)',
                                        'type': 'int'}
            PARAMS['check_lick']    = {'tag: 'Licked?',
                                        'type': 'bool'}

        HARDWARE (dict): dictionary of hardware necessary for the task

            HARDWARE = {
                'SOLENOID':{
                    'L': hardware.trigger,
                    'R': hardware.trigger, ...
                },
                'LICK':{
                    'L': hardware.threshold_crossed,...
                }
            }

        PLOT (dict): Dictionary of plotting parameters.
            PLOT = {
                'roll_window'   : 50 # number of trials for rollling window of accuracy
                'data': {
                    'target'    : 'left',
                    'response'  : 'left',
                    'correct'   : True
                }
            }

        Trial_Data (class): Data table description:
            class TrialData(tables.IsDescription):
                trial_num             = tables.Int32Col(),
                target                = tables.StringCol(1)
                response              = tables.StringCol(1)
                correct               = tables.Int32Col(),
                valid                 = tables.Int32Col()
                stim_onset_timestamp  = tables.StringCol(26)

        STAGE_NAMES (list): List of stage method names
        stage_block (:class:`threading.Event`): Signal when task stages complete.
        stages (iterator): Some generator or iterator that continuously returns the next stage method of a trial
        triggers (dict): Some mapping of some pin to callback methods
        pins (dict): Dict to store references to hardware
        pin_id (dict): Reverse dictionary, pin numbers back to pin letters.

    """

    # class TrialData(tables.IsDescription): # Basic class for trial data
    #     trial_num = tables.Int32Col()
    #     session = tables.Int32Col()


    def __init__(self, *args, **kwargs):
        """
        Private class variables
        Args:
            subject (str): Subject ID
            reward (int): Amount of reward given on each positive feedback.
        """

        # Task Variables
        self.task_manages = None
        self.subject = kwargs.get('subject', None)
        self.trigger = {}
        self.stage_block = None  # threading.Event used by the pilot to manage stage transitions
        self.stages = None

        self.trial_counter = count(int(kwargs.get('current_trial',0)))
        self.current_trial = int(kwargs.get('current_trial',0))

        self.punish_block = threading.Event()
        self.punish_block.set()

        # Hardware
        self.hardware = {}  # References (ports) to all required hardware
        self.pin_id = {}

        self.trigger_lock = threading.Lock()


    def get_configuration(self, directory=None, filename=None):
        '''
        Getting configuration from respective config.yaml file.

        Arguments:
            directory (str): Path to configuration directory relative to root directory (as Protocols/../...)
            filename (str): Specific file name of the configuration file
        '''
        path = '../../' + directory
        hydra.initialize(version_base=None, config_path=path)
        return hydra.compose(filename, overrides=[])



    def set_reward(self, vol=None, duration=None, port=None):
        """
        Set reward value for each port
        Args:
            vol (float, int): Volume of reward per trigger in uL
            duration (float): Duration to open port in ms
            port (None, Port_ID): If None, set value to all ports in 'PORTS', otherwise only set in 'port'
        """
        if not vol and not duration:
            raise Exception("Did not provide either volume or duration of trigger for each pulse")
        if vol and duration:
            raise Warning("Both volume and duration provided. Using volume")

        if not port:
            for k, port in self.hardware['PORTS'].items():
                if vol:
                    try:
                        port.dur_from_vol(vol)
                    except AttributeError:
                        port.duration = 20.0 # If conversion not provided, setting value to 20 (randomly chosen)
                else:
                    port.duration = float(duration)
        else:
            try:
                if vol:
                    try:
                        self.hardware['PORTS'][port].dur_from_vol(vol)
                    except AttributeError:
                        port.duration = 20.0 # If conversion not provided, setting value to 20 (randomly chosen)
                else:
                    port.duration = float(duration)
            except KeyError:
                raise Exception('Port {} not available'.format(port))



    def end(self):
        """
        Releases all hardware and objects
        """
        for k, v in self.hardware.items():
            for pin, obj in v.items():
                obj.release()

        if hasattr(self, 'stim_manager'):
            if self.stim_manager is not None:
                self.stim_manager.end()
                del self.stim_manager

        del self.hardware
