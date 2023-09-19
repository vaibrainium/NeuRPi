import time
from multiprocessing import Process
import omegaconf
from protocols.random_dot_motion.core.stimulus.display import Display
import logging

 # TODO: Need to work with new config.py system
# CHANGE REINFORCEMENT and TUPLE HANDLING

class StimulusManager(Display):
    """
    Class for stimulus structure within trial.

    Inhereting from `Display` to show stimulus

    Args:
        stimulus: a class of stimulus manager generating and managing stimulus structure i.e., shape, size and location of stimuli
        stimulus_config:

    Methods:
        initiate_fixation - show fixation display
        initiate_stimulus - show stimulus display
        initiate_reinforcement - show reinfocement display
        initiate_intertrial - show intertrial display
    """

    def __init__(
        self, stimulus=None, stimulus_configuration=None, in_queue=None, out_queue=None):
        super(StimulusManager, self).__init__(
            stimulus_configuration=stimulus_configuration,
            in_queue=in_queue,
            out_queue=out_queue,
        )

        self.process = None
  
        if isinstance(stimulus_configuration, omegaconf.dictconfig.DictConfig):
            stimulus_configuration = omegaconf.OmegaConf.to_container(stimulus_configuration, resolve=True)
        self.stimulus_config = stimulus_configuration
        self.stimulus = stimulus(stimulus_size=self.stimulus_config["required_functions"]["value"]["initiate_stimulus"]["stimulus_size"])

        # making sure all required functions are defined and store the arguments as instance variables for each function as f"{func}_config" example "initiate_fixation_config"
        for func, args in self.stimulus_config["required_functions"]["value"].items():
            if not hasattr(self, func):
                raise AttributeError(f"StimulusManager does not have function {func}")
            else:
                setattr(self, f"{func}_config", args)  # Store the arguments as an instance variable

    def start(self):
        """
        Start the stimulus manager process
        """
        self.process = Process(target=self._run, daemon=True)
        self.process.start()

    def initiate_fixation(self, args=None):
        self.screen.fill(self.initiate_fixation_config["background_color"])
        self.update()
        if self.initiate_fixation_config["audio"]:
            self.play_audio(self.initiate_fixation_config["audio"])

    def initiate_stimulus(self, args):
        args.update(self.initiate_stimulus_config["dots"])
        self.stimulus.new_stimulus(args)
        if self.initiate_stimulus_config["audio"]:
            self.play_audio(self.initiate_stimulus_config["audio"])

    def update_stimulus(self, args=None):
        if self.clock.get_fps():
            self.stimulus.move_dots(frame_rate=self.clock.get_fps())
        else:
            self.stimulus.move_dots(frame_rate=self.frame_rate)

        func = self.draw_stimulus
        args = {
            "ndots": self.stimulus.nDots,
            "xpos": self.stimulus.x,
            "ypos": self.stimulus.y,
            "radius": [self.stimulus.radius] * self.stimulus.nDots,
            "color": [self.stimulus.color] * self.stimulus.nDots,
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
        args.update(self.initiate_stimulus_config["dots"])
        self.stimulus.new_stimulus(args)
        func, arg = self.update_stimulus()
        func(arg)
        if self.initiate_reinforcement_config["audio"][args['outcome']]:
            audio_name = self.initiate_reinforcement_config["audio"][args['outcome']]
            self.play_audio(audio_name)

    def update_reinforcement(self, args=None):
        return self.update_stimulus()

    def initiate_delay(self, args=None):
        self.screen.fill(self.initiate_delay_config["background_color"])
        self.update()
    
    def update_delay(self, args=None):
        pass
        
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

    def stop(self):
        """
        Stopping display process
        """
        self.process.kill()


def main():
    import queue
    import multiprocessing
    from omegaconf import OmegaConf

    from protocols.random_dot_motion.core.stimulus.random_dot_motion import RandomDotMotion

    import protocols.random_dot_motion.rt_dynamic_training.config as config


    in_queue = multiprocessing.Queue()
    out_queue = multiprocessing.Queue()

    a = StimulusManager(
        stimulus=RandomDotMotion,
        stimulus_configuration=config.STIMULUS,
        in_queue=in_queue,
        out_queue=out_queue,
    )
    a.start()

    while True:
        print("Starting Fixation")
        message = "('fixation_epoch', {})"
        in_queue.put(eval(message))
        time.sleep(2)
        print("Starting Stimulus")
        message = "('stimulus_epoch', {'seed': 1, 'coherence': 9, 'stimulus_size': (1920, 1280)})"
        in_queue.put(eval(message))
        time.sleep(4)
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
