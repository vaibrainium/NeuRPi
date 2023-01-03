from NeuRPi.tasks.trial_construct import TrialConstruct
from protocols.RDK.stimulus.display_manager import DisplayManager as BaseDisplayManager
from protocols.RDK.stimulus.random_dot_kinematogram import (
    RandomDotKinematogram as BaseRDKManager,
)
from protocols.RDK.tasks.rt_task import RTTask


class RDKManager(BaseRDKManager):
    """
    Class for managing stimulus structure i.e., shape, size and location of the stimuli

    Inhereting from base random dot kinematogram class and builds upon it with all new required methods
    """

    def __init__(self):
        super(RDKManager, self).__init__()
        pass


class DisplayManager(BaseDisplayManager):
    """
    Class for managing stimulus display
    """

    def __init__(self):
        super(DisplayManager, self).__init__()
        pass


class SessionManager:
    """
    Class for managing session structure i.e., trial sequence, graduation, and session level summary.
    """


class TrialRoutine(SessionManager):
    """
    Class for running trial structure i.e., how each trial should progress given `SessionManager`. Here we will run reaction time task.

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
        task_pars=None,
        session_manager=None,
        stimulus_queue=None,
        stage_block=None,
        **kwargs
    ) -> None:
        super().__init__()


def main():
    import NeuRPi
    from NeuRPi.utils.get_config import get_config

    directory = "RDK/config"
    filename = "dynamic_coherences.yaml"
    pars = get_configuration(directory=directory, filename=filename)


if __name__ == "__main__":
    # a = StimulusManager
    # print(a)
    main()
