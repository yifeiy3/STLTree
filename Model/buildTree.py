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
    if tree.currentDepth > max_depth:
        return True 
    if tree.nobj < min_nobj:
        return True 
    if max(tree.fracClass) > frac_same:
        print(max(tree.fracClass))
        return True
    return False 

def buildTree(signals, parent=None):
    '''
        build our decision tree
    '''
    T = Node(parent, signals)
    if check_stop(T):
        print("WE GOT FUCKING HERE")
        return T
    PTSLformula = setBestPrimitive(signals)
    T.setPTSL(PTSLformula)
    signals_left, signals_right = T.partitionSignals() 
    if not signals_left.data or not signals_right.data:
        #can't find a way to split data further
        print("Null Split!")
        return T 
    
    T.leftchild = buildTree(signals_left, T)
    T.rightchild = buildTree(signals_right, T)
    return T
    
    

