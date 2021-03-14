import numpy as np 
import copy 

class Signal():
    '''
        representation of our dataset, built from data frame
        currently works best when dataframe is a numpy array of int
        dim 1: the ith dataset
        dim 2: the state for each timestamp
        dim 3: devices
        @param: classdict: since we representing the state of device with integer,
            have a dictionary to convert it back for readable rules.
        @param: alldevices: list of all possible devices in the state, except the label
    '''
    def __init__(self, dataframe, labelidx, classdict, alldevices, labelcol):
        # numcol = np.shape(dataframe)[2]
        # datacols = list(range(1, numcol)) #0th column is for timestamps
        # datacols.pop(labelidx-1)
        self.labelidx = labelidx
        self.time = np.arange(0, np.shape(dataframe)[1]) #a list of all the time stamps
        #since time is relative, WLOG we use the time interval by first sample.  
        copy_alldevice = copy.copy(alldevices) #need to create a copy since we removing columns
        try:
            copy_alldevice.pop(labelidx-1) #pop out the label column 
        except: 
            print(labelidx-1)
            print(copy_alldevice)  
            raise NotImplementedError  
        self.device = copy_alldevice #a list of all the devices
        self.alldevices = alldevices
        self.data = dataframe
        self.robdeg = np.full((np.shape(dataframe)[0],), np.inf) 
        #the robust degree we use as objfunc for learning tree
        self.label = labelcol #leftmost col is timestamp, 
        #right now using the last state of the time interval for our label device in data.
        self.minintval = self.time[1] - self.time[0] #currently assuming equal size intval
        self.classdict = classdict
        self.lblclass = list(classdict[alldevices[labelidx-1]].keys()) #all possible states of the device

    def getDimJ(self, idx):
        '''
            get the data for the states of jth device in the data
        '''
        return self.data[:, :, idx]