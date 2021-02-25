from .DataProcess.signalProcess import Signal 
import numpy as np 
from .PrimitiveCheckSat import primitiveCheckSat

class Node():
    def __init__(self, parent, signals):
        '''
            @param: the parent node 
            @param: the fraction of signals classified by our node
            @param: the learned formula corresponding to our node
        '''
        self.parent = parent
        self.leftchild = None 
        self.rightchild = None 
        self.signal = signals
        self.nodeid = -1
        self.currentDepth = parent.currentDepth + 1 if parent else 1
        self.nobj = 0
        self.PTSLformula = None #the learned rule corresponding to the node.
        self.fracClass = [] #list of the fraction of classes, if reach 99% we stop
        if signals.label is not None:
            self.nobj = np.size(signals.label)
            for item in signals.lblclass:
                self.fracClass.append(np.sum(signals.label == item)/self.nobj)
        self.predClass = self.fracClass.index(max(self.fracClass)) if self.fracClass \
                        else 0 #no signal, give arbitrary class
        self.predError = sum(self.fracClass) - max(self.fracClass) if self.fracClass \
                        else 0
    
    def setPTSL(self, PTSLformula):
        self.PTSLformula = PTSLformula
    
    def partitionSignals(self):
        '''
            separate the signals by our PTSL formula, 
            left branch satisfies our formula and right branch doesnt
        '''
        robdeg, lsat = primitiveCheckSat(self.PTSLformula, self.signal)
        data_left = self.signal.data[lsat, :, :]
        data_right = self.signal.data[~lsat, :, :]
        robdeg_left = np.amin(robdeg[lsat])
        robdeg_right = np.amin(robdeg[~lsat])
        signal_left = Signal(data_left, self.signal.labelidx, self.signal.classdict)
        signal_left.robdeg = robdeg_left
        signal_right = Signal(data_right, self.signal.labelidx, self.signal.classdict)
        signal_right.robdeg = robdeg_right
        return signal_left, signal_right