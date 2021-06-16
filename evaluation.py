import pandas as pd
from Model.treeEval import teval

from Model.DataProcess.signalProcess import Signal
from Model.DataProcess.datahandling import trainingset, evaluationset
import numpy as np 
import pickle
import argparse 

parser = argparse.ArgumentParser(
    description='Print the rules learned by our PSTL Tree'
)
parser.add_argument('--threshold', action = 'store', type=float, dest='error_threshold', default=0.10,
    help='The error threshold a rule need to be less than to have it printed out, default 0.10')
parser.add_argument('--interval', action = 'store', type=int, dest = 'interval', default=10,
    help='Number of timestamps per evaluation data interval, this should be the same as the \
        interval used for training, default 10')
parser.add_argument('--offset', action = 'store', type=int, dest = 'offset', default=2,
    help='Number of timestamps we skip between training data intervals, this should be the same as \
        the interval used for training, default 2')

args = parser.parse_args()

ERROR_THRESHOLD = args.error_threshold #since some state change are just random chance, only the mispredictions going lower
                       #than this threshold is recorded as anomalies.

eval_csv = ['TestSet2/eval.csv']
for csv_file in eval_csv:
    signal_data = pd.read_csv(csv_file, index_col=None, header=None)
    ar = signal_data.to_numpy()
if ar:
    alldevices = ar[0, 1:].tolist()
print(alldevices)

cdict = {}
try:
    with open("LearnedModel/training_classdict.pkl", "rb") as dictfile:
        cdict = pickle.load(dictfile)
except FileNotFoundError:
    raise Exception("Learned class dict not found.")

eval_set = evaluationset(ar, alldevices, cdict, interval=args.interval, offset=args.offset) #need to be consistent with training

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
                if term == -1:
                    data[k1, k2] = "UNKNOWN"
                data[k1, k2] = cd[thedevice][term]
    return data


for signals in eval_set:
    labeldevice = alldevices[signals.labelidx - 1]
    T = None 
    count = 0 #number of unmatched predictions, anomalies
    try: 
        with open("LearnedModel/treepostprunemodel/{0}.pkl".format(labeldevice), 'rb') as inmodel:
            T = pickle.load(inmodel)
    except FileNotFoundError:
        print("Unable to find model file for device :{0}".format(labeldevice))
        continue
    if T is not None:
        with open("EvalReport/{0}_report.txt".format(labeldevice), "w") as outfile:
            for i in range(np.shape(signals.data)[0]):
                data = signals.data[i, :, :]
                single_sig = Signal(data[np.newaxis, :, :], signals.labelidx, signals.classdict, signals.alldevices, signals.label)
                error, tpred = teval(T, single_sig)
                t_gt = single_sig.label[i]
                if tpred != t_gt:
                    count = count + 1
                    if error <= ERROR_THRESHOLD: 
                        #only print out the discrepancy with high probability prediction,
                        #since some change of states are purely based on random chance.
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

