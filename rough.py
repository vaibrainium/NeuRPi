import hydra



class checking():


    def __init__(self, rand_num):

        self.get_configuration(path='conf', filename='rdk')
        self.rand_num = rand_num
        self.configutation_access()

        # self.hardware =

    def get_configuration(self, path=None, filename=None):
        hydra.initialize(version_base=None, config_path=path)
        self.config = hydra.compose(filename, overrides=[])

    def configutation_access(self):
        print(self.config.pretty())
        print(self.rand_num)




if __name__ == '__main__':
    a = checking(rand_num=20)
    #configutation_access()
