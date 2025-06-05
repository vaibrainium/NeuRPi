from protocols.random_dot_motion.core.stimulus.random_dot_motion import (
    RandomDotMotion as core_RDK,
)
from protocols.random_dot_motion.core.stimulus.stimulus_manager import (
    StimulusManager as core_StimulusManager,
)


class RandomDotMotion(core_RDK):
    """
    Class for managing stimulus structure i.e., shape, size and location of the stimuli

    Inhereting from base random dot kinematogram class and builds upon it with all new required methods
    """

    def __init__(self, stimulus_size=None):
        super(RandomDotMotion, self).__init__(stimulus_size=stimulus_size)


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

    def initiate_kor(self, args):
        self.frame_counter = 0
        args.update(self.initiate_stimulus_config["dots"])
        self.stimulus.new_stimulus(args)
        audio_stim = args.get("audio_stim", None)
        audio_volume = args.get("audio_volume", 1)
        audio_loops = args.get("audio_loops", 0)
        if audio_stim and self.initiate_stimulus_config["audio"][audio_stim]:
            self.play_audio(self.initiate_stimulus_config["audio"][audio_stim], loops=audio_loops, volume=audio_volume)

    def update_kor(self, args=None):
        frame_rate = self.clock.get_fps() or self.frame_rate
        self.stimulus.move_dots(frame_rate=frame_rate)
        self.frame_counter += 1

        func = self.draw_stimulus
        args = {
            "ndots": self.stimulus.nDots,
            "xpos": self.stimulus.x,
            "ypos": self.stimulus.y,
            "radius": [self.stimulus.radius] * self.stimulus.nDots,
            "color": [self.stimulus.color] * self.stimulus.nDots,
        }
        return func, args
