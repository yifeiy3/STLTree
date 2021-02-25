from .DataProcess.signalProcess import Signal
import numpy as np 

def computeSignalBounds(signal):
    '''
        compute the bounds for the parameter space we want to learn. 
        our current data is a csv that can be read into a 2d numpy array of
        first row: device name
        first column: time stamps
        other columns: dimension of a signal
        @param: a numpy array of the dataset
    '''
    _, _, ndim = np.shape(signal.data)
    interval_bounds = np.zeros((ndim, 2))
    for j in range(ndim):
        sig = signal.getDimJ(j)
        interval_bounds[j, :] = [np.amin(sig), np.amax(sig)]
    time_bounds = [signal.time[0], signal.time[-1]]
    return (time_bounds, interval_bounds)