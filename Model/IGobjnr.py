from .DataProcess.signalProcess import Signal
from .Prim import FLPrimitives, SLPrimitives, Primitives
from .computeRobustness import computeRobustness
from .checkValidPrimitive import checkValidPrimitive
import math 
import numpy as np 

def InfoGainNoRobustness(p, signal):
    '''
        use info gain w/out robustness as our optimizing obj function.
        p: the primitive
        signal: our dataset
    '''
    if not checkValidPrimitive(p, signal):
        return math.inf 
    robdeg = computeRobustness(p, signal)

    (Strue, Sfalse, true_list, false_list) = partitionWeightsNoRobust(robdeg, signal.label, signal.lblclass)
    #want to minimize this, as we are subtracting this term when computing info cost.
    return IG_costNoRobust(Strue, Sfalse, true_list, false_list)

def IG_costNoRobust(Strue, Sfalse, true_list, false_list):
    H_Strue = sum([-x * math.log(x) for x in true_list])
    H_SFalse = sum([-x * math.log(x) for x in false_list])
    return Strue * H_Strue + Sfalse * H_SFalse

def partitionWeightsNoRobust(robdeg, labels, lblclass):
    Strue = robdeg > 0
    Sfalse = robdeg <= 0

    p_Strue = np.sum(Strue)/labels.size if labels.size > 0 else 0
    p_Sfalse = 1 - p_Strue

    #we add a 0.00001 prior so that we would not take log 0
    numclass = len(lblclass)
    p_true_list = [0.00001] * numclass #arbitray default value for when p_true is empty
    for i in range(numclass-1):
        Strue_c1 = (labels[Strue] == lblclass[i])
        if Strue_c1.size > 0:
            p_true_list[i] = max(0.00001, np.sum(Strue_c1)/Strue_c1.size)
    p_true_list[numclass-1] = max(0.00001, 1.0 - sum(p_true_list))

    p_false_list = [0.0001] * numclass
    for i in range(numclass-1):
        Sfalse_c1 = (labels[Sfalse] == lblclass[i])
        if Sfalse_c1.size > 0: 
            p_false_list[i] = max(0.00001, np.sum(Sfalse_c1)/Sfalse_c1.size)
    p_false_list[numclass-1] = max(0.00001, 1.0 - sum(p_false_list))

    return (p_Strue, p_Sfalse, p_true_list, p_false_list)