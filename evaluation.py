import pandas as pd
from Model.treeEval import teval

from Model.DataProcess.signalProcess import Signal
from Model.DataProcess.datahandling import trainingset
import numpy as np 
import pickle

signal_data = pd.read_csv("eval.csv", index_col=None, header=None)
ar = signal_data.to_numpy()
ar = ar[np.newaxis, :, :]
alldevices = ar[0, 0, 1:].tolist()
print(alldevices)
eval_set = trainingset(ar, alldevices)

def reverse_classdict(signal, index):
    '''
        reverse a single signal back to its state before process,
        used to for printing out evaluation differences.
        @param index of the signal
        @returns the specific index for the signal after reversing.
    '''
    cd = signal.classdict
    devices = signal.device 
    data = signal.data[index, :, :]
    for k1 in range(np.shape(data)[0]):
        for k2 in range(np.shape(data)[1]):
            thedevice = devices[k2]
            if thedevice in cd:
                term = data[k1, k2]
                data[k1, k2] = cd[thedevice][term]
    return data


for signals in eval_set:
    labeldevice = alldevices[signals.labelidx - 1]
    T = None 
    count = 0 #number of unmatched predictions, anomalies
    try: 
        with open("LearnedModel/treemodel_{0}.pkl".format(labeldevice), 'rb') as inmodel:
            T = pickle.load(inmodel)
    except FileNotFoundError:
        print("Unable to find model file for device :{0}".format(labeldevice))
        continue
    if T is not None:
        with open("EvalReport/{0}_report.txt".format(labeldevice), "w") as outfile:
            for i in range(np.shape(signals.data)[0]):
                data = signals.data[i, :, :]
                single_sig = Signal(data[np.newaxis, :, :], signals.labelidx, signals.classdict, signals.device, signals.label)
                tpred = teval(T, single_sig)
                t_gt = single_sig.label[i]
                if tpred != t_gt:
                    count = count + 1
                    tpred_str = signals.classdict[labeldevice][tpred]
                    t_gt_str = signals.classdict[labeldevice][t_gt]
                    s = '___________________________________\n \
                        Anomalie: \n \
                        Predicted State: {0} \n \
                        Actual State: {1} \n \
                        Under data condition: \n {2} \n {3} \n'.format(
                            tpred_str,
                            t_gt_str,
                            signals.device,
                            reverse_classdict(signals, i)
                        )
                    outfile.write(s)
            outfile.write("total discrepancies: {0}\n".format(count))
            outfile.write("Discrepancy percentage: {0}\n".format(count/np.shape(signals.data)[0]))
    else:
        print('File exists but model not found for device: {0}').format(labeldevice)
        continue

