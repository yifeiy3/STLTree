from .Prim import FLPrimitives, SLPrimitives, Primitives
from .DataProcess.signalProcess import Signal
import math 
from .PrimitiveOptProb import FLPrimitiveProblem, SLPrimitiveProblem, primitiveOptimization
from .PrimitiveOptNoSA import findParameterFL, findParameterSL
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
        primitives.append(FLPrimitives('G', dim_idx, dimname, '<=', flparam, math.inf))
        primitives.append(FLPrimitives('G', dim_idx, dimname, '>', flparam, math.inf))
        primitives.append(FLPrimitives('F', dim_idx, dimname, '<=', flparam, math.inf))
        primitives.append(FLPrimitives('F', dim_idx, dimname, '>', flparam, math.inf))
        #We omit GF rules since the wording is not as useful in home IoT setting.
        # primitives.append(SLPrimitives('GF', dim_idx, dimname, '<', slparam, math.inf))
        # primitives.append(SLPrimitives('GF', dim_idx, dimname, '>', slparam, math.inf))
        primitives.append(SLPrimitives('FG', dim_idx, dimname, '<=', slparam, math.inf))
        primitives.append(SLPrimitives('FG', dim_idx, dimname, '>', slparam, math.inf))
    
    return primitives
    
def primOptimizationInit(signal, primitives, Tmax, Steps):
    '''
        optimize with simulated annealing to find the best primitive options,
        then return its corresponding objective function val. (info gain with robustness)
    '''
    timebounds, spacebounds, checkAllState = computeSignalBounds(signal, Steps)
    print(checkAllState)
    for i in range(len(primitives)):
        prim = primitives[i]
        prim_dim = prim.dim 
        continuous = prim.dimname not in signal.classdict.keys() #if it is not a key, then it is a continuous variable, we use robustness measure

        if prim.oper == 'G' or prim.oper == 'F':
            if not checkAllState[prim_dim][0]: #too many states, use simulated annealing instead
                problem = FLPrimitiveProblem(prim, timebounds, spacebounds, signal, Tmax, Steps, userobustness=continuous)
                primitives[i], objfunval = primitiveOptimization(problem, signal, continuous)
                primitives[i].objfunval = objfunval
            else:
                print("Finding parameter assignment through checking all possible states for {0}\
                    prim oper: {1}\
                    prim ineq: {2}".format(prim.dimname, prim.oper, prim.ineq))
                primitives[i], objfunval = findParameterFL(prim, prim_dim, signal, timebounds, spacebounds, continuous)
                primitives[i].objfunval = objfunval
                print("Learned result with parameter: {0}, objective function val: {1}".format(primitives[i].param, primitives[i].objfunval))
        elif prim.oper == 'GF' or prim.oper == 'FG':
            if not checkAllState[prim_dim][0]: #too many states, use simulated annealing instead
                problem = SLPrimitiveProblem(prim, timebounds, spacebounds, signal, Tmax, Steps, userobustness=continuous)
                primitives[i], objfunval = primitiveOptimization(problem, signal, continuous)
                primitives[i].objfunval = objfunval
            else:
                print("Finding parameter assignment through checking all possible states for {0}\
                    prim oper: {1}\
                    prim ineq: {2}".format(prim.dimname, prim.oper, prim.ineq))
                primitives[i], objfunval = findParameterSL(prim, prim_dim, signal, timebounds, spacebounds, continuous)
                primitives[i].objfunval = objfunval
                print("Learned result with parameter: {0}, objective function val: {1}".format(primitives[i].param, primitives[i].objfunval))
        else:
            raise Exception("Invalid primitives")

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

def setBestPrimitive(signal, Tmax, Steps):
    '''
        gets the best primitive to split our dataset, from simulated annealing algorithm.
        @param: Tmax for SA algorithm
        @param Steps for SA algorithm
    '''
    sig_devices = signal.device
    primitives = primInit(sig_devices)
    opt_primitives = primOptimizationInit(signal, primitives, Tmax, Steps)
    return primGetBest(opt_primitives)