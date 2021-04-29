import pickle 
from Model.Prim import FLPrimitives, SLPrimitives, Primitives, negateIneq

'''
    This program parses the rules learned from our STLTree model into a dictionary
    for our monitor to use
'''
def negateOper(oper):
    if oper == 'F':
        return 'G'
    if oper == 'G':
        return 'F'
    if oper == 'FG':
        return 'GF'
    return 'FG'

def findleaves(T):
    if T is None:
        return []
    if T.leftchild is None and T.rightchild is None:
        return [T] 
    return findleaves(T.leftchild) + findleaves(T.rightchild)

def findPossibleStates(statedict, idx, ineq):
    '''
        given some rule (device < c), we convert this into all the possible states in classdict that
        is mapped from some integer less than c. In otherwords, a list of all possible satisfying states
    '''
    if ineq == '<':
        return [statedict[i] for i in statedict.keys() if int(i) < idx]
    if ineq == '>':
        return [statedict[i] for i in statedict.keys() if int(i) > idx]
    if ineq == '>=':
        return [statedict[i] for i in statedict.keys() if int(i) >= idx]
    else:
        return [statedict[i] for i in statedict.keys() if int(i) <= idx]
    
def getRule(T, classdict, cap):
    s = []
    if T is None:
        return s 
    while T.parent is not None:
        PTSL = T.parent.PTSLformula 
        if PTSL is None:
            raise Exception("Parent has null split")
        PTSL_type, PTSL_ineq = PTSL.oper, PTSL.convertIneq() 
        #(a, b) represents the interval last cap - a, cap-b seconds 
        if PTSL_type == 'G' or PTSL_type == 'F':
            PTSL_time_interval = (cap - PTSL.param[0], cap - PTSL.param[1], -1)
            objval = int(PTSL.param[2])
        else:
            PTSL_time_interval = (cap - PTSL.param[0], cap - PTSL.param[1], PTSL.param[2])
            objval = int(PTSL.param[3])

        statedict = classdict[PTSL.dimname]
        if T.branch == 'left':
            #true branch
            s.append((PTSL.dimname, PTSL_type, PTSL_ineq, PTSL_time_interval, findPossibleStates(statedict, objval, PTSL_ineq)))
        else:
            PTSL_ineq = negateIneq(PTSL_ineq)
            PTSL_type = negateOper(PTSL_type)
            s.append((PTSL.dimname, PTSL_type, PTSL_ineq, PTSL_time_interval, findPossibleStates(statedict, objval, PTSL_ineq)))
        T = T.parent
    return s 

def convertRules(cdict, error_threshold = 0.05, cap = 10):
    '''
        for a model that we learned device state to be A when B happens, we add a rule dictionary that
        says device should be in the specified state when B happens 

        @param: cdict: the classdict used to train our model
        @param: error_threshold: only rules with confidence higher than this will be considered.
        @param: cap: the interval period we used to divide our dataset during training.

        @return map each device to a list of rules, each rule is a list of 4 tuple condition of
        (deviceName, PTSL_type, inequality, time_interval, possibleStates for the rule)

        We trigger the rule if all of the rule condition is satisfied in the list, and we change the device
        state if at least 1 of the rules is satisfied.
    '''

    parsedict = {}
    devices = cdict.keys()

    for device in devices:
        T = None 
        try: 
            with open("LearnedModel/treemodel/{0}.pkl".format(device), 'rb') as inmodel:
                T = pickle.load(inmodel)
        except FileNotFoundError:
            raise Exception("Learned model not found")
        ruledict = {values: [] for (keys,values) in cdict[device].items()}
        for leaf in findleaves(T):
            if leaf.predError < error_threshold:
                s = getRule(leaf, cdict, cap)
                predclass = leaf.predClass
                ruledict[cdict[device][predclass]].append(s)
        parsedict[device] = ruledict

    return parsedict