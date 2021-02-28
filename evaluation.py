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