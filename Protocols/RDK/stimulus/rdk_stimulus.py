from NeuRPi.stimulus.stim_window import StimWindow
import threading


class RDKStimulus(StimWindow):
    def __init__(self, configuration=None, courier=None):
        self.config = configuration
        self.courier = courier
        super(RDKStimulus, self).__init__(configuration=configuration, courier=courier)

        self.run()
    def run(self):
        self.courier_map = self.stim_config.courier_handle
        while True:
            self.stim_block.wait()
            self.stim_block.clear()

            properties = self.courier_map.get(self.message)
            function = eval('self.' + properties.function)

    def stimulus(self):
        Dots.next_frame()
        for dot in range(Dots.nDots):
            pygame.draw.circle(screen, Dots.color, (int(Dots.x[dot]), int(Dots.y[dot])), Dots.radius)

        fps = font.render(str(int(fpsClock.get_fps())), True, pygame.Color('white'))
        



            # function(is_static=properties.is_static)
