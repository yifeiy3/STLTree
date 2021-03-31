import pandas as pd 
from .signalProcess import Signal
import numpy as np 
import copy 
import pickle 

def separate_dataset(dataset, interval):
    '''
        for Samsung Smarttthings data, it is possible to have large gaps between events,
        we use this to separate the large gaps into components where we have separation
        by 1 second.
    '''
    components = []
    num_data = np.shape(dataset)[0]
    last_ts = 0 #if difference > 10, we are at a different component for analyze.
    last_cut = 1 #beginning of this component
    for i in range(1, num_data): #first row is our device column
        curr_ts = int(dataset[i, 0]) #this should be the row idx.
        if curr_ts - interval > last_ts:
            if curr_ts >= last_cut + interval:
                #if the component is big enough to separate into our interval
                components.append(dataset[last_cut: i, :])
            last_cut = i
        last_ts = curr_ts 
    if num_data - last_cut > 10:
        components.append(dataset[last_cut: num_data, :])
    return components
            

def separate_by_intervals(dataset, interval, offset):
    '''
        since our data exhibits behavior for the entire day, separate into
        short time intervals to help learning.
        Default interval length: 10 timestamplength, 
        each interval we shift from beginning of last interval after 5 timestamplength.
        @param: dataset, a list of 2 dimensional numpy array
                each 2d array represents a component of data described by separate_dataset.
    '''
    ds_list = []
    for i in range(len(dataset)):
        datacomponent = dataset[i]
        num_rows = np.shape(datacomponent)[0] - 1
        for j in range(1, num_rows, offset):
            end = j + interval
            if end >= num_rows - 1:
                diff = end - num_rows + 1
                ds = (datacomponent[j - diff + 1:num_rows, :])
                ds = ds[np.newaxis, :, :]
                ds_list.append(ds)
                break #we reached the end
            else:
                ds = (datacomponent[j: end, :])
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

def build_from_classdict(dataset, devices, classdict):
    '''
        change the dataset into a numpy array of integers, the way to change is 
        instructed by given classdict
        @return: a dict that maps individual item to the dictionary corresponding to them.
    '''
    for i in range(np.shape(devices)[0]):
        if devices[i] not in classdict:
            #convert each to int
            for k1 in range(np.shape(dataset)[0]):
                for k2 in range(np.shape(dataset)[1]):
                    dataset[k1, k2, i+1] = int(dataset[k1, k2, i+1])
                    #our dataset should be converted into an array of generic items, so this should work
        else:
            statedict = classdict[devices[i]] #map each integer to the state it is representing.
            itemdict = {v: k for k, v in statedict.items()} #all the dictionary values should be unique
            print(itemdict)
            for k1 in range(np.shape(dataset)[0]):
                for k2 in range(np.shape(dataset)[1]):
                    try:
                        dataset[k1, k2, i+1] = itemdict[dataset[k1, k2, i+1]]
                    except KeyError:
                        print("unrecognized state: {0} for device {1}".format(
                            dataset[k1, k2, i+1],
                            devices[i]
                        ))
                        dataset[k1, k2, i+1] = -1 #arbitrary class
    return dataset

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
    data_components = separate_dataset(dataset, interval)
    data_by_intervals = separate_by_intervals(data_components, interval, offset)
    ds, classdict = construct_classdict(data_by_intervals, alldevices)
    print(classdict)
    res = construct_trainingset(ds, classdict, alldevices)
    with open("LearnedModel/training_classdict.pkl", "wb") as savefile:
        pickle.dump(classdict, savefile, pickle.HIGHEST_PROTOCOL)
    return res

def evaluationset(dataset, alldevices, classdict, interval = 10, offset = 2):
    #different than training set, we need to use the class dictionary learned from our trainingset
    #to avoid any representation discrepancy.
    data_components = separate_dataset(dataset, interval)
    data_by_intervals = separate_by_intervals(data_components, interval, offset)
    ds = build_from_classdict(data_by_intervals, alldevices, classdict)
    return construct_trainingset(ds, classdict, alldevices)