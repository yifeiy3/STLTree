import numpy as np 
import math
import copy
from .IGobjnr import InfoGainNoRobustness

def findParameterFL(prim, dimension, signal, timebounds, spacebounds):
    '''
        Simply iterating through all possible parameter assignments to find the
        one with the most info gain.
    '''
    timemin, timemax = timebounds[0], timebounds[1]
    spacemin, spacemax = int(spacebounds[dimension, 0]), int(spacebounds[dimension, 1])
    bestPrim = copy.deepcopy(prim)
    bestObjval = math.inf

    for i in range(timemin, timemax+1):
        for j in range(i+1, timemax+1):
            for k in range(spacemin, spacemax+1):
                prim.modifyparam([i, j, k])
                objval = InfoGainNoRobustness(prim, signal)
                if objval < bestObjval:
                    bestObjval = objval
                    bestPrim = copy.deepcopy(prim)
    
    return bestPrim, bestObjval

def findParameterSL(prim, dimension, signal, timebounds, spacebounds):
    timemin, timemax = timebounds[0], timebounds[1]
    spacemin, spacemax = int(spacebounds[dimension, 0]), int(spacebounds[dimension, 1])
    bestPrim = copy.deepcopy(prim)
    bestObjval = math.inf

    for i in range(timemin, timemax+1):
        for j in range(i+1, timemax+1):
            for l in range(1, timemax-j+1):
                for k in range(spacemin, spacemax+1):
                    prim.modifyparam([i, j, l, k])
                    objval = InfoGainNoRobustness(prim, signal)
                    if objval < bestObjval:
                        bestObjval = objval
                        bestPrim = copy.deepcopy(prim)
    
    return bestPrim, bestObjval