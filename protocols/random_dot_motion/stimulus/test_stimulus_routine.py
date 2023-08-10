from NeuRPi.hardware.display_manager import DisplayManager
from protocols.random_dot_motion.stimulus.random_dot_motion import RandomDotMotion as baseRDK
import multiprocessing as mp
from omegaconf import OmegaConf
import numpy as np


class RandomDotMotion(baseRDK):
    def __init__(self):
        super().__init__()
        pass


class StimulusManager(DisplayManager):

    def __init__(self, stimulus_config=None, in_queue=None, out_queue=None, epoch_update_event=None, stop_event=None):
        super().__init__(stimulus_config=stimulus_config, in_queue=in_queue, out_queue=out_queue, epoch_update_event=epoch_update_event, stop_event=stop_event)

        self.stimulus_manager = RandomDotMotion()
        self.stimulus_config = stimulus_config

        # making sure all required functions are defined and store the arguments as instance variables for each function as f"{func}_config" example "initiate_fixation_config"
        for func, args in self.stimulus_config.required_functions.value.items():
            if not hasattr(self, func):
                raise AttributeError(f"DisplayManager does not have function {func}")
            else:
                setattr(self, f"{func}_config", args)  # Store the arguments as an instance variable
                
    ### Defining required functions
    def initiate_fixation(self, args=None, surface=None):
        surface.fill(self.initiate_fixation_config.background_color)
        if self.initiate_fixation_config.audio:
            self.pygame.mixer.stop()
            self.audios[self.initiate_fixation_config.audio].play()
        return surface
    
    def initiate_stimulus(self, args=None, surface=None):
        dot_pars = self.initiate_stimulus_config.dots
        self.stimulus_manager.new_stimulus(**dot_pars, **(args or {}))
        surface = self.draw_stimulus(args=args, surface=surface)
        if self.initiate_stimulus_config.audio:
            self.pygame.mixer.stop()
            self.audios[self.initiate_stimulus_config.audio].play()
        return surface

    def update_stimulus(self, args=None, surface=None):
        if self.clock.get_fps():
            self.stimulus_manager.move_dots(frame_rate=self.clock.get_fps())
        surface = self.draw_stimulus(args=args, surface=surface)
        return surface
    
    def initiate_reinforcement(self, args=None, surface=None):
        self.update_stimulus(args=args, surface=surface)
        if self.initiate_reinforcement_config.audio:
            self.pygame.mixer.stop()
            audio_name = getattr(self.initiate_reinforcement_config.audio, args['outcome'])
            self.audios[audio_name].play()
        return surface
    
    def update_reinforcement(self, args=None, surface=None): 
        self.update_stimulus(args=args, surface=surface)
        return surface
    
    def initiate_must_respond(self, args=None, surface=None): 
        self.update_stimulus(args=args, surface=surface)
        return surface

    def update_must_respond(self, args=None, surface=None): 
        self.update_stimulus(args=args, surface=surface)
        return surface

    def initiate_intertrial(self, args=None, surface=None):
        surface.fill(self.initiate_intertrial_config.background_color)
        return surface

    def draw_stimulus(self, args=None, surface=None):
        surface.fill(self.initiate_stimulus_config.background_color)
        #TODO: Modify code to draw stimulus faster or make frame queue as as queue of surfaces
        
        # for idx in range(self.stimulus_manager.nDots):
        #     self.pygame.draw.circle(
        #         surface,
        #         self.stimulus_manager.color,
        #         (self.stimulus_manager.x[idx], self.stimulus_manager.y[idx]),
        #         self.stimulus_manager.radius,
        #     )
        return surface

def separate_process_test_function(stimulus_config, in_queue, out_queue, epoch_update_event, stop_event):
    stim = StimulusManager(stimulus_config=stimulus_config, in_queue=in_queue, out_queue=out_queue, epoch_update_event=epoch_update_event, stop_event=stop_event)
    stim.connect()
    stim.load_media()
    stim.start()

    # stim.screen['Primary'].fill((255, 255, 255))
    # stim.pygame.display.update()

if __name__ == "__main__":
    from omegaconf import OmegaConf
    import multiprocessing as mp
    import time

    config = OmegaConf.load("protocols/random_dot_motion/config/rt_dynamic_training.yaml")
    stimulus_config = config.STIMULUS
    in_queue = mp.Queue()
    out_queue = mp.Queue()
    epoch_update_event = mp.Event()
    stop_event = mp.Event()

    stim_process = mp.Process(target=separate_process_test_function, args=(stimulus_config, in_queue, out_queue, epoch_update_event, stop_event), daemon=True)
    stim_process.start()

    while True:
        if not out_queue.empty():
            print(out_queue.get())
            break
    
    time.sleep(1)

    # in_queue.put(("intertrial_epoch", None))
    in_queue.put(("stimulus_epoch", {'coherence':100}))
    epoch_update_event.set()

    while True:
        pass

    # while True:
    #     print("Starting Fixation")
    #     in_queue.put(("fixation_epoch", None))
    #     epoch_update_event.set()
    #     time.sleep(2)

    #     print("Starting Stimulus")
    #     in_queue.put(("stimulus_epoch", {'coherence':100}))
    #     epoch_update_event.set()
    #     time.sleep(2)

    #     print("Starting Reinforcement")
    #     in_queue.put(("reinforcement_epoch", {'outcome': 'correct'}))
    #     epoch_update_event.set()
    #     time.sleep(2)

    #     print("Starting Must Respond")
    #     in_queue.put(("must_respond_epoch", None))
    #     epoch_update_event.set()
    #     time.sleep(2)

    #     print("Starting Intertrial")
    #     in_queue.put(("intertrial_epoch", None))
    #     epoch_update_event.set()
    #     time.sleep(2)
