from .Prim import FLPrimitives, SLPrimitives, Primitives
from .DataProcess.signalProcess import Signal
import math 
from .PrimitiveOptProb import FLPrimitiveProblem, SLPrimitiveProblem, primitiveOptimization
from .computeSignalBounds import computeSignalBounds
import numpy 

def primInit(num_signal_dim):
    '''
        param: # of devices,
        we would infer at most one rule for each device so we start with empty rules.
    '''
    primitives = []
    flparam = [math.nan, math.nan, math.nan]
    slparam = [math.nan, math.nan, math.nan, math.nan]

    for dim_idx in range(num_signal_dim):
        primitives.append(FLPrimitives('G', dim_idx, '<', flparam, math.nan))
        primitives.append(FLPrimitives('G', dim_idx, '>', flparam, math.nan))
        primitives.append(FLPrimitives('F', dim_idx, '<', flparam, math.nan))
        primitives.append(FLPrimitives('F', dim_idx, '>', flparam, math.nan))
        primitives.append(FLPrimitives('GF', dim_idx, '<', slparam, math.nan))
        primitives.append(FLPrimitives('GF', dim_idx, '>', slparam, math.nan))
        primitives.append(FLPrimitives('FG', dim_idx, '<', slparam, math.nan))
        primitives.append(FLPrimitives('FG', dim_idx, '>', slparam, math.nan))
    
    return primitives
    
def primOptimizationInit(signal, primitives):
    '''
        optimize with simulated annealing to find the best primitive options,
        then return its corresponding objective function val. (info gain with robustness)
    '''
    timebounds, spacebounds = computeSignalBounds(signal)
    for i in range(len(primitives)):
        prim = primitives[i]
        if prim.oper == 'G' or prim.oper == 'F':
            problem = FLPrimitiveProblem(prim, timebounds, spacebounds, signal)
        elif prim.oper == 'GF' or prim.oper == 'FG':
            problem = SLPrimitiveProblem(prim, timebounds, spacebounds, signal)
        else:
            raise Exception("Invalid primitives")
        prim.param, prim.objfunval = primitiveOptimization(problem)
    return primitives

def primGetBest(primitives):
    '''
        return the primitive with the minimum objective function value, use to split tree
    '''
    minimum = math.inf
    minprim = None
    for prim in primitives:
        if prim.objfunval < minimum:
            minprim = prim 
            minimum = prim.objfunval
    return minprim

def setBestPrimitive(signal):
    '''
        gets the best primitive to split our dataset, from simulated annealing algorithm.
    '''
    sig_dim = numpy.shape(signal.device)[0]
    primitives = primInit(sig_dim)
    opt_primitives = primOptimizationInit(signal, primitives)
    return primGetBest(opt_primitives)