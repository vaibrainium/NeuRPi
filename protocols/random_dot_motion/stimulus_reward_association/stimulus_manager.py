from protocols.random_dot_motion.core.stimulus.stimulus_manager import (
    StimulusManager as core_StimulusManager,
)
from protocols.random_dot_motion.core.stimulus.random_dot_motion import (
    RandomDotMotion as core_RDK,
)


class RandomDotMotion(core_RDK):
    """
    Class for managing stimulus structure i.e., shape, size and location of the stimuli

    Inhereting from base random dot kinematogram class and builds upon it with all new required methods
    """

    def __init__(self, stimulus_size=None):
        super(RandomDotMotion, self).__init__(stimulus_size=stimulus_size)
        pass


class StimulusManager(core_StimulusManager):
    """
    Class for diplaying stimulus

    Inhereting from base :class: `DisplayManager`
    """

    def __init__(
        self,
        stimulus=RandomDotMotion,
        stimulus_configuration=None,
        in_queue=None,
        out_queue=None,
    ):
        super().__init__(stimulus, stimulus_configuration, in_queue=in_queue, out_queue=out_queue)
