import numpy as np

class RandomDotKinematogram(object):
    def __init__(self):
        self.stimulus_size = (None, None)
        self.radius = 10
        self.color = (255, 255, 255)
        self.vel = 300
        self.lifetime = 60
        self.nDots = []
        self.fill = 15
        self.x = []
        self.y = []
        self.age = []
        self.theta = []
        self.randTheta = [0,45,90,135,180,225,270,315,360]
        self.coherence = None
        self.cohDots = []
        self.noncohDots = []
        self.Xpath = np.array([])
        self.Ypath = np.array([])

        self.rdk_generator = np.random.RandomState()     # Creating separate random number generator -> rdk_generator

    def update_lifetime(self, pars):
        self.lifetime = pars['lifetime']

    def new_stimulus(self, pars):
        if 'seed' in pars:
            self.rdk_generator.seed(pars['seed'])
        self.coherence = pars['coherence']
        self.stimulus_size = pars['stimulus_size']
        self.nDots = round((self.fill/100) * self.stimulus_size[0] * self.stimulus_size[1] / (np.pi * self.radius ** 2))
        self.x = self.rdk_generator.randint(self.stimulus_size[0],size=self.nDots)
        self.y = self.rdk_generator.randint(self.stimulus_size[1],size=self.nDots)
        self.age = self.rdk_generator.randint(self.lifetime, size=self.nDots)
        self.theta = self.rdk_generator.randint(360, size=self.nDots)                 # Non coherent dots in all direction of 360 degrees
        # self.theta = self.rdk_generator.choice(self.randTheta, size=self.nDots)     # Non coherent dots in one of 8 direction separated by 45 degrees
        self.cohDots = list(range(round(np.abs(self.coherence) * self.nDots / 100)))
        if not self.cohDots: self.noncohDots = list(range(self.nDots))        # If cohDots are empty all dots are non-coherent
        else: self.noncohDots = list(range(self.cohDots[-1]+1, self.nDots))
        self.theta[self.cohDots] = np.sign(pars['coherence'])*90

    def move_dots(self, frame_rate):
        self.x[self.age == self.lifetime] = self.rdk_generator.randint(self.stimulus_size[0],size=np.count_nonzero(self.age == self.lifetime))
        self.y[self.age == self.lifetime] = self.rdk_generator.randint(self.stimulus_size[1],size=np.count_nonzero(self.age == self.lifetime))
        self.age[self.age == self.lifetime] = 0
        # Accounting for boundaries
        self.x[self.x >= self.stimulus_size[0]] = 0
        self.x[self.x < 0] = self.stimulus_size[0]
        self.y[self.y >= self.stimulus_size[1]] = 0
        self.y[self.y < 0] = self.stimulus_size[1]

        # Moving dots one step a time
        self.x = self.x + int(self.vel/frame_rate)*np.sin(np.deg2rad(self.theta))
        self.y = self.y + int(self.vel/frame_rate)*np.cos(np.deg2rad(self.theta))
        self.age += 1

    # def update_burst(self, burstCoherence):
    #     # Congruent burst - high coherence
    #     if (np.sign(burstCoherence) == np.sign(self.coherence)) and (np.abs(burstCoherence) > np.abs(self.coherence)):
    #         Nchangedots = round(self.nDots*(np.abs(burstCoherence - self.coherence))/100)
    #         changeDots = list(self.noncohDots[0:Nchangedots])
    #         self.theta[changeDots] = np.sign(burstCoherence) * 90
    #         # updating properties
    #         self.coherence = burstCoherence
    #         self.cohDots = list(set(self.cohDots) | set(changeDots))    # Combining unique elements from two lists
    #         self.noncohDots = [i for i in self.noncohDots if i not in changeDots]
    #
    #     # Congruent burst - low coherence
    #     elif (np.sign(burstCoherence) == np.sign(self.coherence)) and (np.abs(burstCoherence) < np.abs(self.coherence)):
    #         Nchangedots = int(self.nDots*(np.abs(burstCoherence - self.coherence))/100)
    #         changeDots = list(self.cohDots[0:Nchangedots])
    #         self.theta[changeDots] = self.rdk_generator.randint(360, size=Nchangedots)
    #         # self.theta[changeDots] = self.rdk_generator.choice(self.randTheta, size=Nchangedots)
    #         # updating properties
    #         self.coherence = burstCoherence
    #         self.cohDots = [i for i in self.cohDots if i not in changeDots]
    #         self.noncohDots = list(set(self.noncohDots) | set(changeDots))    # Combining unique elements from two lists
    #
    #     # Inongruent burst - high coherence
    #     elif (np.sign(burstCoherence) != np.sign(self.coherence)) and (np.abs(burstCoherence) > np.abs(self.coherence)):
    #         Nchangedots = int(self.nDots * (np.abs(burstCoherence)) / 100)
    #         if Nchangedots > np.shape(self.cohDots)[0]:
    #             changeDots = self.cohDots + list(self.noncohDots[0:(Nchangedots-np.shape(self.cohDots)[0])])
    #         self.theta[changeDots] = np.sign(burstCoherence) * 90  # changing direction of coh+few noncoh dots
    #         # updating properties
    #         self.coherence = burstCoherence
    #         self.noncohDots = [i for i in self.noncohDots if i not in changeDots]
    #         self.cohDots = list(set(self.cohDots) | set(changeDots))    # Combining unique elements from two lists
    #
    #     # Incongruent burst - low coherence
    #     elif (np.sign(burstCoherence) != np.sign(self.coherence)) and (np.abs(burstCoherence) <= np.abs(self.coherence)):
    #         Nchangedots = int(self.nDots*(np.abs(burstCoherence))/100)
    #         if Nchangedots <= np.shape(self.cohDots)[0]:
    #             changeDots = list(self.cohDots[0:Nchangedots])
    #         self.theta[changeDots] = np.sign(burstCoherence)*90      # changing direction of few coh dots
    #         self.theta[[i for i in self.cohDots if i not in changeDots]] = self.rdk_generator.randint(360, size=np.shape(self.cohDots)[0]-Nchangedots)   # making remaining coh dots random
    #         # self.theta[[i for i in self.cohDots if i not in changeDots]] = self.rdk_generator.choice(self.randTheta, size=np.shape(self.cohDots)[0] - Nchangedots)  # making remaining coh dots random
    #         # updating properties
    #         self.coherence = burstCoherence
    #         self.noncohDots = self.noncohDots + [i for i in self.cohDots if i not in changeDots]
    #         self.cohDots = changeDots #list(set(self.cohDots) | set(changeDots))    # Combining unique elements from two lists