import pickle 
from Model.Prim import FLPrimitives, SLPrimitives, Primitives, negateIneq
from UserDefinedRules.parseUserRules import parse 
from dictUtil import addOrAppendDepth2
import itertools

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
    #TODO: this does not handle rules with continued data yet.
    if not statedict:
        return [idx] #continuous data, simply evaluate base on value.
    if ineq == '<':
        return [statedict[i] for i in statedict.keys() if int(i) < idx]
    if ineq == '>':
        return [statedict[i] for i in statedict.keys() if int(i) > idx]
    if ineq == '>=':
        return [statedict[i] for i in statedict.keys() if int(i) >= idx]
    else:
        return [statedict[i] for i in statedict.keys() if int(i) <= idx]

def getRule(T, classdict, cap):
    '''
        Each rule is 5 tuple of:
        (Device Name, PTSL type, ineq, [from last x seconds, to last x seconds, duration], satisfyingStates)
        The list comes in "And", everything need to be satisfied.
    '''
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

        try:
            statedict = classdict[PTSL.dimname]
        except KeyError:
            statedict = {} #if continuous data, can't find in the classdict

        if T.branch == 'left':
            #true branch
            s.append((PTSL.dimname, PTSL_type, PTSL_ineq, PTSL_time_interval, findPossibleStates(statedict, objval, PTSL_ineq)))
        else:
            PTSL_ineq = negateIneq(PTSL_ineq)
            PTSL_type = negateOper(PTSL_type)
            s.append((PTSL.dimname, PTSL_type, PTSL_ineq, PTSL_time_interval, findPossibleStates(statedict, objval, PTSL_ineq)))
        T = T.parent
    return s 

def convertImmediateDoRules(parsedDict):
    '''
        Given a parsed immediate rule dict, convert it to process do rules

        @return a dictionary d, d[deviceName_state][keyTriple] = ruledict
        where key Triple = (negate?, stateBefore, stateAfter) and
        ruledict[device_state][(keyBefore, keyAfter)] = List of rules need to be satisfied 
        for device_state to change from keyBefore to keyAfter.
    '''
    if not parsedDict:
        return None 

    d = {}

    for device in parsedDict.keys():
        for stateChange in parsedDict[device].keys(): 
            allValueRules = parsedDict[device][stateChange]
            #each rule is a five tuple of (device_state, stateBefore, stateAfter, stateChanged?, negate)
            for individualRule in allValueRules:
                for deviceName, stateBefore, stateAfter, changed, negate in individualRule:
                    if not changed and not negate: 
                        #the device stays in the state, not intereting in checking do rules
                        #since we only monitor device changes
                        continue 

                    if deviceName not in d.keys():
                        d[deviceName] = {}
                    
                    deviceDict = d[deviceName]
                    keytriple = (negate, stateBefore, stateAfter)
                    tempdict = {}
                    addOrAppendDepth2(tempdict, device, stateChange, individualRule)
                    deviceDict[keytriple] = tempdict
    
    return d

def convertDoRules(parsedDict):
    '''
        Given a parsed rule dict, we want to convert to another dictionary that is easy for processing do rules,
        the dictionary will be, for a device_state ds change to value v
        d[ds][v] = ruledict, where
        ruledict[device][newValue] = set of rules associates with changing s to v that can change our device to newValue
    '''
    d = {}

    #initialize d with mapping to ruledict, note parseDict should have all devices and their corresponding states as keys already
    for device in parsedDict.keys():
        d[device] = {}
        for newStateValues in parsedDict[device].keys():
            d[device][newStateValues] = {}
    
    for device in parsedDict.keys():
        for newStateValues in parsedDict[device].keys():
            allValueRules = parsedDict[device][newStateValues]
            #a list of rules, each rule is a list of 5 tuple with "and" relation, described in getRule above.
            for individualRule in allValueRules:
                for clause in individualRule:
                    deviceName, _tp, ineq, _ti, possibleStates = clause
                    for eachState in possibleStates:
                        ruledict = {}
                        try:
                            ruledict = d[deviceName][eachState]
                            addOrAppendDepth2(ruledict, device, newStateValues, individualRule)
                        except KeyError:
                            #we have a continuous variable
                            if deviceName not in d.keys():
                                d[deviceName] = {}
                            newstateKey = eachState + '_' + ineq
                            d[deviceName][newstateKey] = {}
                            ruledict = d[deviceName][newstateKey]

                            newkey = newStateValues #add in inequality for rules
                            addOrAppendDepth2(ruledict, device, newkey, individualRule)
    
    return d 

def convertRules(cdict, error_threshold = 0.05, cap = 10, user_defined = None, immediate = True):
    '''
        for a model that we learned device state to be A when B happens, we add a rule dictionary that
        says device should be in the specified state when B happens 

        @param: cdict: the classdict used to train our model
        @param: error_threshold: only rules with confidence higher than this will be considered.
        @param: cap: the interval period we used to divide our dataset during training.
        @param: user_defined: A file describing user defined rules that we would like to be added to the dict
        @param: immediate: whether we check the immediate rules derived from TreeNoSTL

        @return map each device to a list of rules, each rule is a list of 4 tuple condition of
        (deviceName, PTSL_type, inequality, time_interval, possibleStates for the rule)

        if immediate is set to True, we also return a dictionary of immediate rules such that
        dict[device][(startState, endState)] = rule

        We trigger the rule if all of the rule condition is satisfied in the list, and we change the device
        state if at least 1 of the rules is satisfied.
    '''

    parsedict = {}
    parseImmediateDict = {}
    devices = cdict.keys()

    #STL tree defined rules
    for device in devices:
        #note: device = deviceName_deviceState
        T = None 
        try: 
            with open("LearnedModel/treemodel/{0}.pkl".format(device), 'rb') as inmodel:
                T = pickle.load(inmodel)
        except FileNotFoundError:
            print("WARNING: Learned STL model not found for {0}".format(device))
            continue 

        ruledict = {values: [] for (keys,values) in cdict[device].items()}
        for leaf in findleaves(T):
            if leaf.predError < error_threshold:
                s = getRule(leaf, cdict, cap)
                predclass = leaf.predClass
                ruledict[cdict[device][predclass]].append(s)
        parsedict[device] = ruledict

    if user_defined:
        userRuleList = convertUserDefinedRules(user_defined)
        for device, dontStateVal, userRule in userRuleList:
            addOrAppendDepth2(parsedict, device, dontStateVal, userRule)
    
    if immediate:
        gap_dict = None 
        try:
            with open("LearnedModel/treeNoSTLgapDict/gap.pkl", 'rb') as rmodel:
                gap_dict = pickle.load(rmodel)
        except FileNotFoundError:
            gap_dict = None
            print("WARNING: No gap dict found, every continuous variable category is set with default 5")

        for device in devices: 
            immeruledict = None 
            try:
                with open("LearnedModel/treeNoSTLRules/{0}.pkl".format(device), 'rb') as rmodel:
                    immeruledict = pickle.load(rmodel)
            except FileNotFoundError:
                print("WARNING: Learned TreeNoSTL model not found for {0}".format(device))
                continue

            for devices in immeruledict.keys():
                for startState, endState, _stateChg, rulestr in immeruledict[devices]:
                    #parseImmediateDict[devices][(startState, endstate)] = ruleStr
                    #ruleStr =  (deviceName_state, startState, endState, stateChanged?, negate?)
                    addOrAppendDepth2(parseImmediateDict, devices, (startState, endState), rulestr)
    return gap_dict, parseImmediateDict, parsedict

def convertUserDefinedRules(userfile):

    def convertTime(timeduration, timeUnit):
        if timeUnit == 'SECONDS':
            return int(timeduration)
        elif timeUnit == 'MINUTES':
            return 60 * int(timeduration)
        else: #hours
            return 3600 * int(timeduration)

    def handleContinuous(value):
        '''
            Given a continuous value for device, parse the inequality. 
            The continuous value is specified as GREATER THAN xxx/LESS THAN xxx etc.
        '''
        if 'GREATER EQUAL THAN ' in value:
            return '>=', value.lstrip('GREATER EQUAL THAN ')
        elif 'GREATER THAN ' in value:
            return '>', value.lstrip('GREATER THAN ')
        elif 'LESS THAN ' in value:
            return '<', value.lstrip('LESS THAN ')
        elif 'LESS EQUAL THAN ' in value:
            return '<=', value.lstrip('LESS EQUAL THAN ')
        else: #not a continuous variable
            return '=', value

    ruleList = []
    with open(userfile, 'r') as rulefile:
        for rules in rulefile:
            req, cond = parse(rules)
            #by parse, precond = (deviceMethod, device)
            #timeprecond = (Time duration, Time unit)
            precond, timeprecond = req 
            device, dontstateVal = precond 
            timedur, timeu = timeprecond
            afterTime = convertTime(timedur, timeu) #AFTER xxx seconds 

            #obtain cartisian product of each item in cond, since they occur in 'or' relation within each item,
            #and between items give and relation
            allrulecombs = list(itertools.product(*cond))
            for items in allrulecombs:
                individualRuleList = []
                for ruletuples in items:
                    deviceInfo, timeInfo = ruletuples
                    deviceName = deviceInfo[1] + '_' + deviceInfo[0] #format: deviceName_deviceState
                    possibleIneq, possibleState = handleContinuous(deviceInfo[2]) #handle continuous data

                    if timeInfo[2] == 'FG':
                        secondaryTime, primaryTime = timeInfo[0].split('+')
                        secondaryDur, primaryDur = timeInfo[1].split('+')
                        durTimeSecondary = convertTime(secondaryTime, secondaryDur)
                        durTimePrimary = convertTime(primaryTime, primaryDur)
                        timeBound = (afterTime + durTimePrimary, afterTime, durTimeSecondary)
                        individualRuleList.append((deviceName, timeInfo[2], possibleIneq, timeBound, [possibleState]))
                    else:
                        durTime = convertTime(timeInfo[0], timeInfo[1])
                        lb = afterTime + durTime
                        timeBound = (lb, afterTime, -1)
                        individualRuleList.append((deviceName, timeInfo[2], possibleIneq, timeBound, [possibleState]))
                        
            ruleList.append((device, dontstateVal, individualRuleList))
    return ruleList

if __name__ == '__main__':
    cdict = {}
    # userRuleList = convertUserDefinedRules('./UserDefinedRules/rule.txt')
    # print(userRuleList)
    with open("LearnedModel/training_classdict.pkl", "rb") as dictfile:
        cdict = pickle.load(dictfile)
    #doDict = convertDoRules(convertRules(cdict, user_defined='UserDefinedRules/rule.txt'))
    print(cdict.keys())
    gapd, immediate, xd = convertRules(cdict)
    simple_imme = immediate['Door_lock']
    print("Immediate Rules: {0}".format(simple_imme))
    print("________________________________________")
    print("Converted Immediate Rules: {0}".format(convertImmediateDoRules({'Door_lock':simple_imme})))
    # for keys in doDict.keys():
    #     print("key: {0}".format(keys))
    #     print(doDict[keys])
    #     print('_____________________________________________')