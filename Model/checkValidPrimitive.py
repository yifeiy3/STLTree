from .DataProcess.signalProcess import Signal
from .Prim import FLPrimitives, SLPrimitives, Primitives
import math 

def checkValidPrimitive(p, signal):
    if p.oper == 'G' or p.oper == 'F':
        return checkValidFLPrimitive(p, signal)
    elif p.oper == 'FG' or p.oper == 'GF':
        return checkValidSLPrimitive(p, signal)
    else:
        print("invalid oper")
        return False 
    
def checkValidFLPrimitive(p, signal):
    t1, t2 = (p.param[0], p.param[1])
    if math.isnan(t1) or math.isnan(t2):
        return False 
    if t1 >= t2:
        print("Invalid FL interval, t1 appears before t2")
        return False
    min_sample_time = signal.time[1] - signal.time[0]
    #currently assume evenly spaced time stamps, makes no sense to have an interval smaller than that
    #since no change is happening. 
    if t2-t1 < min_sample_time or t1 < signal.time[0] or t2 > signal.time[-1]:
        print("Invalid FL interval, either too small or exceed time stamp unit")
        return False 
    return True 

def checkValidSLPrimitive(p, signal):
    t1, t2, t3 = (p.param[0], p.param[1], p.param[2])
    if math.isnan(t1) or math.isnan(t2):
        return False 
    if t1 >= t2 or t3 <= 0:
        print ("Invalid SL interval, t1 appears before t2 or t3 <= 0")
        return False
    min_sample_time = signal.time[1] - signal.time[0]
    #We don't want uninteresting rules that something happens after a very long time.
    #TODO: may need to change when doing real time data handling
    max_t3 = 10 * min_sample_time
    if t1 < signal.time[0] or t1 > signal.time[-1] - t3 or t2 - t1 < min_sample_time\
        or t2 > signal.time[-1] - t3 or min_sample_time > t3 or t3 > min(max_t3, signal.time[-1]-t2):
        print("Invalid SL interval, either too small or exceed time stamp unit")
        return False 
    return True 