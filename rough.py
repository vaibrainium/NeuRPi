# import time

# if __name__ == "__main__":

#     from NeuRPi.agents import test_pilot, test_terminal

#     test_pilot.main()
#     # test_terminal.main()
#     pass


class temp:
    def __init__(self) -> None:
        self._name = None

    @property
    def name(self):
        self._name = 2
        return self._name

    def change_name(self):
        self._name = None


a = temp()
print(a.name)
print(a._name)
a.change_name()
print(a.name)
print(a._name)
