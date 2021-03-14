import numpy as np 
from .treeEval import teval 
from .DataProcess.signalProcess import Signal 

def treeEvalPerformance(T, signals):
    '''
        evaluate our tree based on the misclassification rate
        input: signals: test data, 
                processed to intervals similar to our training data
    '''
    mcc = 0 #misclassficiation count
    for i in range(np.shape(signals.data)[0]):
        data = signals.data[i, :, :]
        single_sig = Signal(data[np.newaxis, :, :], signals.labelidx, signals.classdict, signals.alldevices, signals.label)
        tpred = teval(T, single_sig)
        t_gt = single_sig.label[i]
        if tpred != t_gt:
            mcc += 1
    print("misclassfication rate: {0}".format(mcc/(np.shape(signals.data)[0])))
    return mcc/(np.shape(signals.data)[0])


