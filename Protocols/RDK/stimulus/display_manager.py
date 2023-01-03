import time
from multiprocessing import Process

from protocols.RDK.stimulus.display import Display


class DisplayManager(Display):
    """
    Class for stimulus structure within trial.

    Inhereting from `Display` to show stimulus

    Args:
        stimulus_manager: a class of stimulus manager generating and managing stimulus structure i.e., shape, size and location of stimuli
        stimulus_config:

    Methods:
        initiate_fixation - show fixation display
        initiate_stimulus - show stimulus display
        initiate_reinforcement - show reinfocement display
        initiate_intertrial - show intertrial display
    """

    def __init__(
        self, stimulus_manager=None, stimulus_configuration=None, stimulus_courier=None
    ):
        super(DisplayManager, self).__init__(
            stimulus_configuration,
            stimulus_courier,
        )

        self.courier_map = stimulus_configuration.courier_handle
        self.RDK = stimulus_manager()  # RandomDotKinematogram()

    def initiate_fixation(self):
        if self.courier_map.initiate_fixation.visual.need_update:
            self.screen[0].fill(
                eval(
                    self.courier_map.initiate_fixation.visual.properties.generate.background
                )
            )
            self.update()
        if self.courier_map.initiate_fixation.audio.need_update:
            self.pygame.mixer.stop()
            if self.courier_map.initiate_fixation.audio.is_static:
                self.audio["initiate_fixation"][0].play(
                    self.courier_map.initiate_fixation.audio.is_static - 1
                )

    def initiate_stimulus(self, pars):
        pars["stimulus_size"] = eval(
            self.courier_map.initiate_stimulus.visual.properties.generate.stimulus_size
        )
        print("New Stimulus Initiated")
        self.RDK.new_stimulus(pars)

    def next_frame_stimulus(self):
        if self.clock.get_fps():
            self.RDK.move_dots(frame_rate=self.clock.get_fps())
        else:
            self.RDK.move_dots(frame_rate=self.frame_rate)

        func = self.draw_stimulus
        pars = {
            "ndots": self.RDK.nDots,
            "xpos": self.RDK.x,
            "ypos": self.RDK.y,
            "radius": [self.RDK.radius] * self.RDK.nDots,
            "color": [self.RDK.color] * self.RDK.nDots,
        }
        screen = 0
        return func, pars, screen

    def draw_stimulus(self, pars, screen):
        self.screen[screen].fill(
            eval(
                self.courier_map.initiate_stimulus.visual.properties.generate.background
            )
        )
        for ind in range(len(pars["xpos"])):
            self.pygame.draw.circle(
                self.screen[screen],
                pars["color"][ind],
                (pars["xpos"][ind], pars["ypos"][ind]),
                pars["radius"][ind],
            )

    def initiate_reinforcement(self, pars):
        if self.courier_map.initiate_stimulus.audio.need_update:
            if (
                pars["outcome"] == "Correct"
                and self.courier_map.initiate_stimulus.audio.properties.load.correct
            ):
                try:
                    self.audio["correct"].play()
                except:
                    raise Warning("correct audio path not set")
            if (
                pars["outcome"] == "incorrect"
                and self.courier_map.initiate_stimulus.audio.properties.load.incorrect
            ):
                try:
                    self.audio["incorrect"].play()
                except:
                    raise Warning("incorrect audio path not set")
            if (
                pars["outcome"] == "invalid"
                and self.courier_map.initiate_stimulus.audio.properties.load.correct.invalid
            ):
                try:
                    self.audio["invalid"].play()
                except:
                    raise Warning("invalid audio path not set")

    def next_frame_reinforcement(self):
        return self.next_frame_stimulus()

    def initiate_must_respond(self):
        pass

    def next_frame_must_respond(self):
        return self.next_frame_stimulus()

    def initiate_intertrial(self):
        if self.courier_map.initiate_intertrial.visual.need_update:
            self.screen[0].fill(
                eval(
                    self.courier_map.initiate_intertrial.visual.properties.generate.background
                )
            )
            self.update()
        if self.courier_map.initiate_intertrial.audio.need_update:
            self.pygame.mixer.stop()
            if self.courier_map.initiate_intertrial.audio.is_static:
                self.audio["initiate_fixation"].play(
                    self.courier_map.initiate_intertrial.audio.is_static - 1
                )

    def next_frame_intertrial(self, pars):
        raise Warning("next_frame_intertrial Function Not Implemented")

    def next_frame_fixation(self, pars):
        raise Warning("next_frame_fixation Function Not Implemented")

    def initiate_response(self, pars):
        raise Warning("initiate_response Function Not Implemented")

    def next_frame_response(self, pars):
        raise Warning("next_frame_response Function Not Implemented")


def main():
    import queue

    import hydra

    path = "../../../Protocols/RDK/config"
    filename = "dynamic_coherences"
    hydra.initialize(version_base=None, config_path=path)
    config = hydra.compose(filename, overrides=[])

    courier = queue.Queue()
    a = DisplayManager(stimulus_configuration=config.STIMULUS, stimulus_courier=courier)
    while True:
        print("Starting Fixation")
        message = "('initiate_fixation', {})"
        courier.put(eval(message))
        time.sleep(2)
        print("Starting Stimulus")
        message = "('initiate_stimulus', {'seed': 1, 'coherence': 100, 'stimulus_size': (1920, 1280)})"
        courier.put(eval(message))
        time.sleep(2)
        print("Starting Intertrial")
        message = "('initiate_intertrial', {})"
        courier.put(eval(message))
        time.sleep(2)
        print("Loop complete")


if __name__ == "__main__":
    main()
