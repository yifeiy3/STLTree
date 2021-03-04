from .Prim import FLPrimitives, SLPrimitives, Primitives
from .DataProcess.signalProcess import Signal
from .computeRobustness import computeRobustness

def primitiveCheckSat(prim, signal):
    '''
        for a list of signal, check whether each satisfies our primitive
    '''
    robdeg = computeRobustness(prim, signal)
    return robdeg, (robdeg > 0)