from .treeStruct import Node 
from .treePruneSelect import treeEvalPerformance
import copy 

def isleaf(T):
    '''
        check wheter our current node is a leaf
    '''
    return T.leftchild is None and T.rightchild is None 

def findnonleaf(T):
    '''
        find all the nodes of the tree that are not leaves, we prune from there
    '''
    if isleaf(T):
        return []
    leftnonleaf = findnonleaf(T.leftchild)
    rightnonleaf = findnonleaf(T.rightchild)
    return leftnonleaf + [T] + rightnonleaf 

def compute_Rerr(T):
    '''
        compute the total training error of the leaf nodes in the subtree with root T
        @return: (total error, number of leaves in the subtree)
    '''
    if isleaf(T):
        return T.predError, 1
    else:
        rerrl, numleafl = compute_Rerr(T.leftchild) #left error, total leaves on the left
        rerrr, numleafr = compute_Rerr(T.rightchild)
        return rerrl + rerrr, numleafl + numleafr

def compute_alpha(T):
    '''
        computes the effective alpha of a node
    '''
    err, numleaf = compute_Rerr(T)
    ealpha = (T.predError - err)/(numleaf - 1)
    T.effectivealpha = ealpha 
    return ealpha, T

def prune_basic_tree(parentnodes, epsilon = 0.02):
    '''
        basic pruning, for each parent of the leaves, if the prediction error did not 
        fall below threshold epsilon,
        the split is unnecessary, can simply prune the split.
    '''
    if not parentnodes:
        return #at root
    update = True 
    while update:
        update = False
        for i in range(len(parentnodes)):
            nodes = parentnodes[i]
            lnode = nodes.leftchild
            rnode = nodes.rightchild
            if isleaf(lnode) and isleaf(rnode):
                if nodes.predError <= lnode.predError + rnode.predError + epsilon:
                    #this means the split is unnecessary
                    print("we got here!")
                    nodes.chopleaf()
                    parentnodes.pop(i)
                    print(nodes)
                    if not isleaf(nodes):
                        print("this should not happen")
                    update = True
                    break 
                    #now is a leaf, not a parent node anymore 

def find_prunable_node(parentnodes):
    '''
        Given a list of leaf parents of the tree, return a prunable parent of leaf 
        based on the criterion:
            effective alpha for cost complexity < alpha 
        The node with the least effective alpha is returned first.
        @return: (modified leaf list afterwards, pruneable leaf node)
                None if not found, i.e. all nodes are more than alpha threshold, we done pruning
    '''
    if not parentnodes:
        return -1, None #we are at root
    ea_tuple = [] #list of (effective alpha, Node)
    for nodes in parentnodes:
        ea_tuple.append(compute_alpha(nodes)) #give each node a effective alpha 
    _least, thenode = min(ea_tuple)
    return parentnodes.index(thenode), thenode


def pruneTree(T, testdata):
    '''
        prune the tree base order effective alpha,
        compares test accuracy of pruned tree after each iteration of chopping
        @return the chopped tree with least test error.
    '''
    parentnodes = findnonleaf(T)
    prune_basic_tree(parentnodes)
    if not parentnodes:
        print("T should only be a root leaf now")
        print(T)
        return T.predError, T #we only have leaf left
    Tcopy = copy.deepcopy(T)
    test_error = treeEvalPerformance(T, testdata)
    stopiteration = 0
    iteration = 0
    idx, tnode = find_prunable_node(parentnodes)
    while tnode:
        #we find the tree with best test accuracy after pruning, and save
        #how many steps of pruning was needed to complete the tree.
       iteration += 1
       tnode.chopleaf()
       parentnodes.pop(idx)
       mcr = treeEvalPerformance(T, testdata)
       if test_error > mcr:
           stopiteration = iteration
           test_error = mcr
       idx, tnode = find_prunable_node(parentnodes)
    
    copy_parentnodes = findnonleaf(Tcopy)
    print("stop iteration : {0}".format(stopiteration))
    for i in range(stopiteration): 
        #we perform the pruning again to the copied tree, 
        #this tree should be the optimal tree for test set.
        copyidx, copynode = find_prunable_node(copy_parentnodes)
        copynode.chopleaf()
        copy_parentnodes.pop(copyidx)

    return test_error, Tcopy 


