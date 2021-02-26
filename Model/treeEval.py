from .PrimitiveCheckSat import primitiveCheckSat
from .treeStruct import Node 
import numpy as np

def eval(T, signal):
    '''
        evaluate our signal by our learned Tree to check whether for anomalies
        @T: our learned tree
        @signal: the signal data to be evaluated
        return the class by our learned tree
    '''
    if T.leftchild is None: #should be a leaf
        if T.rightchild:
            print("Null split 1, this should not happen")
            raise Exception("Not Implemented")
        return T.predclass 
    if T.rightchild is None: #should be a leaf
        print("Null split 2, this should not happen")
        raise Exception("Not Implemented")
    prim = T.PTSLformula 
    _, lsat = primitiveCheckSat(prim, signal)
    if np.sum(lsat) == 1: 
        return eval(T.leftchild, signal)
    else:
        return eval(T.rightchild, signal)
