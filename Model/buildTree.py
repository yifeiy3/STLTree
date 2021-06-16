from .setPrim import setBestPrimitive
from .treeStruct import Node 
import numpy as np 

def check_stop(tree, max_depth, frac_same, min_nobj):
    '''
        check our stop condition for learning the tree.
    '''
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

def buildTree(signals, Tmax, Steps, maxDepth, fracSame, minNumberObj):

    def buildTreeHelper(signals, parent=None, branch='left'):
        '''
            build our decision tree
        '''
        T = Node(parent, signals, branch)
        if check_stop(T, maxDepth, fracSame, minNumberObj):
            return T
        PTSLformula = setBestPrimitive(signals, Tmax, Steps)
        T.setPTSL(PTSLformula)
        signals_left, signals_right = T.partitionSignals() 
        if not signals_left or not signals_right:
            #can't find a way to split data further
            print("Null Split!")
            return T 
        
        T.leftchild = buildTreeHelper(signals_left, T, "left")
        T.rightchild = buildTreeHelper(signals_right, T, "right")
        return T
        
    return buildTreeHelper(signals)

