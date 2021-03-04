from .setPrim import setBestPrimitive
from .treeStruct import Node 
import numpy as np 

max_depth = 5 #maximum depth of the tree
frac_same = 0.99 #once we reach 99% accuracy of the class, we stop splitting that branch
min_nobj = 2 #min number of signals in the class to continue recursion

def check_stop(tree):
    '''
        check our stop condition for learning the tree.
    '''
    global max_depth
    global frac_same
    global min_nobj
    if tree.currentDepth >= max_depth:
        print("Learning stopped by exceeding current depth limit")
        return True 
    if tree.nobj < min_nobj:
        print("Learning stopped by going below minimum object")
        return True 
    if max(tree.fracClass) > frac_same:
        print("Learning stpped by exceeding accuracy threshold")
        return True
    return False 

def buildTree(signals, parent=None):
    '''
        build our decision tree
    '''
    T = Node(parent, signals)
    PTSLformula = setBestPrimitive(signals)
    T.setPTSL(PTSLformula)
    if check_stop(T):
        return T
    signals_left, signals_right = T.partitionSignals() 
    if not signals_left or not signals_right:
        #can't find a way to split data further
        print("Null Split!")
        return T 
    
    T.leftchild = buildTree(signals_left, T)
    T.rightchild = buildTree(signals_right, T)
    return T
    
    

