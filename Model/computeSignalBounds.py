from .DataProcess.signalProcess import Signal
import numpy as np 

def computeSignalBounds(signal, steps):
    '''
        compute the bounds for the parameter space we want to learn. 
        our current data is a csv that can be read into a 2d numpy array of
        first row: device name
        first column: time stamps
        other columns: dimension of a signal
        @param: a numpy array of the dataset
        @param: step limiter for simulated annealing, if total states from our bounds
        is less than specified steps, we simply look through all possible parameter
        assignments.
        @return: (time bounds, space bounds, whether we check all states instead of using SA
        for FLprim and SLprim)
    '''
    _, _, ndim = np.shape(signal.data)
    interval_bounds = np.zeros((ndim, 2))
    time_bounds = [signal.time[0], signal.time[-1]]
    check_all_states = [(False, False)] * ndim 

    for j in range(ndim):
        sig = signal.getDimJ(j)
        interval_bounds[j, :] = [np.amin(sig), np.amax(sig)]
        #total number of space parameter is limited by the number of states in interval bounds
        total_space_possible = np.amax(sig) - np.amin(sig) + 1

        #total number of possible assignments of time parameter for first level primitive is n choose 2
        total_time_possible_FL = (time_bounds[1]-time_bounds[0] + 1) * (time_bounds[1]-time_bounds[0]) // 2
        #total number of possible assignments of time parameter for second level primitive can be upperbounded by n choose 2 * n/2
        total_time_possible_SL = ((time_bounds[1]-time_bounds[0] + 1) ** 2) * (time_bounds[1]-time_bounds[0]) // 4
        #prevent overflow
        possibleFL = total_space_possible < steps and total_time_possible_FL < steps \
                        and total_space_possible * total_time_possible_FL < steps 
        #prevent overflow
        possibleSL = total_space_possible < steps and total_time_possible_SL < steps \
                        and total_space_possible * total_time_possible_SL < steps 
        check_all_states[j] = (possibleFL, possibleSL)

    return (time_bounds, interval_bounds, check_all_states)