import pickle 
from Model.Prim import FLPrimitives, SLPrimitives, Primitives

def isleaf(T):
    return T.leftchild is None and T.rightchild is None 

def findleaves(T):
    if T is None:
        return []
    if isleaf(T):
        return [T] 
    return findleaves(T.leftchild) + findleaves(T.rightchild)

def printRule(T):
    s = ''
    if T is None:
        return s
    while T.parent is not None:
        print(T.parent)
        PTSL = T.parent.PTSLformula #the tree is split based on parent's PTSL
        if PTSL is None:
            raise Exception("Parent has null split")
        if T.branch == 'left':
            #true branch
            s += PTSL.toWordString()
        else:
            s += PTSL.negateWordString()
        T = T.parent
        if(T.parent) is not None:
            s += " and \n\t\t"
    return s 

ERROR_THRESHOLD = 0.10 #since some state change are only random choice, we should only
                       #print out the rules with good confidence
cdict = {}
with open("LearnedModel/training_classdict.pkl", "rb") as dictfile:
    cdict = pickle.load(dictfile)
if not cdict:
    raise Exception("Learned class dict not found")

devices = cdict.keys()
for device in devices: 
    T = None 
    try:
        with open("LearnedModel/treemodel/{0}.pkl".format(device), 'rb') as inmodel:
            T = pickle.load(inmodel)
    except FileNotFoundError:
        raise Exception("Learned model not found")
    possibleStates = cdict[device].keys()
    ruledict = {keys: [] for keys in possibleStates}
    leaves = findleaves(T)
    for leaf in leaves: 
        if leaf.predError < ERROR_THRESHOLD:
            s = printRule(leaf)
            predclass = leaf.predClass 
            s += "(Error rate: {0})\n".format(leaf.predError)
            ruledict[predclass].append(s)
    with open("LearnedModel/PrintedRules/{0}.txt".format(device), "w") as ofile:
        ofile.write("Device: {0} \n".format(device))
        ofile.write("Classdict: {0} \n".format(cdict))
        for keys in ruledict.keys():
            statename = cdict[device][keys]
            ofile.write("State: {0}\n".format(statename))
            ofile.write("Under Condition: \n")
            count = 1
            for i in range(len(ruledict[keys])):
                rulestr = ruledict[keys][i]
                ofile.write("\t" + str(count) + ". ")
                ofile.write(rulestr)
                ofile.write("\n")
                if i != len(ruledict[keys]) - 1:
                    ofile.write("or")
                count += 1
            ofile.write("___________________________________________\n")
    
    