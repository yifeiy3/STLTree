from z3 import *
import itertools
import pickle 

def LogToString(events):
    s = ''
    for items in events:
        s += '{0},\n\t\t'.format(items)
    return s 

class ConflictVerification():
    '''
        A class check for if it is possible to have any direct conflicts between learned rules.
        if possible, the tool will return an example log of device changes showing the conflict
    '''
    def __init__(self, devices, tempDontrules, immeDontrules, gapdict, timebound):
        ''' 
            @param deviceDict: the dictionary mapping device state tuple to their possible state values
            @param gapdict: a dictionary specifying the gaps used to generate immediate rules for continuous
            variables
            @param timebound: the maximum timestamp hi can be for temporal rules
        '''
        self.deviceDict = devices
        self.STLRule = tempDontrules
        self.immeRule = immeDontrules
        self.gapdict = gapdict 
        self.valueMap = self._convertValueMap(self.deviceDict)
        self.timebound = timebound
    
    def _convertValueMap(self, devicedict):
        '''
            create a dictionary that maps discrete device states values to indices since z3 solver can not take in strings
        '''
        valuemap = {}
        for devices in devicedict.keys():
            d = {}
            continuous = False
            for i in range(len(devicedict[devices])):
                stateval = devicedict[devices][i]
                try:
                    int(stateval)
                except ValueError:
                    d[stateval] = i
                else: #dont care about continuous variables
                    continuous = True
                    break 
            if not continuous:
                valuemap[devices] = d
        return valuemap

    def checkConflict(self, tempRules, immeRules):
        '''
            @param: a list of temporal/immediate rules we want to check for conflicts, that is, if it is possible to generate
            a set of devie change logs that satisfy the conditions for all of the rules

            @return: a tuple, (conflict?, log if conflict)
                     log will be a list of 4-tuples, each of item
                     (timestamps from current time, device, state, value)
        '''
        def createSTLConstraint(variableName, index, ineq, state):
            value = -1
            tempName = '{0}_{1}'.format(variableName, index)

            try:
                value = int(state)
            except ValueError: #discrete state
                return Int(tempName) == self.valueMap[variableName][state] 
            else:
                bounds = self.deviceDict[variableName]
                lb, ub = bounds[0], bounds[1]
                tempvar = Int(tempName)
                if ineq == '>':
                    return And(tempvar > value, tempvar <= ub)
                elif ineq == '>=':
                    return And(tempvar >= value, tempvar <= ub) 
                elif ineq == '<':
                    return And(tempvar < value, tempvar >= lb) 
                else:
                    return And(tempvar <= value, tempvar >= lb)

        def createImmeConstraint(variableName, index, state):
            value = -1
            tempName = '{0}_{1}'.format(variableName, index)

            try:
                value = int(state)
            except ValueError:
                return Int(tempName) == self.valueMap[variableName][state] 
            else:
                gap = self.gapdict[variableName]
                tempvar = Int(tempName)
                return And(tempvar >= value, tempvar < value + gap)

        constraint = True 
        #add in constraints for temporal rules
        for rules in tempRules:
            for i in range(len(rules)):
                keyname, oper, ineq, intval, statelist, _tsunit = rules[i]
                hi, lo, dur = intval

                if oper == 'G':
                    primConstraint = True
                    for j in range(lo, hi+1):
                        stateConstraint = False
                        for states in statelist:
                            newConstraint = createSTLConstraint(keyname, j, ineq, states)
                            stateConstraint = Or(stateConstraint, newConstraint)
                        primConstraint = And(primConstraint, stateConstraint)
                    constraint = And(constraint, primConstraint)
                
                elif oper == 'F':
                    primConstraint = False
                    for j in range(lo, hi+1):
                        stateConstraint = False
                        for states in statelist:
                            newConstraint = createSTLConstraint(keyname, j, ineq, states)
                            stateConstraint = Or(stateConstraint, newConstraint)
                        primConstraint = Or(primConstraint, stateConstraint)
                    constraint = And(constraint, primConstraint)
                            
                elif oper == 'FG':
                    primConstraint = False
                    for j in range(lo, hi-dur+1):
                        durConstraint = True 
                        for k in range(0, dur+1):
                            stateConstraint = False 
                            for states in statelist:
                                stateConstraint = Or(stateConstraint, createSTLConstraint(keyname, j+k, ineq, states))
                            durConstraint = And(durConstraint, stateConstraint)
                        primConstraint = Or(primConstraint, durConstraint)
                    constraint = And(constraint, primConstraint) 

                else: #GF case
                    primConstraint = True
                    for j in range(lo, hi-dur+1):
                        durConstraint = False
                        for k in range(0, dur+1):
                            stateConstraint = False
                            for states in statelist:
                                stateConstraint = Or(stateConstraint, createSTLConstraint(keyname, j+k, ineq, states))
                            durConstraint = Or(durConstraint, stateConstraint)
                        primConstraint = And(primConstraint, durConstraint)
                    constraint = And(constraint, primConstraint)           
        
        #add in constraints for immediate rules
        for imrules in immeRules:
            for i in range(len(imrules)):
                keyname, beforeState, afterState, _stateChange, negate, _ts = imrules[i]
                #just need to be afterState at timestamp 0, and beforeState at timestamp 1. for both statechange and not statechange cases.
                if not negate:
                    stateConstraint = And(createImmeConstraint(keyname, 1, beforeState), createImmeConstraint(keyname, 0, afterState))
                    constraint = And(constraint, stateConstraint)

                else: #negate is true. the timestamps at 0 and 1 can be of any state except the combination given by (beforeState, afterState)
                    possibleStates = []
                    for before in self.deviceDict[keyname]:
                        for after in self.deviceDict[keyname]:
                            if before != beforeState or after != afterState:
                                possibleStates.append((before, after))

                    stateConstraint = False  
                    for bstate, astate in possibleStates:
                        stateConstraint = Or(stateConstraint, And(createImmeConstraint(keyname, 1, bstate), createImmeConstraint(keyname, 0, astate)))
                    constraint = And(constraint, stateConstraint)

        s = Solver()
        s.add(constraint)
        res = s.check()  
        if res == sat: #satisfied
            m = s.model()
            return True, self._generateLog(m)
        else:
            return False, []
    
    def _generateLog(self, model):
        '''
            given a conflict can be achieved from our SAT solver, 
            generate a log of device changes to reflect the conflict.
            @param model: The sat solver model.
        '''
        resultdict = {}
        resultlog = []

        for d in model.decls():
            resultdict[d.name()] = model[d].as_long()

        for devices in self.deviceDict.keys():
            dname, dstate = devices.rsplit('_', -1)
            lastval = -1
            for i in range(self.timebound, -1, -1):
                varname = '{0}_{1}'.format(devices, i)
                if varname not in resultdict.keys():
                    continue #the timestamp is irrelevant in or conflict generation. 
                stateval = resultdict[varname]
                if stateval != lastval: #we only need a state change if assigned value is different.
                    if devices not in self.valueMap.keys() and stateval >= int(self.deviceDict[devices][0]) and stateval <= int(self.deviceDict[devices][1]):
                        #continuous variable with a relevant state change, add to our log
                        resultlog.append((i, dname, dstate, str(stateval)))
                        lastval = stateval
                    elif devices in self.valueMap.keys() and stateval >= 0 and stateval < len(self.deviceDict[devices]):
                        #discrete variable with a relevant state change, convert it to the corresponding value the index matches
                        strval = self.deviceDict[devices][stateval]
                        lastval = stateval
                        resultlog.append((i, dname, dstate, strval))
                    #otherwise, there could be random values our sat solver assigns, they are irrelevant for state changes, we can just keep it as it is. 
        
        return sorted(resultlog, key = lambda x: -x[0]) #we want sorted so that the event with timestamps farthest away to be on top

    def _conflictGen(self):
        '''
            From the envirionment's temporal rule and immediate rule sets, generate a list of all the possible combination
            of rules possibly giving conflicts for our tool to check.
        '''
        def delete_multiple_element(list_obj, indices):
            indices = sorted(indices, reverse=True)
            for idx in indices:
                if idx < len(list_obj):
                    list_obj.pop(idx)
            return list_obj

        def powerset(iterable, minlength):
            '''
                @param minlength: each item within the result must have at least minlength members
            '''
            s = list(iterable)
            return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(minlength, len(s) + 1))

        def generateImmediate(device, valuesToPick, ruleConflict, STLpickedvalues):
            '''
                Given an already generated ruleConflict list for STL rules, we add in
                immediate rules to the list from values specified in valuesToPick to check for 
                conflicts together.

                Note: for a immediate rule to have conflict, they must have the same beforeState
                but different afterState.

                @param: valuesToPick: the associated values for immediate rules to pick
                @param: ruleConflict: the picked STL rules to check conflict
                @param: STLpickedvalues: the values associated with picked STL rules.
                @return a list of tuple (values picked for STL, startval, valuestopick, ruleConflict, generatedimmediateRules)
            '''
            if device not in self.immeRule.keys():
                return [] #no immediate rule about this, simply skip by returning empty
            result = []
            availableBeforeStates = self.deviceDict[device]
            
            startStates = []
            for bstate in availableBeforeStates:
                validStart = True
                for values in valuesToPick:
                    if (bstate, values) not in self.immeRule[device].keys():
                        validStart = False
                        break 
                if validStart:
                    startStates.append(bstate)
            
            for start in startStates:
                vRules = []
                for values in valuesToPick:
                    vRules.append(self.immeRule[device][(start, values)])

                for elements in itertools.product(*vRules):
                    result.append((STLpickedvalues, start, valuesToPick, ruleConflict, elements))
            return result

        ruledict = {} #a dictionary mapping device_state to (STLrule, immerules) to check for conflict

        valuedict = {} #map device values to the corresponding index in the cartesian product.

        for devices in self.deviceDict.keys():
            valueRules = []
            valuedict[devices] = {}
            index = 0
            for values in self.deviceDict[devices]:
                try:
                    rules = self.STLRule[devices][values]
                except KeyError: #no rules regarding the device, but it still should be included in the tuple since there can be immediate rules
                    rules = []
                temprule = []
                for items in rules:
                    temprule.append(items) 
                temprule.append([]) #add in an empty list for the case none of the rule for that value is picked for conflict analysis
                valuedict[devices][index] = values
                index += 1
                valueRules.append(temprule)

            allpossible = itertools.product(*valueRules) #cartesian product

            reslist = []
            for elements in allpossible:
                notpicked = []
                picked = []

                for i in range(index):
                    if elements[i] == []:
                        notpicked.append(i) #record all the not picked values for STL rules, we can interlace with immediate rules
                    else:
                        picked.append(i)
                
                notpickedvalues = [valuedict[devices][idxs] for idxs in notpicked]
                pickedvalues = [valuedict[devices][idxs] for idxs in picked]

                STLRule = delete_multiple_element(list(elements), notpicked)  #delete all the not picked entry

                if len(picked) > 1: #at least 2 temporal rule is picked, we can check for conflict
                    reslist.append((pickedvalues, '', [], STLRule, []))

                #we can pick any element of the powerset for notpickedvalues to test for conflict
                if len(notpicked) == index: #no STL rules, just immediate rules only
                    possibleCombinationNotPicked = powerset(notpickedvalues, 2) #we need at least 2 rules to check
                else:
                    possibleCombinationNotPicked = powerset(notpickedvalues, 1)

                for notpickedcombinations in possibleCombinationNotPicked:
                    reslist += generateImmediate(devices, notpickedcombinations, STLRule, pickedvalues)
            
            ruledict[devices] = reslist 
        
        return ruledict

    def conflictAnalysis(self, outfile, resultdict):
        '''
            Analyze all the potential direct conflicts in our environment defined by the temporal and immediate rules

            A direct conflict is defined by having a log that satisfies conditions for two rules specifying different
            behaviors at the same time.

            @param: outfile: output file for logging all the possible conflicts.
            @param: resultdict: a pickle uploaded file on a list of 3-tuple: (STLrules, Immerules, Log) for rules that
            has a conflict, this is used to simulate on Samsung Smarthub.
        '''
        
        ruledict = self._conflictGen()
        conflicts = []

        with open(outfile, 'w') as out:
            for devices in ruledict.keys():
                out.write("Rule conflicts for device: {0} \n\n".format(devices))
                count = 1

                for pickedSTLval, beforeState, valuesToPick, STLrules, Immerules in ruledict[devices]:
                    checkResult, log = self.checkConflict(STLrules, Immerules)
                    if checkResult: #a conflict happened
                        out.write("{0} \n\t".format(count))
                        for i in range(len(STLrules)):
                            assovalue = pickedSTLval[i]
                            rule = STLrules[i]
                            out.write("Value:{0} \n\tRule:{1}\n\t".format(assovalue, rule))

                        for i in range(len(Immerules)):
                            assovalue = valuesToPick[i]
                            rule = Immerules[i]
                            out.write("BeforeValue:{0}, AfterValue:{1} \n\tRule:{2}\n\t".format(beforeState, assovalue, rule))

                        out.write("With example violation log: \n\t\t{0}\n\n".format(LogToString(log)))
                        conflicts.append((STLrules, Immerules, log))
                        count += 1

        with open(resultdict, 'wb') as outLog:
            pickle.dump((self.timebound, conflicts), outLog, protocol=pickle.HIGHEST_PROTOCOL)

if __name__ == '__main__':
    deviceInput = {
        'Door_lock': ['locked', 'unlocked'],
        'Virtual Switch 2_switch': ['on', 'off'],
        'Virtual Switch1_switch': ['on', 'off'],
        'Thermostat_temperature': ['75', '95'],
    }
    STLruleInput = {'Virtual Switch 2_switch': {'on': [[('Virtual Switch1_switch', 'F', '>=', (4, 3, -1), ['off'], 'seconds')], [('Virtual Switch1_switch', 'GF', '>', (9, 8, 1), ['off'], 'seconds'), ('Door_lock', 'GF', '<', (1, 0, 1), ['locked'], 'seconds')]], 'off': [[('Virtual Switch1_switch', 'F', '>', (8, 3, -1), ['off'], 'seconds'), ('Door_lock', 'G', '<=', (5, 3, -1), ['locked'], 'seconds')], [('Thermostat_temperature', 'FG', '>', (7, 3, 2), ['90'], 'seconds'), ('Virtual Switch1_switch', 'GF', '>=', (6, 5, 1), ['off'], 'seconds'), ('Door_lock', 'F', '>', (4, 2, -1), ['unlocked'], 'seconds')]]}, 'Door_lock': {'locked': [[('Virtual Switch 2_switch', 'G', '>=', (3, 2, -1), ['off'], 'seconds')], [('Thermostat_temperature', 'GF', '<=', (10, 4, 3), ['89'], 'seconds'), ('Virtual Switch1_switch', 'FG', '>=', (1, 0, 1), ['off'], 'seconds'), ('Virtual Switch 2_switch', 'F', '<=', (10, 9, -1), ['on'], 'seconds')]], 'unlocked': [[('Virtual Switch 2_switch', 'G', '>=', (2, 0, -1), ['off'], 'seconds')]]}, 'Virtual Switch1_switch': {'on': [[('Door_lock', 'F', '<', (9, 0, -1), ['locked'], 'seconds')]], 'off': [[('Thermostat_temperature', 'GF', '>=', (3, 0, 1), ['85'], 'seconds'), ('Thermostat_temperature', 'FG', '>=', (2, 0, 1), ['85'], 'seconds'), ('Door_lock', 'FG', '<=', (8, 2, 2), ['locked'], 'seconds')]]}} 
    ImmeruleInput = {'Virtual Switch 2_switch': {('off', 'on'): [[('Thermostat_temperature', '83', '83', False, False, 'seconds'), ('Virtual Switch1_switch', 'on', 'off', True, True, 'seconds'), ('Thermostat_temperature', '91', '91', False, False, 'seconds')]]}} 
    
    gapdict = {'Thermostat_temperature': 4}
    cv = ConflictVerification(deviceInput, STLruleInput, ImmeruleInput, gapdict, 10)

    STLrules = [
        [('Thermostat_temperature', 'F', '<', (2, 1, -1), ['80'], 'seconds'), ('Door_lock', 'G', '>', (7, 4, -1), ['unlocked'], 'seconds')],
        [('Thermostat_temperature', 'F', '<', (2, 1, -1), ['76'], 'seconds'), ('Door_lock', 'G', '>', (3, 1, -1), ['unlocked'], 'seconds')]
    ]
    immerule = [
        [('Door_lock', 'unlocked', 'unlocked', True, True, 'seconds'), ('Virtual Switch 2_switch', 'off', 'off', True, False, 'seconds'), 
        ('Virtual Switch 2_switch', 'off', 'on', False, True, 'seconds')], 
    ]

    cv.conflictAnalysis('analysisResult.txt', 'analysisResult.pkl')