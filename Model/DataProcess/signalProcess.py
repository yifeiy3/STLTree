import numpy as np 

class Signal():
    '''
        representation of our dataset, built from data frame
        currently works best when dataframe is a numpy array of int
        dim 1: the ith dataset
        dim 2: the state for each timestamp
        dim 3: devices
        @param: classdict: since we representing the state of device with integer,
            have a dictionary to convert it back for readable rules.
        @param: alldevices: list of all possible devices in the state
    '''
    def __init__(self, dataframe, labelidx, classdict, alldevices):
        numcol = np.shape(dataframe)[2]
        datacols = list(range(1, numcol)) #0th column is for timestamps
        datacols.pop(labelidx-1)
        self.labelidx = labelidx
        self.time = dataframe[0, 1:, 0] #a list of all the time stamps
        #since time is relative, WLOG we use the time interval by first sample.
        alldevices.pop(labelidx-1) #i-1th entry represents the ith column.
        self.device = alldevices #a list of all the devices
        self.data = dataframe[:, 1 :, datacols]
        self.robdeg = np.full((np.shape(dataframe)[0],), np.inf) 
        self.label = dataframe[:, 1:, labelidx] #leftmost col is timestamp
        #the robust degree we use as objfunc for learning tree
        self.lblclass = np.unique(self.label)
        self.minintval = self.time[1] - self.time[0] #currently assuming equal size intval
        self.classdict = classdict
        
    def getDimJ(self, idx):
        '''
            get the data for the states of jth device in the data
        '''
        return self.data[:, 1:, idx]