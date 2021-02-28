import pandas as pd 

from Model.DataProcess.signalProcess import Signal
from Model.DataProcess.datahandling import trainingset
from Model.buildTree import buildTree
from Model.treeToString import TreeToString
import numpy as np 
import pickle 

#our training data
signal_data = pd.read_csv("event.csv", index_col=None, header=None)
ar = signal_data.to_numpy()
ar = ar[np.newaxis, :, :] #our dataset
alldevices = ar[0, 0, 1:].tolist()
print(alldevices)
training_set = trainingset(ar, alldevices) #a list of signals for training from our dataset

learnedTrees = [] #list of learned decision trees
for signals in training_set:
    T = buildTree(signals)
    learnedTrees.append(T)
    labeldevice = alldevices[signals.labelidx - 1]
    lbldict = signals.classdict[labeldevice]
    tree_output_file = "LearnedModel/treeprint_{0}.txt".format(labeldevice)
    tree_model_file = "LearnedModel/treemodel_{0}.pkl".format(labeldevice)
    with open(tree_output_file, "w") as out:
        out.write("LabelClass: {0}\n".format(labeldevice))
        treetxt = TreeToString(T, lbldict, signals.device)
        out.write(treetxt)
    
    with open(tree_model_file, "w") as outmodel:
        pickle.dump(T, outmodel, pickle.HIGHEST_PROTOCOL)




    


