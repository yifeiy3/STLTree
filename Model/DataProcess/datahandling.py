import pandas as pd 
from .signalProcess import Signal
import numpy as np 
import copy 

def separate_by_intervals(dataset, interval, offset):
    '''
        since our data exhibits behavior for the entire day, separate into
        short time intervals to help learning.
        Default interval length: 30 timestamplength, 
        each interval we shift from beginning of last interval after 5 timestamplength.
        @param: dataset, a 3 dimensional numpy array, described by Signal object
    '''
    ds_list = []
    num_data = np.shape(dataset)[0]
    for i in range(num_data):
        num_rows = np.shape(dataset)[1] - 1
        for j in range(1, num_rows, offset):
            end = j + interval
            if end >= num_rows - 1:
                diff = end - num_rows + 1
                ds = (dataset[i, j - diff + 1:num_rows, :])
                ds = ds[np.newaxis, :, :]
                ds_list.append(ds)
                break #we reached the end
            else:
                ds = (dataset[i, j: end, :])
                ds = ds[np.newaxis, :, :]
                ds_list.append(ds)
    return np.concatenate(ds_list)

def checkint(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

def construct_classdict(dataset, devices):
    '''
        change the dataset into a numpy array of integers
        map the states to integers for decision trees to learn. return the dict for that
        @return: a dict that maps individual item to the dictionary corresponding to them.
    '''
    print(devices)
    classdict = {}
    for i in range(np.shape(devices)[0]):
        if checkint(dataset[0, 1, i+1]):
            #convert each to int
            for k1 in range(np.shape(dataset)[0]):
                for k2 in range(np.shape(dataset)[1]):
                    dataset[k1, k2, i+1] = int(dataset[k1, k2, i+1])
                    #our dataset should be converted into an array of generic items, so this should work
        else:
            possibleStates = np.unique(dataset[:, :, i+1])
            itemdict = {} #maps individual item's state to each integer we converts
            statedict = {} #map each integer to the state it is representing.
            for k3 in range(np.shape(possibleStates)[0]):
                itemdict[possibleStates[k3]] = k3 
                statedict[k3] = possibleStates[k3]
            classdict[devices[i]] = statedict
            for k1 in range(np.shape(dataset)[0]):
                for k2 in range(np.shape(dataset)[1]):
                    dataset[k1, k2, i+1] = itemdict[dataset[k1, k2, i+1]]
    return dataset, classdict



def construct_trainingset(data_by_intervals, classdict, alldevices):
    '''
        construct our training set by returning a list of signals for our tree to learn.
        data_by_interval is a 3 dimensional numpy array, described by Signal object
        @param data_by_interval: already processed by construct_classdict
        @param classdict: the dict map.
        @param alldevices: list of all the possible devices in the system.
    '''
    training_signals = []
    numcols = np.shape(data_by_intervals)[2]
    for i in range(numcols-1):
        #not a continuous value, we can train tree with this as label
        if alldevices[i] in classdict:
            datacols = list(range(1, numcols)) #0th column is for timestamps
            datacols.pop(i)
            labelcol = data_by_intervals[:, -1, i+1]
            data_for_signal = data_by_intervals[:, :, datacols]
            training_signals.append(Signal(data_for_signal, i+1, classdict, alldevices, labelcol))
    return training_signals
    

def trainingset(dataset, alldevices, interval = 10, offset = 2):
    data_by_intervals = separate_by_intervals(dataset, interval, offset)
    ds, classdict = construct_classdict(data_by_intervals, alldevices)
    print(classdict)
    res = construct_trainingset(ds, classdict, alldevices)
    return res