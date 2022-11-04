# import hydra


# class checking():


#     def __init__(self, rand_num):

#         self.get_configuration(path='conf', filename='rdk')
#         self.rand_num = rand_num
#         self.configutation_access()

#         # self.hardware =

#     def get_configuration(self, path=None, filename=None):
#         hydra.initialize(version_base=None, config_path=path)
#         self.config = hydra.compose(filename, overrides=[])

#     def configutation_access(self):
#         print(self.config.pretty())
#         print(self.rand_num)

# if __name__ == "__main__":
#     a = checking(rand_num=20)
#     # configutation_access()


# from pathlib import Path
# from typing import Optional, Union


# class TEMP:
#     def __init__(self, file: Optional[Path] = None):
#         if file:
#             print(file.stem)


# file = Path(".", "data", "models", "biography.py")

# print(file)
# print(Path(file).absolute)
# a = TEMP(file)

import logging

logging.basicConfig(filename="example.log", level=logging.DEBUG)
logging.debug("This message should go to the log file")
logging.info("So should this")
logging.warning("And this, too")
logging.error("And non-ASCII stuff, too, like Øresund and Malmö")
