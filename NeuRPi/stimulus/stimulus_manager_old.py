from NeuRPi.stimulus.stimulus_manager import StimWindow


class StimulusManager(StimWindow):

    def __init__(self, configuration=None, courier=None, stimulus=None):
        self.config = configuration
        self.courier = courier
        self.stimulus = stimulus()
        super(StimulusManager, self).__init__(configuration=configuration, courier=courier)

    def initiate_fixation(self, pars):
        raise Warning('initiate_fixation Function Not Implemented')

    def next_frame_fixation(self, pars):
        raise Warning('next_frame_fixation Function Not Implemented')

    def initiate_stimulus(self, pars):
        raise Warning('initiate_stimulus Function Not Implemented')

    def next_frame_stimulus(self, pars):
        raise Warning('next_frame_stimulus Function Not Implemented')

    def initiate_response(self, pars):
        raise Warning('initiate_response Function Not Implemented')

    def next_frame_response(self, pars):
        raise Warning('next_frame_response Function Not Implemented')

    def initiate_reinforcement(self, pars):
        raise Warning('initiate_reinforcement Function Not Implemented')

    def next_frame_reinforcement(self, pars):
        raise Warning('next_frame_reinforcement Function Not Implemented')

    def initiate_must_response(self, pars):
        raise Warning('initiate_must_response Function Not Implemented')

    def next_frame_must_response(self, pars):
        raise Warning('next_frame_must_response Function Not Implemented')

    def initiate_intertrial(self, pars):
        raise Warning('initiate_intertrial Function Not Implemented')

    def next_frame_intertrial(self, pars):
        raise Warning('next_frame_intertrial Function Not Implemented')

