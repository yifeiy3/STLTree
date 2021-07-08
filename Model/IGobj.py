from .DataProcess.signalProcess import Signal
from .Prim import FLPrimitives, SLPrimitives, Primitives
from .computeRobustness import computeRobustness
from .checkValidPrimitive import checkValidPrimitive
import math 
import numpy as np 

def InfoGain(p, signal):
    '''
        use info gain w/ robustness as our optimizing obj function.
        p: the primitive
        signal: our dataset
    '''
    if not checkValidPrimitive(p, signal):
        return math.inf 
    robdeg_node = computeRobustness(p, signal)
    robdeg = np.minimum(robdeg_node, signal.robdeg)

    (Strue, Sfalse, true_list, false_list) = partitionWeights(robdeg, signal.label, signal.lblclass, p.oper)
    #want to minimize this, as we are subtracting this term when computing info cost.
    return IG_cost(Strue, Sfalse, true_list, false_list)

def IG_cost(Strue, Sfalse, true_list, false_list):
    H_Strue = sum([-x * math.log(x) for x in true_list])
    H_SFalse = sum([-x * math.log(x) for x in false_list])
    return Strue * H_Strue + Sfalse * H_SFalse

def partitionWeights(robdeg, labels, lblclass, oper):
    if oper == '>':
        Strue = robdeg > 0
        Sfalse = robdeg <= 0
    else: #due to handling for 0-1 variables
        Strue = robdeg >= 0
        Sfalse = robdeg < 0
    absrd = np.abs(robdeg)
    absrd_true = absrd[Strue]
    absrd_false = absrd[Sfalse]

    p_Strue = np.sum(absrd_true)/np.sum(absrd) if np.sum(absrd) > 0.00001 else 0
    p_Sfalse = 1 - p_Strue

    #we add a 0.00001 prior so that we would not take log 0
    numclass = len(lblclass)
    p_true_list = [0.00001] * numclass #arbitray default value for when absrd_true is empty
    for i in range(numclass-1):
        Strue_c1 = (labels[Strue] == lblclass[i])
        if absrd_true.size > 0:
            p_true_list[i] = max(0.00001, np.sum(absrd_true[Strue_c1])/np.sum(absrd_true))
    p_true_list[numclass-1] = max(0.00001, 1.0 - sum(p_true_list))

    p_false_list = [0.0001] * numclass
    for i in range(numclass-1):
        Sfalse_c1 = (labels[Sfalse] == lblclass[i])
        if absrd_false.size > 0: 
            p_false_list[i] = max(0.00001, np.sum(absrd_false[Sfalse_c1])/np.sum(absrd_false))
    p_false_list[numclass-1] = max(0.00001, 1.0 - sum(p_false_list))
    return (p_Strue, p_Sfalse, p_true_list, p_false_list)