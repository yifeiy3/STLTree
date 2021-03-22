from .Prim import FLPrimitives, SLPrimitives, Primitives
from .DataProcess.signalProcess import Signal
import math 
from .PrimitiveOptProb import FLPrimitiveProblem, SLPrimitiveProblem, primitiveOptimization
from .computeSignalBounds import computeSignalBounds
import numpy 

def primInit(signal_devices):
    '''
        param: devices of label our label col
        we would infer at most one rule for each device so we start with empty rules.
    '''
    primitives = []
    num_signal_dim = numpy.shape(signal_devices)[0]
    flparam = [math.nan, math.nan, math.nan]
    slparam = [math.nan, math.nan, math.nan, math.nan]

    for dim_idx in range(num_signal_dim):
        dimname = signal_devices[dim_idx]
        primitives.append(FLPrimitives('G', dim_idx, dimname, '<', flparam, math.inf))
        primitives.append(FLPrimitives('G', dim_idx, dimname, '>', flparam, math.inf))
        primitives.append(FLPrimitives('F', dim_idx, dimname, '<', flparam, math.inf))
        primitives.append(FLPrimitives('F', dim_idx, dimname, '>', flparam, math.inf))
        #TODO: Is GF needed in learning the rules? The wording kind of odd.
        # primitives.append(SLPrimitives('GF', dim_idx, dimname, '<', slparam, math.inf))
        # primitives.append(SLPrimitives('GF', dim_idx, dimname, '>', slparam, math.inf))
        primitives.append(SLPrimitives('FG', dim_idx, dimname, '<', slparam, math.inf))
        primitives.append(SLPrimitives('FG', dim_idx, dimname, '>', slparam, math.inf))
    
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
        primitives[i], objfunval = primitiveOptimization(problem)
        primitives[i].objfunval = objfunval
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
    if minprim is None:
        print("minimum prim is none, should not happen")
    return minprim

def setBestPrimitive(signal):
    '''
        gets the best primitive to split our dataset, from simulated annealing algorithm.
    '''
    sig_devices = signal.device
    primitives = primInit(sig_devices)
    opt_primitives = primOptimizationInit(signal, primitives)
    return primGetBest(opt_primitives)