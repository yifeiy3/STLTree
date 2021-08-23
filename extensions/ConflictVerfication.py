from z3 import *

class ConflictVerification():
    '''
        A class check for if it is possible to have any direct conflicts between learned rules.
        if possible, the tool will return an example log of device changes showing the conflict

        Method: check pairs first, then combine the conflicts into groups using union find?
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

    def checkDontConflict(self, tempRules, immeRules):
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
                keyname, oper, ineq, intval, statelist, tsunit = rules[i]
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
                        stateConstraint = False
                        for states in statelist:
                            durConstraint = True
                            for k in range(0, dur+1):
                                durConstraint = And(durConstraint, createSTLConstraint(keyname, j+k, ineq, states))
                            stateConstraint = Or(stateConstraint, newConstraint)
                        primConstraint = Or(primConstraint, stateConstraint)
                    constraint = And(constraint, primConstraint) 

                else: #GF case
                    primConstraint = True
                    for j in range(lo, hi-dur+1):
                        stateConstraint = False
                        for states in statelist:
                            durConstraint = False
                            for k in range(0, dur+1):
                                durConstraint = Or(durConstraint, createSTLConstraint(keyname, j+k, ineq, states))
                            stateConstraint = Or(stateConstraint, newConstraint)
                        primConstraint = And(primConstraint, stateConstraint)
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


if __name__ == '__main__':
    deviceInput = {
        'Door_lock': ['locked', 'unlocked'],
        'Virtual Switch 2_switch': ['on', 'off'],
        'Virtual Switch1_switch': ['on', 'off'],
        'Thermostat_temperature': ['75', '95'],
    }
    STLruleInput = {}
    ImmeruleInput = {}
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

    print(cv.checkDontConflict(STLrules, immerule))
    print('\n\n')
    print(cv.valueMap)