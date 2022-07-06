
from Protocols.RDK.tasks.rt_task import rtTask
import threading
import socket
import datetime
import sys

class RigManager():
    def __init__(self):

        self.task = None

        # Creating events for event lock
        self.stage_block = threading.Event()  # is stage block finished?
        self.quitting = threading.Event()     # Quitting the task?
        self.running = threading.Event()      # Is task running or paused?

        # # Establishing connection
        # self.ip = self.get_ip()
        # self.handshake()

        self.command_start_session()


    # def get_parameters(self, _dict, keys, default=None):
    #     for key in keys:
    #         if isinstance(_dict, odict):
    #             _dict = _dict.get(key, default)
    #         else:
    #             return default
    #     return _dict
    #
    # def set_parameters(self, source, overrides):
    #     """
    #     Update a nested dictionary or similar mapping.
    #     Modify ``source`` in place.
    #     """
    #     for key, value in overrides.items():
    #         if isinstance(value, collections.abc.Mapping) and value:
    #             returned = set_parameters(self, source.get(key, {}), value)
    #             source[key] = returned
    #         else:
    #             source[key] = overrides[key]
    #     return source
    #
    #
    #
    # def test_set_parameters(self):
    #     source = {'hello1': 1}
    #     overrides = {'hello2': 2}
    #     deep_update(source, overrides)
    #     assert source == {'hello1': 1, 'hello2': 2}
    #
    #     source = {'hello': 'to_override'}
    #     overrides = {'hello': 'over'}
    #     deep_update(source, overrides)
    #     assert source == {'hello': 'over'}
    #
    #     source = {'hello': {'value': 'to_override', 'no_change': 1}}
    #     overrides = {'hello': {'value': 'over'}}
    #     deep_update(source, overrides)
    #     assert source == {'hello': {'value': 'over', 'no_change': 1}}
    #
    #     source = {'hello': {'value': 'to_override', 'no_change': 1}}
    #     overrides = {'hello': {'value': {}}}
    #     deep_update(source, overrides)
    #     assert source == {'hello': {'value': {}, 'no_change': 1}}
    #
    #     source = {'hello': {'value': {}, 'no_change': 1}}
    #     overrides = {'hello': {'value': 2}}
    #     deep_update(source, overrides)
    #     assert source == {'hello': {'value': 2, 'no_change': 1}}
    #
    #
    # def get_ip(self):
    #     """
    #     Retrieve IP address of current computer
    #
    #     Returns:
    #         ip: IP address of current computer
    #     """
    #     unwrap00 = [ip for ip in socket.gethostbyname_ex(socket.gethostname())[2] if not ip.startswith("127.")][:1]
    #     unwrap01 = [[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in
    #                  [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]]
    #     unwrap2 = [l for l in (unwrap00, unwrap01) if l][0][0]
    #     return unwrap2
    #
    # def handshake(self):
    #     """
    #     Communicate with main computer to indicate connection established
    #     """
    #     # TODO
    #     pass
    #
    # def command_update_params(self):
    #     pass

    def command_start_session(self):
        task_class = rtTask
        value = {}
        threading.Thread(target=self.run_task, args=(task_class, value)).start()

    def command_stop_session(self):
        self.running.set()
        self.quitting.set()

    def run_task(self, task_class, task_params):
        # Creating task object and setting running event
        self.task = task_class(stage_block=self.stage_block, **task_params)
        self.running.set()

        # while True:
        #     data = next(self.task.stages)()
        #
        #     self.stage_block.wait()
        #
        #     # Has trial ended?
        #     if 'TRIAL_END' in data.keys():
        #         self.running.wait()         # If paused, waiting for running event set?
        #         if self.quitting.is_set():  # is quitting event set?
        #             break                   # Won't quit if the task is paused.
        #
        # self.task.stop()







if __name__ == "__main__":

    a = RigManager()
    a.quitting.wait(timeout=1)
    sys.exit()
