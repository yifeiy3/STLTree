import pandas as pd 

from Model.DataProcess.signalProcess import Signal
from Model.DataProcess.datahandling import trainingset, evaluationset, trainingsetWithStateChange, evaluationsetWithStateChange
from Model.buildTree import buildTree
from Model.treeToString import TreeToString
from Model.treepruning import pruneTree
import numpy as np 
import pickle 
import argparse

#parsing input about data handling
parser = argparse.ArgumentParser(description='Train a tree on learning time related rules with PSTL in a Smartthings environment')
parser.add_argument('--interval', action = 'store', type=int, dest = 'interval', default=10,
    help='Number of timestamps per training data interval, default 10')
parser.add_argument('--offset', action = 'store', type=int, dest = 'offset', default=2,
    help='Number of timestamps we skip between training data intervals, default 2')
parser.add_argument('--withStateChange', action = 'store_true', dest='stateChange', default=False,
    help='Whether we process interval on interval and offset or on stateChanges.')

#parsing input about tree stop condition
parser.add_argument('--maxDepth', action = 'store', type=int, dest = 'maxDepth', default=4,
    help='Maximum depth of the learned treee, default is 4')
parser.add_argument('--fracSame', action = 'store', type=float, dest = 'fracSame', default=0.95,
    help='Once we reach this accuracy of the class, we stop splitting that branch, default 0.95')
parser.add_argument('--minObj', action = 'store', type=int, dest = 'minObj', default=30,
    help='minimum number of signals in the class to continue recursion, default is 30')

#parsing input about Simulated Annealing
parser.add_argument('--Tmax', action='store', type=float, dest='tmax', default=20000.0, 
    help='The maximum temperature for learning rules with Simulated Annealing, default 20000')
parser.add_argument('--Steps', action='store', type=int, dest='steps', default=20000, 
    help='The number of steps we perform for Simulated Annealing, default 20000')
args = parser.parse_args()

#our training data
data_csv = ['Samsung/benchmark8.csv', 'Samsung/benchmark9.csv', 'Samsung/benchmark10.csv', 'Samsung/benchmark11.csv', 'Samsung/benchmark12.csv', 'Samsung/benchmark13.csv']
validate_csv = ['Samsung/benchmark8.csv']
ar = []
for csv_file in data_csv:
    signal_data = pd.read_csv(csv_file, index_col=None, header=None)
    ar.append(signal_data.to_numpy())

if ar:
    alldevices = ar[0][0, 1:].tolist()
else:
    raise Exception("We do not have data files")

if args.stateChange:
    training_set = trainingsetWithStateChange(ar, alldevices, args.interval)
else:
    training_set = trainingset(ar, alldevices, interval=args.interval, offset=args.offset) #a list of signals for training from our dataset

#add a validation set for pruning our tree
va = []
for csv_file in validate_csv:
    validation_data = pd.read_csv(csv_file, index_col=None, header=None)
    va.append(validation_data.to_numpy())

if args.stateChange:
    validation_set = evaluationsetWithStateChange(va, alldevices, args.interval, args.offset)
else:
    cdict = {}
    try:
        with open("LearnedModel/training_classdict.pkl", "rb") as dictfile:
            cdict = pickle.load(dictfile)
    except FileNotFoundError:
        raise Exception("Learned class dict not found.")
    validation_set = evaluationset(va, alldevices, cdict, interval=args.interval, offset=args.offset) #consistent with training set

if len(training_set) != len(validation_set):
    raise Exception("Training set and validation set does not contain the same number of devices")

learnedTrees = [] #list of learned decision trees
for i in range(len(training_set)): 
    signals = training_set[i]
    T = buildTree(signals, Tmax=args.tmax, Steps=args.steps, maxDepth=args.maxDepth, fracSame=args.fracSame, minNumberObj=args.minObj)
    learnedTrees.append(T)
    labeldevice = alldevices[signals.labelidx - 1]
    lbldict = signals.classdict[labeldevice]
    tree_output_file = "LearnedModel/treeprint/{0}.txt".format(labeldevice)
    tree_model_file = "LearnedModel/treemodel/{0}.pkl".format(labeldevice)
    with open(tree_output_file, "w") as out:
        out.write("LabelClass: {0}\n".format(labeldevice))
        out.write("Device to Number dictionary: {0}\n".format(signals.classdict))
        treetxt = TreeToString(T, lbldict, signals.device)
        out.write(treetxt)
    
    with open(tree_model_file, "wb") as outmodel:
        pickle.dump(T, outmodel, pickle.HIGHEST_PROTOCOL)


    #prune our learned tree
    validation_signals = validation_set[i]
    validation_error, TP = pruneTree(T, validation_signals)
    tree_prune_output = "LearnedModel/treepostpruneprint/{0}.txt".format(labeldevice)
    tree_prune_model = "LearnedModel/treepostprunemodel/{0}.pkl".format(labeldevice)

    with open(tree_prune_output, "w") as out:
        out.write("Test_error: {0} \n".format(validation_error))
        out.write("LabelClass: {0}\n".format(labeldevice))
        out.write("Device to Number dictionary: {0}\n".format(signals.classdict))
        treetxt = TreeToString(TP, lbldict, signals.device)
        out.write(treetxt)
    with open(tree_prune_model, "wb") as outmodel:
        pickle.dump(TP, outmodel, pickle.HIGHEST_PROTOCOL)
    


