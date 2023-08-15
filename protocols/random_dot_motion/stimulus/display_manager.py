import time
from multiprocessing import Process
import omegaconf
from protocols.random_dot_motion.stimulus.display import Display
import logging

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
  
        if isinstance(stimulus_configuration, omegaconf.dictconfig.DictConfig):
            stimulus_configuration = omegaconf.OmegaConf.to_container(stimulus_configuration, resolve=True)

        self.stimulus_config = stimulus_configuration
        self.courier_map = stimulus_configuration["courier_handle"]
        self.RDK = stimulus_manager()

        # making sure all required functions are defined and store the arguments as instance variables for each function as f"{func}_config" example "initiate_fixation_config"
        for func, args in self.stimulus_config["required_functions"]["value"].items():
            if not hasattr(self, func):
                raise AttributeError(f"DisplayManager does not have function {func}")
            else:
                setattr(self, f"{func}_config", args)  # Store the arguments as an instance variable
        self.conversion_to_tuple()

    def conversion_to_tuple(self):
        self.initiate_fixation_config["background_color"] = tuple(self.initiate_fixation_config["background_color"])
        self.initiate_stimulus_config["background_color"] = tuple(self.initiate_stimulus_config["background_color"])
        self.initiate_stimulus_config["dots"]["dot_color"] = tuple(self.initiate_stimulus_config["dots"]["dot_color"])
        self.initiate_intertrial_config["background_color"] = tuple(self.initiate_intertrial_config["background_color"])
        
    def play_audio(self, audio_name):
        pass
        # self.pygame.mixer.stop()
        # self.audios[audio_name].play()

    def initiate_fixation(self, args=None):
        self.screen.fill(self.initiate_fixation_config["background_color"])
        self.update()
        if self.initiate_fixation_config["audio"]:
            self.play_audio(self.initiate_fixation_config["audio"])

    def initiate_stimulus(self, args):
        args.update(self.initiate_stimulus_config["dots"])
        self.RDK.new_stimulus(args)
        if self.initiate_stimulus_config["audio"]:
            self.play_audio(self.initiate_stimulus_config["audio"])

    def update_stimulus(self, args=None):
        if self.clock.get_fps():
            self.RDK.move_dots(frame_rate=self.clock.get_fps())
        else:
            self.RDK.move_dots(frame_rate=self.frame_rate)

        func = self.draw_stimulus
        args = {
            "ndots": self.RDK.nDots,
            "xpos": self.RDK.x,
            "ypos": self.RDK.y,
            "radius": [self.RDK.radius] * self.RDK.nDots,
            "color": [self.RDK.color] * self.RDK.nDots,
        }
        return func, args

    def draw_stimulus(self, args):
        self.screen.fill(self.initiate_stimulus_config["background_color"])
        for ind in range(len(args["xpos"])):
            self.pygame.draw.circle(
                self.screen,
                args["color"][ind],
                (args["xpos"][ind], args["ypos"][ind]),
                args["radius"][ind],
            )

    def initiate_reinforcement(self, args):
        if self.initiate_reinforcement_config["audio"]:
            audio_name = self.initiate_reinforcement_config["audio"][args['outcome']]
            self.play_audio(audio_name)

    def update_reinforcement(self, args=None):
        return self.update_stimulus()

    def initiate_must_respond(self, args=None):
        pass

    def update_must_respond(self, args=None):
        return self.update_stimulus()

    def initiate_intertrial(self, args=None):
        self.screen.fill(self.initiate_intertrial_config["background_color"])
        self.update()

    def update_intertrial(self, args=None):
        raise Warning("update_intertrial Function Not Implemented")

    def update_fixation(self, args=None):
        raise Warning("update_fixation Function Not Implemented")

    def initiate_response(self, args=None):
        raise Warning("initiate_response Function Not Implemented")

    def update_response(self, args=None):
        raise Warning("update_response Function Not Implemented")


def main():
    import queue
    from omegaconf import OmegaConf

    from protocols.random_dot_motion.stimulus.random_dot_motion import RandomDotMotion


    config = OmegaConf.load("protocols/random_dot_motion/config/rt_dynamic_training.yaml")

    courier = queue.Queue()
    a = DisplayManager(
        stimulus_manager=RandomDotMotion,
        stimulus_configuration=config.STIMULUS,
        stimulus_courier=courier,
    )
    a.start()

    # print("Starting Stimulus")
    # message = "('stimulus_epoch', {'seed': 1, 'coherence': 100, 'stimulus_size': (1920, 1280)})"
    # courier.put(eval(message))
    
    while True:

        print("Starting Fixation")
        message = "('fixation_epoch', {})"
        courier.put(eval(message))
        time.sleep(2)
        print("Starting Stimulus")
        message = "('stimulus_epoch', {'seed': 1, 'coherence': 100, 'stimulus_size': (1920, 1280)})"
        courier.put(eval(message))
        time.sleep(4)
        # print("Starting Reinforcement")
        # message = "('reinforcement_epoch', {'outcome': 'correct'})"
        # courier.put(eval(message))
        # time.sleep(2)
        # print("Starting Intertrial")
        # message = "('intertrial_epoch', {})"
        # courier.put(eval(message))
        # time.sleep(2)
        # print("Loop complete")


if __name__ == "__main__":
    import multiprocessing
    
    game = multiprocessing.Process(target=main())
    game.start()
