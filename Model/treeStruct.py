from .DataProcess.signalProcess import Signal 
import numpy as np 
from .PrimitiveCheckSat import primitiveCheckSat
import math 

class Node():
    def __init__(self, parent, signals, branch):
        '''
            @param: the parent node 
            @param: the fraction of signals classified by our node
            @param: the learned formula corresponding to our node
        '''
        self.parent = parent
        self.branch = branch
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
                        else 0.0
        self.effectivealpha = math.inf #effective alpha of the node used for pruning
        #default inifinity so we won't prune leaves.
    
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
        if data_left.size <= 0 or data_right.size <=0:
            return None, None
        robdeg_left = np.minimum(robdeg[lsat], self.signal.robdeg[lsat])
        robdeg_right = np.minimum(-robdeg[~lsat], self.signal.robdeg[~lsat])
        label_left = self.signal.label[lsat]
        label_right = self.signal.label[~lsat]
        signal_left = Signal(data_left, self.signal.labelidx, self.signal.classdict, self.signal.alldevices, label_left)
        signal_left.robdeg = robdeg_left
        signal_right = Signal(data_right, self.signal.labelidx, self.signal.classdict, self.signal.alldevices, label_right)
        signal_right.robdeg = robdeg_right
        return signal_left, signal_right

    def chopleaf(self):
        '''
            chop unnecessary splits of the tree to avoid overfitting
        '''
        self.leftchild = None 
        self.rightchild = None 
        self.PTSLformula = None 