import time

from NeuRPi.utils.get_config import get_configuration
from protocols.RDK.stimulus.dynamic_training_rt import Stimulus_Display


def prepare_config():

    # Preparing parameters parameters
    directory = "protocols/RDK/config"
    filename = "stimulus"
    config = get_configuration(directory=directory, filename=filename)
    return config


def main():
    import queue

    config = prepare_config()
    courier = queue.Queue()
    a = Stimulus_Display(
        stimulus_configuration=config.STIMULUS,
        stimulus_courier=courier,
    )

    while True:
        print("Starting Fixation")
        message = "('initiate_fixation', {})"
        courier.put(eval(message))
        time.sleep(2)
        print("Starting Stimulus")
        message = "('initiate_stimulus', {'seed': 1, 'coherence': 100, 'stimulus_size': (1920, 1280)})"
        courier.put(eval(message))
        time.sleep(5)
        print("Starting Intertrial")
        message = "('initiate_intertrial', {})"
        courier.put(eval(message))
        time.sleep(2)
        print("Loop complete")


if __name__ == "__main__":
    import multiprocessing

    display = multiprocessing.Process(target=main, args=())
    display.start()
