import pandas as pd 

from Model.DataProcess.signalProcess import Signal
from Model.DataProcess.datahandling import trainingset, evaluationset
from Model.buildTree import buildTree
from Model.treeToString import TreeToString
from Model.treepruning import pruneTree
import numpy as np 
import pickle 

#our training data
data_csv = ['Samsung/event.csv', 'Samsung/event1.csv', 'Samsung/event2.csv', 'Samsung/event3.csv']
validate_csv = ['Samsung/validate.csv']
ar = []
for csv_file in data_csv:
    signal_data = pd.read_csv(csv_file, index_col=None, header=None)
    ar.append(signal_data.to_numpy())
#ar = ar[np.newaxis, :, :] #our dataset
if ar:
    alldevices = ar[0][0, 1:].tolist()
else:
    raise Exception("We do not have data files")
#print(alldevices)
training_set = trainingset(ar, alldevices, interval=10, offset=2) #a list of signals for training from our dataset

cdict = {}
with open("LearnedModel/training_classdict.pkl", "rb") as dictfile:
    cdict = pickle.load(dictfile)
if cdict is None:
    raise Exception("Learned class dict not found.")

#add a validation set for pruning our tree
va = []
for csv_file in validate_csv:
    validation_data = pd.read_csv(csv_file, index_col=None, header=None)
    va.append(validation_data.to_numpy())
validation_set = evaluationset(va, alldevices, cdict, interval=10, offset=2) #consistent with training set

learnedTrees = [] #list of learned decision trees
for i in range(len(training_set)): 
    signals = training_set[i]
    T = buildTree(signals)
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
    


