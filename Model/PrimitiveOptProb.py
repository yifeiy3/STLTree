from simanneal import Annealer
import math
import numpy as np 
from .IGobj import InfoGain
from .IGobjnr import InfoGainNoRobustness
import random 

class FLPrimitiveProblem(Annealer):
    '''
        for first level primitive: G/F
    '''
    def __init__(self, pinit, timebounds, spacebounds, signal, userobustness=False):
        '''
            @param pinit: initial state of the primitive, when passed in should be an
            primitive object with all parameters being Nan
            @param userobustness: whether we use robustness measure in our objective function
        '''
        initialstate = pinit.param
        lb = np.amin(spacebounds[:, 0])
        ub = np.amax(spacebounds[:, 1])
        if any([math.isnan(x) for x in initialstate]):
            initialstate[0] = timebounds[0] #beginning of timestamp
            initialstate[1] = timebounds[1] #end
            #TODO: see if this would be impacted by our 0-1 discrete variables.
            initialstate[2] = (lb + ub)/2 #"middle" of all possible vals for state
        super().__init__(pinit)
        self.signal = signal 
        self.lb = lb 
        self.ub = ub 
        self.timelb = timebounds[0]
        self.timeub = timebounds[1]
        # self.Tmax = 8000.0
        # self.steps = 10000
        self.Tmax = 800.0
        self.steps = 100
        self.userobustness = userobustness

    def move(self):
        #defines how our algorithm randomly moves.
        try:
            l = random.randrange(self.timelb, self.timeub, self.signal.minintval)
            r = random.randrange(l+1, self.timeub+1, self.signal.minintval)
            c = random.randint(self.lb, self.ub)
            self.state.modifyparam([l, r, c])
        except ValueError:
            print("our data currently looks like this: {0}".format(self.signal.data))
            print("time bound is this: \n {0}".format(self.signal.time))
            raise NotImplementedError

    def energy(self):
        #note: state is our current primitive, computes the objective function
        if self.userobustness:
            return InfoGain(self.state, self.signal)
        else:
            return InfoGainNoRobustness(self.state, self.signal)


class SLPrimitiveProblem(Annealer):
    '''
        for second level primitive: GF/FG
    '''
    def __init__(self, pinit, timebounds, spacebounds, signal, userobustness=False):
        '''
            @param pinit: initial state of the primitive, when passed in should be an
            primitive object with all parameters being Nan
        '''
        initialstate = pinit.param
        lb = np.amin(spacebounds[:, 0])
        ub = np.amax(spacebounds[:, 1])
        if any([math.isnan(x) for x in initialstate]):
            initialstate[0] = timebounds[0] #beginning of timestamp
            initialstate[1] = timebounds[1] #end
            #TODO: see if this would be impacted by our 0-1 discrete variables.
            initialstate[2] = signal.minintval #start with the smallest interval possible
            initialstate[3] = (lb + ub)/2 #"middle" of all possible vals for state
        super().__init__(pinit)
        self.signal = signal 
        self.lb = lb 
        self.ub = ub 
        self.timelb = timebounds[0]
        self.timeub = timebounds[1]
        # self.Tmax = 8000.0
        # self.steps = 10000
        self.Tmax = 800.0
        self.steps = 100
        self.userobustness = userobustness

    def move(self):
        try:
            l = random.randrange(self.timelb, self.timeub, self.signal.minintval)
            r = random.randrange(l+1, self.timeub+1, self.signal.minintval)
            t3 = random.randrange(self.signal.minintval, 10*self.signal.minintval, self.signal.minintval)
            c = random.randint(self.lb, self.ub)
            self.state.modifyparam([l, r, t3, c])
        except ValueError:
            print("our data currently looks like this: {0}".format(self.signal.data))
            print("time bound is this: \n {0}".format(self.signal.time))
            raise NotImplementedError

    def energy(self):
        if self.userobustness:
            return InfoGain(self.state, self.signal)
        else:
            return InfoGainNoRobustness(self.state, self.signal)


def primitiveOptimization(problem):
    '''
        returns (State/our primitive, objective function value)
    '''
    return problem.anneal()