from .treeStruct import Node
from .Prim import FLPrimitives, SLPrimitives, Primitives
nodeid = 0

def NodeToString(node, lbldict, parentid, nodebranch, devicenames=None):
    '''
        @param: node, the subtree
        @param: dictionary corresponding to the label, i.e. classdict[label]
        @param: list of devices that maps to the primitive's dimension index
        @param: nodebranch: left child or right child, the root by default is left child.
    '''
    global nodeid
    ptsl = node.PTSLformula
    node.nodeid = nodeid
    nodeid += 1
    if not ptsl:
        ptsl_str = 'Not enough data, the device is always in state: {0}'.format(
            lbldict[node.predClass]
        )
        return ptsl_str
    else:
        ptsl_str = ptsl.toString(devicenames)
        s = "Node id: {0} \n \
            Parent id: {1} \n \
            Node branch: {2} \n \
            PTSL formula: {3} \n \
            Number of objects: {4} \n \
            Predicted Class: {5} \n \
            Prediction Error: {6} \n \
            Actual Predicted State: {7}\n\n".format(
                node.nodeid,
                parentid,
                nodebranch,
                ptsl_str,
                node.nobj,
                node.predClass,
                node.predError,
                lbldict[node.predClass]
            )
        return s 

def TreeToString(node, lbldict, devicenames=None):
    '''
        convert our learned tree to a readable format
    '''
    global nodeid 
    nodeid = 0 #reset node id for each tree
    queue = [(node, -1, 'left')] #(node, parentid)
    currentDepth = 1
    s = ''
    while queue:
        tnode, pid, branch = queue.pop(0) #pop from front
        if tnode.currentDepth > currentDepth:
            currentDepth += 1
            s += '_________________________________________________\n'
        s += NodeToString(tnode, lbldict, pid, branch, devicenames)
        if tnode.leftchild:
            queue.append((tnode.leftchild, tnode.nodeid, 'left'))
        if tnode.rightchild:
            queue.append((tnode.rightchild, tnode.nodeid, 'right'))
    return s 

