from .Prim import FLPrimitives, SLPrimitives
from .DataProcess.signalProcess import Signal
import numpy as np 
import math 
import copy

def computeRobustness(p, signal):
    '''
        p: primitive
        signal: dataset
    '''
    if p is None:
        raise Exception("No prmitive given")
    if p.oper == 'G':
        return fl_G(p, signal)
    elif p.oper == 'F':
        return fl_F(p, signal)
    elif p.oper == 'GF':
        return sl_GF(p, signal)
    elif p.oper == 'FG':
        return sl_FG(p, signal)
    else:
        raise Exception("unsupported primitive for robustness")

def fl_G(p, signal):
    Nobj = np.shape(signal.data)[0]
    dim_idx = p.dim 
    ineq_dir = p.ineq

    tau1, tau2, c = (p.param[0], p.param[1], p.param[2])
    #TODO: currently the model is treating each measure of the signal is of equal time interval,
    #might need to change this in the future for real data.
    t1, t2 = (signal.time[0], signal.time[1])
    t_intval = t2 - t1
    intv_start = math.floor((tau1 - t1) / t_intval)
    intv_end = math.floor((tau2 - t1) / t_intval) + 1

    robustdeg = np.zeros((Nobj, ))
    if ineq_dir == '<':
        for i in range(Nobj):
            robustdeg[i] = c - np.amax(signal.data[i, intv_start: intv_end, dim_idx], axis=0)
            #ith data, the interval part, and the device id
    elif ineq_dir == '>':
        for i in range(Nobj):
            robustdeg[i] = np.amin(signal.data[i, intv_start: intv_end, dim_idx], axis=0) - c
    else:
        raise Exception("invalid ineq_dir in robustness: {0}".format(ineq_dir))
    return robustdeg

def fl_F(p, signal):
    ineq_dir = p.ineq
    if ineq_dir == '<':
        newp = copy.deepcopy(p)
        newp.ineq = '>'
        res = -fl_G(newp, signal)
        #print(res)
        return res 
    elif ineq_dir == '>':
        newp = copy.deepcopy(p)
        newp.ineq = '<'
        res = -fl_G(newp, signal)
        #print(res)
        return res 
    else:
        raise Exception("invalid ineq_dir in robustness: {0}".format(ineq_dir))

def sl_FG(p, signal):
    Nobj = np.shape(signal.data)[0]
    dim_idx = p.dim 
    ineq_dir = p.ineq

    tau1, tau2, tau3, c = (p.param[0], p.param[1], p.param[2], p.param[3])
    t1, t2 = (signal.time[0], signal.time[1])
    t_intval = t2 - t1
    intv_start = math.floor((tau1 - t1) / t_intval)
    intv_end = math.floor(max((tau2 + tau3 - t1) // t_intval+1, np.shape(signal.time)[0]))
    window_len = math.floor(tau3 // t_intval) + 1 #size of [0, tau3] window

    robustdeg = np.zeros((Nobj, ))
    if ineq_dir == '<':
        for i in range(Nobj):
            a = signal.data[i, intv_start: intv_end, dim_idx]
            robustdeg[i] = c - computeMinMaxFilt(a, window_len)
    elif ineq_dir == '>':
        for i in range(Nobj):
            a = signal.data[i, intv_start: intv_end, dim_idx]
            robustdeg[i] = c - computeMaxMinFilt(a, window_len)        
    else:
        raise Exception("invalid ineq_dir in robustness: {0}".format(ineq_dir))        
    return robustdeg

def sl_GF(p, signal):
    ineq_dir_t = p.ineq
    if ineq_dir_t == '<':
        newp = copy.deepcopy(p)
        newp.ineq = '>'
        return -sl_FG(newp, signal)
    elif ineq_dir_t == '>':
        newp = copy.deepcopy(p)
        newp.ineq = '<'
        return -sl_FG(newp, signal)
    else:
        raise Exception("invalid ineq_dir in robustness: {0}".format(ineq_dir_t))

def computeMinMaxFilt(a, windowlen):
    '''
        input: state for our device in a numpy array, 
               our window size
    '''
    minlst = [0] * (np.shape(a)[0] - windowlen + 1)
    for i in range(np.shape(a)[0] - windowlen + 1):
        minlst[i] = min(a[i : i+windowlen-1])
    return max(minlst)


def computeMaxMinFilt(a, windowlen):
    '''
        input: state for our device in a numpy array, 
               our window size
    '''
    maxlst = [0] * (np.shape(a)[0] - windowlen + 1)
    for i in range(np.shape(a)[0] - windowlen + 1):
        maxlst[i] = max(a[i : i+windowlen-1])
    return min(maxlst)
