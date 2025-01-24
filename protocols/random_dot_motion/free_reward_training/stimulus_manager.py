from protocols.random_dot_motion.core.stimulus.stimulus_manager import StimulusManager as core_StimulusManager
from protocols.random_dot_motion.core.stimulus.random_dot_motion import RandomDotMotion as core_RDK


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


def main():
    import time
    import multiprocessing

    from protocols.random_dot_motion.core.stimulus.random_dot_motion import RandomDotMotion

    import protocols.random_dot_motion.rt_dynamic_training.config as config

    import numpy as np

    in_queue = multiprocessing.Queue()
    out_queue = multiprocessing.Queue()

    a = StimulusManager(
        stimulus=RandomDotMotion,
        stimulus_configuration=config.STIMULUS,
        in_queue=in_queue,
        out_queue=out_queue,
    )
    a.start()

    volumes = [0.2, 0.4, 0.6, 0.8, 1]
    while True:
        vol_idx = np.random.randint(0, 5)
        print("Starting Fixation")
        message = "('fixation_epoch', {})"
        in_queue.put(eval(message))
        time.sleep(2)
        print("Starting Stimulus")
        # message = "('stimulus_epoch', {'seed': 1, 'coherence': 9, 'stimulus_size': (1920, 1280)})"
        message = "('stimulus_epoch', {'seed': 1, 'coherence': 9, 'stimulus_size': (1920, 1280), 'pulse': [(240,9),(243,9)]})"
        # message = "('stimulus_epoch', {'seed': 1, 'coherence': np.sign(np.random.rand() - 0.5)*9, 'stimulus_size': (1920, 1280), 'pulse': [(240,9),(243,9)], 'audio_stim': '8KHz', 'volume':volumes[-1]})"
        in_queue.put(eval(message))
        time.sleep(6)
        print("Starting Reinforcement")
        message = "('reinforcement_epoch', {'outcome': 'correct'})"
        in_queue.put(eval(message))
        time.sleep(2)
        print("Starting Intertrial")
        message = "('intertrial_epoch', {})"
        in_queue.put(eval(message))
        time.sleep(2)
        # print("Loop complete")


if __name__ == "__main__":
    import multiprocessing

    game = multiprocessing.Process(target=main())
    game.start()
