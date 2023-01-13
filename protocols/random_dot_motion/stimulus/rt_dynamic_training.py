from protocols.random_dot_motion.stimulus.display_manager import (
    DisplayManager as BaseDisplayManager,
)
from protocols.random_dot_motion.stimulus.random_dot_motion import (
    RandomDotMotion as BaseRDK,
)


class RandomDotMotion(BaseRDK):
    """
    Class for managing stimulus structure i.e., shape, size and location of the stimuli

    Inhereting from base random dot kinematogram class and builds upon it with all new required methods
    """

    def __init__(self):
        super(RandomDotMotion, self).__init__()
        pass


class Stimulus_Display(BaseDisplayManager):
    """
    Class for diplaying stimulus

    Inhereting from base :class: `DisplayManager`
    """

    def __init__(
        self,
        stimulus_manager=RandomDotMotion,
        stimulus_configuration=None,
        stimulus_courier=None,
    ):
        super().__init__(stimulus_manager, stimulus_configuration, stimulus_courier)
        pass
