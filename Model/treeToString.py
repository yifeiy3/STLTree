from .treeStruct import Node
from .Prim import FLPrimitives, SLPrimitives, Primitives
nodeid = 0

def NodeToString(node, lbldict, parentid, devicenames=None):
    '''
        @param: node, the subtree
        @param: dictionary corresponding to the label, i.e. classdict[label]
        @param: list of devices that maps to the primitive's dimension index
    '''
    global nodeid
    ptsl = node.PTSLformula
    node.nodeid = nodeid
    if not ptsl:
        ptsl_str = 'error, empty ptsl when printing Node'
        return ptsl_str
    else:
        ptsl_str = ptsl.toString(devicenames)
        s = "Node id: {0} \n \
            Parent id {1} \n \
            PTSL formula: {2} \n \
            Number of objects {3} \n \
            Predicted Class {4} \n \
            Prediction Error {5} \n \
            Actual Predicted State {6}\n\n".format(
                nodeid,
                parentid,
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
    queue = [(node, -1)] #(node, parentid)
    currentDepth = 1
    s = ''
    while queue:
        tnode, pid = queue.pop(0) #pop from front
        if tnode.currentDepth > currentDepth:
            currentDepth += 1
            s += '_________________________________________________\n'
        s += NodeToString(tnode, lbldict, pid, devicenames)
        if tnode.leftchild:
            queue.append((tnode.leftchild, tnode.nodeid))
        if tnode.rightchild:
            queue.append((tnode.rightchild, tnode.nodeid))
    return s 

