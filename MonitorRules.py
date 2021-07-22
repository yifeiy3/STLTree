from ParseRules import convertDoRules, convertImmediateDoRules
import datetime
import time 
import functools
import copy
import math

def sec_diff(date_ref, date, timestampunit):
    '''
        compute the second diff between date timestamps, hardcode style
        Date format is IsoDate for devices: yyyy-MM-ddThh:mm:ss
    '''
    #we would at most have last 7 days of data so no need to worry about year 
    month_diff = int(date[5:7]) - int(date_ref[5:7])
    month_gap = 30
    if month_diff > 0:
        if int(date_ref[5:7]) in [1, 3, 5, 7, 8, 10, 12]:
            month_gap = 31 
        elif int(date_ref[5:7]) == 2:
            if(int(date_ref[0:4]) % 4 == 0):
                month_gap = 29
            else:
                month_gap = 28 
    day_diff = int(date[8:10]) - int(date_ref[8: 10]) + month_diff * month_gap
    hour_diff = int(date[11:13]) - int(date_ref[11:13])
    minute_diff = int(date[14:16]) - int(date_ref[14:16])
    sec_diff = int(date[17: 19]) - int(date_ref[17:19])
    diff = day_diff * 86400 + hour_diff * 3600 + minute_diff * 60 + sec_diff
    if timestampunit == 'minutes':
        return diff//60
    else:
        return diff 

class MonitorRules():
    def __init__(self, rules, immediateRules, gapdict, devices, max_states = 5, do=True):
        '''
            @param: rules: rules learned from STLTree
            @param: immediateRules: immediate rules learned from TreeNoSTL
            @param: gapdict: dictionary maps immediate continuous variables to the gap for separating categories, 
            if not found the gap is set to 5.
            @devices: devices in the environment
            @param: max_states: maximum number of states for each device our monitor stores
            @param: whether we track for DO rules, that is, if a rule condition gets satisfied but no device change has
            happened, the monitor automatically commands the device to change after a fixed amount of time.
        '''
        self.devices = devices 
        self.deviceStates = self._initializeState(devices)
        self.rules = rules #dont rules received from ParseRules.py 
        self.doRules = convertDoRules(rules) if do else None
        self.immediateRules = immediateRules
        self.gapdict = gapdict if gapdict else {}
        self.doimmediateRules = convertImmediateDoRules(immediateRules) if do else None
        self.max_states = max_states
    
    def _initializeState(self, devices):
        deviceState = {}
        for device in devices:
            deviceState[device] = {}
        return deviceState 
    
    def updateState(self, date, device, state, value):
        if device not in self.deviceStates: #we have a continuous variable
            self.deviceStates[device] = {}

        if state not in self.deviceStates[device]:
            self.deviceStates[device][state] = [(date, value)]
        else:
            st = self.deviceStates[device][state]
            if len(st) >= self.max_states:
                st.pop(0)
            st.append((date, value))

    def _checkValid(self, possibleStates, oper, value):
        '''
            check if the current value satisfies the rule. 
            
            if value discrete, simply check if it is in the possibleStates
            otherwise, convert it to int to compare value with oper
        '''
        intval = -1
        try:
            intval = int(value)
        except ValueError: #discrete value
            return value in possibleStates
        if oper == '<':
            return intval < int(value)
        elif oper == '<=':
            return intval <= int(value)
        elif oper == '>':
            return intval > int(value)
        else:
            return intval >= int(value)

    def _checkPTSL(self, currdate, oper, interval, possibleStates, currentStates, tsunit):
        hi, lo, gap = interval

        if oper == 'F':
            validStates = [(sec_diff(date, currdate, tsunit), value) for (date, value) in currentStates if self._checkValid(possibleStates, oper, value)]
            for date, value in validStates:
                if date <= hi and date >= lo:
                    return True  
            return False 

        elif oper == 'G':
            satisfied = True 
            first_idx = -1 #first occurence of the index greater or equal date range. i.e what the device is like before date range
            last_idx_outside_range = -2 #last idx happens before hi, used when no state change has happened within the data range
            for i in range(len(currentStates)):
                #Note current states is stored such that the first element is farthest away.
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate, tsunit)
                if datediff >= lo and datediff <= hi:
                    if first_idx < 0:
                        first_idx = i 
                    satisfied = satisfied and self._checkValid(possibleStates, oper, value)
                if datediff > hi:
                    last_idx_outside_range = i 

            first_idx = last_idx_outside_range + 1 if first_idx < 0 else first_idx

            if first_idx < 0:
                return False #we have no idea what happens within date range
            elif first_idx == 0:
                satisfied = self._checkValid(possibleStates, oper, currentStates[first_idx][1]) 
                satisfied = satisfied and sec_diff(currentStates[first_idx][0], currdate, tsunit) >= hi 
            else:
                date, value = currentStates[first_idx-1]
                satisfied = satisfied and self._checkValid(possibleStates, oper, value) #last state change before date range is valid 
            return satisfied

        elif oper == 'FG':
            for i in range(len(currentStates)):
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate, tsunit)
                print("datediff: {0}".format(datediff))
                if datediff <= hi and datediff >= lo and self._checkValid(possibleStates, oper, value):
                    j = i+1
                    if j >= len(currentStates):
                        return True # no state change has happend since. 
                    while j < len(currentStates):
                        t_date, t_value = currentStates[j]
                        t_datediff = sec_diff(t_date, currdate, tsunit)
                        if datediff - t_datediff > gap:
                            return True 
                        else:
                            if not self._checkValid(possibleStates, oper, t_value):
                                break 
                            j = j+1
            return False #no F has happend

        else: #GF case 
            if ((hi - lo) // gap > self.max_states):
                #simply not possible
                return False 
            possibleIntervals = [(max(x-gap, 0), x) for x in range(lo, hi, 1)] #we need 1 satisfying state change for each of these intervals
            validStates = [(sec_diff(date, currdate, tsunit), value) for (date, value) in currentStates if self._checkValid(possibleStates, oper, value)]
            for lo_int, hi_int in possibleIntervals:
                hasSatisfied = False
                for date, value in validStates:
                    if date >= lo_int and date <= hi_int:
                        hasSatisfied = True 
                        break 
                if not hasSatisfied: #it must be satisfied for each interval
                    return False 
            return True 

    def _checkOneRule(self, rule, currdate):
        satisfied = True 
        for keyname, oper, _ineq, intval, stateList, tsunit in rule: 
            parseName = keyname.rsplit('_', 1)
            dname, dstate = parseName[0], parseName[1]
            if dname not in self.deviceStates:
                return False #continuous variable not encountered, we dont know states
            statedict = self.deviceStates[dname]
            if dstate not in statedict:
                return False #we don't know the device state, so we can't infer anything
            satisfied = satisfied and self._checkPTSL(currdate, oper, intval, stateList, statedict[dstate], tsunit)
        return satisfied

    def _checkRules(self, currChg):
        currdate, currdevice, currState, currValue = currChg
        keyname = "{0}_{1}".format(currdevice, currState)
        if keyname not in self.rules:
            return True, currValue #no rules about this device, we can just continue, this should also skip all continuous variable devices
        ruledict = self.rules[keyname]
        keys = [key for key in ruledict.keys() if key != currValue]
        #we only need to worry about the rules that does not match curr value being satisfied
        for key in keys:
            for rules in ruledict[key]:
                if self._checkOneRule(rules, currdate):
                    return False, key #the device should be in this state instead 
        return True, currValue

    def _checkPTSLonDO(self, currdate, oper, interval, possibleStates, currentStates, offsetInfo, tsunit):
        '''
            @return a tuple: (Rule satisfied?, Possible starting intervals for rule to be satisfied)
        '''
        offsethi, offsetlo, offsetgap, offsetPSTL = offsetInfo
        offsetgap = max(0, offsetgap) #since for first level PSTL we set offsetgap to be -1
        offsethi, offsetlo = offsethi, offsetlo + offsetgap #add gap for FG rules.

        hi, lo, gap = interval 
        satisfied = False 
        #if its of rule G or GF, we have to wait at least offsethi seconds for our action rule
        #to be true, but we can wait for as long as we want assuming no state change happens.
        if offsetPSTL == 'G' or offsetPSTL == 'GF': 
            offsetlo = offsethi
            offsethi = math.inf

        if oper == 'G': 
            satisfied = True 
            first_idx = -1
            last_idx_outside_range = -2
            modifiedintvalhi, modifiedintvallo = (max(0, hi - offsetlo), max(0, lo - offsethi))

            intvStart = -1
            startDate = -1
            satisfyingIntvList = []
            for i in range(len(currentStates)):
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate, tsunit)
                if datediff >= modifiedintvallo and datediff <= modifiedintvalhi:
                    if first_idx < 0:
                        first_idx = i 
                    if intvStart < 0 and self._checkValid(possibleStates, oper, value):
                        #have to wait hi amount of seconds for G.
                        intvStart = max(offsetlo, hi - datediff)
                        startDate = datediff 
                    elif intvStart >= 0 and not self._checkValid(possibleStates, oper, value):
                        satisfyingIntvList.append((intvStart, intvStart + (startDate - datediff)))
                        intvStart = -1
                        startDate = -1
                if datediff > modifiedintvalhi:
                    last_idx_outside_range = i 

            first_idx = last_idx_outside_range + 1 if first_idx < 0 else first_idx

            if intvStart >= 0 and intvStart + (hi - lo + 1) <= offsethi: #everything after will be satisfied, append this
                satisfied = True
                satisfyingIntvList.append((intvStart, offsethi)) #check behavior before the first interval

            firstStart, firstEnd = -1, -1
            if satisfyingIntvList:
                firstStart, firstEnd = satisfyingIntvList[0]

            if first_idx < 0:
                return False, [] 
            elif first_idx == 0: #nothing happened before the interval
                print("first index = 0, nothing to be done here")
            elif first_idx == len(currentStates): #nothing happened within the interval
                satisfyingIntvList = [(offsetlo, offsethi)]
            else:
                date, value = currentStates[first_idx - 1]
                nextdate, _nextvalue = currentStates[first_idx]
                if sec_diff(nextdate, currdate, tsunit) < modifiedintvallo: #nothing happened within the interval
                    return satisfied, [(offsetlo, offsethi)]
                    
                if self._checkValid(possibleStates, oper, value) and nextdate == firstStart: #then any time before our first interval also works, extend our interval.
                    satisfyingIntvList.pop(0)
                    satisfyingIntvList.insert(0, (offsetlo, firstEnd))

            reslist = []
            #for each found interval, we need to know that they have to be at least the size of [lo, hi].
            for start, end in satisfyingIntvList:
                duration = (end - start) - (hi - lo)
                if duration >= 0:
                    reslist.append((start, start + duration))
            return len(reslist) > 0, reslist
            
        elif oper == 'F':
            pStates = [(sec_diff(date, currdate, tsunit), value) for (date, value) in currentStates]
            #Since the action rule for F or FG can be immediately satisfied after offsetlo seconds have passed.
            modifiedintvalhi, modifiedintvallo = (max(0, hi - offsetlo), max(0, lo - offsethi))
            satisfyingIntvList = []
            for date, value in pStates:
                if date <= modifiedintvalhi and date >= modifiedintvallo:
                    if self._checkValid(possibleStates, oper, value):
                        #we have to wait at least lo - date seconds to satisfy rule
                        intvStart = lo - date
                        satisfied = True 
                        #we can't wait more than (hi - lo) seconds from intvStart, since then the intvStart event won't
                        #satisfy our rule anymore.
                        endpoint = min(intvStart + (hi - lo), offsethi)
                        if endpoint >= offsetlo:
                            intvStart = max(offsetlo, intvStart) #we have to wait at least offsetlo seconds
                            satisfyingIntvList.append((intvStart, endpoint))
                            
            #we do a post processing to avoid overlaps, we note the start time for interval must appear in order
            reslist = []
            currstartpt, currendpt = -1, -1
            for startpt, endpt in satisfyingIntvList:
                if startpt < currendpt: #overlapping interval, we extend.
                    if endpt > currendpt:
                        currendpt = endpt 
                else: #a separated interval 
                    reslist.append((currstartpt, currendpt))
                    currstartpt = startpt 
                    currendpt = endpt
            reslist.append((currstartpt, currendpt)) #add in last interval
            return satisfied, reslist[1:]
        
        elif oper == 'FG':
            satisfyingIntvList = []

            for i in range(len(currentStates)):
                date, value = currentStates[i]
                modifiedintvalhi, modifiedintvallo = (max(0, hi - offsetlo), max(0, lo - offsethi))
                datediff = sec_diff(date, currdate, tsunit)
                if datediff <= modifiedintvalhi and datediff >= modifiedintvallo:
                    if intvStart < 0 and self._checkValid(possibleStates, oper, value):
                        j = i+1
                        if j >= len(currentStates):
                            satisfied = True 
                            intvStart = lo - datediff
                            endpoint = min(intvStart + (hi - lo), offsethi)
                            if endpoint >= offsetlo:
                                intvStart = max(offsetlo, intvStart)
                                satisfyingIntvList.append((intvStart, endpoint))
                        else:
                            while j < len(currentStates):
                                t_date, _t_value = currentStates[j]
                                t_datediff = sec_diff(t_date, currdate, tsunit)
                                if intvStart < 0 and datediff - t_datediff > gap:
                                    satisfied = True 
                                    intvStart = lo - datediff
                                    endpoint = min(intvStart + (hi - lo), offsethi)
                                    if endpoint >= offsetlo:
                                        intvStart = max(offsetlo, intvStart)
                                        satisfyingIntvList.append((intvStart, endpoint))
                                    break
                                j = j+1
            
            #post processing to avoid overlaps
            reslist = []
            currstartpt, currendpt = -1, -1
            for startpt, endpt in satisfyingIntvList:
                if startpt < currendpt: #overlapping interval, we extend.
                    if endpt > currendpt:
                        currendpt = endpt 
                else: #a separated interval 
                    reslist.append((currstartpt, currendpt))
                    currstartpt = startpt 
                    currendpt = endpt
            reslist.append((currstartpt, currendpt)) #add in last interval
            return satisfied, reslist[1:]
        
        else: #GF case
            intvStart = -1
            satisfyingIntvList = []

            #if i > lo, we cant check for globally all satisfiable since we dont know events yet, can simply skip.
            rangeend = min(offsethi+1, lo + 1)

            for i in range(offsetlo, rangeend, 1):
                modifiedhi, modifiedlo = (hi-i, lo - i)

                validStates = []
                for date, value in currentStates[: -1]:
                    datediff = sec_diff(date, currdate, tsunit)
                    if datediff <= modifiedhi and datediff >= modifiedlo and self._checkValid(possibleStates, oper, value):
                        validStates.append((datediff, value))

                lastStateAdded = False 
                dateLast, dateValue = currentStates[-1]
                dateLastDiff = sec_diff(dateLast, currdate, tsunit)
                if dateLastDiff <= modifiedhi and dateLastDiff >= modifiedlo:
                    if self._checkValid(possibleStates, oper, dateValue):
                        validStates.append((dateLastDiff, dateValue))    
                    lastStateAdded = True 
            
                if ((hi - lo) // gap > len(validStates)): #have more non overlapping intervals than state changes
                    if lastStateAdded:
                        return satisfied, satisfyingIntvList 
                        #any interval happening after will not satisfy our rule since not enough changes for intervals
                    continue

                possibleIntervals = [(max(x-gap, 0), x) for x in range(modifiedlo, modifiedhi+1, 1)]

                currentlySatisfied = True #whether our current choice of i satisfy the rule

                for lo_int, hi_int in possibleIntervals:
                    hasSatisfied = False
                    for date, value in validStates:
                        if date >= lo_int and date <= hi_int:
                            hasSatisfied = True 
                            break
                    #None of the valid states satisfies our rule
                    if not hasSatisfied:
                        if intvStart >= 0:
                            satisfyingIntvList.append((intvStart, i-1))
                            intvStart = -1
                        currentlySatisfied = False 
                        break
                
                #all intervals have been satisfied.
                if currentlySatisfied and intvStart < 0:
                    intvStart = i 
                    satisfied = True

            if intvStart > 0:
                satisfyingIntvList.append((intvStart, min(intvStart + (hi - lo), rangeend)))
            return satisfied, satisfyingIntvList
        
    def _findWaitTime(self, timeIntervals, offsetInfo):
        '''
            Given a list of interval constraint list, check for a wait time that satisfy at least one
            interval constraint for each list.

            @param: The time interval constraint list list
            @param: offsetInfo, used when the rule for current event is either F or FG, and it is the only clause
                    of the rule. In that case we need to wait for at least offsetlo's seconds.
            @return: A satisfactory wait time, -1 if none found
        '''
        def compareFn(item1, item2):
            '''
                compare an interval tuple, if they have the same timestamp, 'L' is prioritized ahead of 'R'
            '''
            if item1[0] == item2[0]:
                if item1[1] == item2[1]:
                    return 0
                elif item1[1] == 'L':
                    return -1
                else:
                    return 1
            elif item1[0] < item2[0]:
                return -1
            else:
                return 1
                
        if not timeIntervals:
            #this happens when only current change is in the rule, so the rule is satisfied trivially
            #if its F or FG, we return modified offsetLo, if its G or GF, we return modified offsetHi
            if offsetInfo[3] == 'G' or offsetInfo[3] == 'GF':
                return offsetInfo[0] + max(0, offsetInfo[2])
            else:
                return offsetInfo[1] + max(0, offsetInfo[2])

        #we note each interval with in a list would not overlap by our construction, our goal is simply to check
        #if there is len(timInterval) amount of interval overlap in the provided intervals.
        allIntVals = [item for sublist in timeIntervals for item in sublist] #flattens our list.
        startFinishList = []
        for intStart, intEnd in allIntVals:
            startFinishList.append((intStart, 'L'))
            startFinishList.append((intEnd, 'R'))
        sortedIntVals = sorted(startFinishList, key=functools.cmp_to_key(compareFn)) 

        count = 0
        maxcount = 0
        startWithMaxOverlap = -1
        for timesec, desc in sortedIntVals:
            if desc == 'L':
                count += 1 
                if count > maxcount:
                    maxcount = count 
                    startWithMaxOverlap = timesec
            else: #desc = 'R'
                count -= 1
        
        if maxcount >= len(timeIntervals):
            return startWithMaxOverlap
        else:
            return -1

    def _checkOneDoRule(self, rule, currdate, offsetInfo):
        '''
            @param: offsetinfo for checking do rules, a tuple of (offsethi, offsetlo, offsetgap, actionType) 
            for the interval of the rule for current action. To check if the DO rule is satisfied, we need to shift the PSTL 
            to the timeframe corresponding to when the part for the rule respective to the current action is satisfied.

            @return: 2-tuple: (rule satisfied?, Number of seconds to wait to check on Rule)
        '''
        satisfied = True
        waitTimeIntvals = [] 
        for keyname, oper, _ineq, intval, stateList, tsunit in rule: 
            parseName = keyname.rsplit('_', 1)
            dname, dstate = parseName[0], parseName[1]
            if dname not in self.deviceStates:
                return False, -1 #we have not yet encountered this continous variable
            statedict = self.deviceStates[dname]
            if dstate not in statedict:
                return False, -1 #we don't know the device state, so we can't infer anything
            ruleSatisfied, satisfyingIntval = self._checkPTSLonDO(currdate, oper, intval, stateList, statedict[dstate], offsetInfo, tsunit)
            satisfied = satisfied and ruleSatisfied
            waitTimeIntvals.append(satisfyingIntval)

        #we have to check there is a satisfying waitTime to satisfy all rules
        if not satisfied:
            return False, -1
        else:
            satisfyingWaitime = self._findWaitTime(waitTimeIntvals, offsetInfo)
            if satisfyingWaitime >= 0:
                return satisfied, satisfyingWaitime
            else:
                return False, -1 #there is no wait time that satisfies all the rules, so the rule is not satisfied.

    def _checkDoRules(self, currChg, doRuleDict):
        '''
            @param doRuleDict d, where
            d[device_state][value] = ruledict, where
            ruledict[device'][newValue] = set of rules associates with changing device's state to value
            that can change our device' to newValue

            @return a dictionary describing anticipated changes in the environment for do rules after certain timedelay
            antChgs[timedelay][device] = (newStateValue, rulestring), which represents the device should be 
            changed to newStateValue after timedelay according to rulestring. If multiple state value change occurs for
            the same time delay, arbitrarily pick one and report the conflict.
        '''

        def checkDoRuleOnce(stateDict, currentDate, device):
            '''
                @param stateDict = ruledict[device]
                @param currentDate = currDate
                @param device = device_state name as in key of the dictionary

                returns list of (Rule satisfied?, State Value it should change to, # of seconds needed to perform this action
                if the action has not been done)
            '''
            offset = (0, 0, -1, 'G') #some arbitrary start value
            recordedChgs = []
            for newStateValues in stateDict.keys():
                for rules in stateDict[newStateValues]:
                    #we first iterate through the rules to find the offset interval.
                    temprule = copy.copy(rules)
                    tunit = 'seconds'
                    for i in range(len(temprule)): 
                        keyname, oper, _ineq, intval, _stateList, tsunit = temprule[i]
                        if keyname == device:
                            #(hi, lo)
                            offset = (intval[0], intval[1], intval[2], oper)
                            tunit = tsunit #each rule's time stamp unit must be the same. Since we can only learn minute rules or second rules,
                                           #not a combination of both.
                            temprule.pop(i) #we don't need to check validity of the current action itself, it will be valid as long as offset is satisfied
                            break
                    satisfactory, timeWait = self._checkOneDoRule(temprule, currentDate, offset)
                    if satisfactory:
                        recordedChgs.append((True, newStateValues, timeWait, temprule, tunit))
            return recordedChgs
        
        def checkValidValue(keyvalue, currentvalue):
            '''
                For continuous variables, there could be multiple ruledicts being satisfied by the change, we check whether
                currentvalue satisfies the keyvalue for the ruledict.

                keyvalue is in the format: value_ineq
            '''
            value, ineq = keyvalue.rsplit('_', 1)
            if ineq == '<':
                return int(currentvalue) < int(value)
            elif ineq == '>':
                return int(currentvalue) > int(value)
            elif ineq == '>=':
                return int(currentvalue) >= int(value)
            elif ineq == '<=':
                return int(currentvalue) <= int(value)
            else:
                print("unrecognized inequality: {0}".format(ineq))
                return False

        currdate, currdevice, currState, currValue = currChg 
        keyname = "{0}_{1}".format(currdevice, currState)
        anticipatedChgs = {}
        if keyname not in self.doRules:
            return anticipatedChgs #no rules about this device and this state, we can just continue
        
        value = -1
        dicts = [] #there could be multiple rule dicts about continuous variables chaning state, we need to check all satsifying
        try:
            value = int(currValue)
        except ValueError:
            dicts = [self.doRules[keyname][currValue]]
        else:
            for keyvalues in self.doRules[keyname].keys():
                if checkValidValue(keyvalues, value):
                    dicts.append(self.doRules[keyname][keyvalues])
        
        for ruledict in dicts:
            for device in ruledict.keys():
                for _tag, newStateValue, timedelay, theRule, tsunit in checkDoRuleOnce(ruledict[device], currdate, keyname):
                    immediate = timedelay == 0 #it is possible to have immediate rules due to user defined.
                    
                    if timedelay in anticipatedChgs.keys():
                        if device in anticipatedChgs[timedelay].keys(): #this device is also a device_state tuple.
                            #direct conflict occured
                            #TODO: maybe do something other than just raise a warning here?
                            val, rule, _imme = anticipatedChgs[timedelay][device]
                            print("WARNING: direct conflict between rules: {0} \n and rule: {1} \n, with the first rule changing \
                            device {2} to value {3}, second to value {4}".format(rule, theRule, device, val, newStateValue))
                        #if multiple rules are satisfied for the same device, we pick the last one
                        anticipatedChgs[timedelay][device] =  (newStateValue, theRule, immediate, tsunit) 
                    else:
                        anticipatedChgs[timedelay] = {}
                        anticipatedChgs[timedelay][device] =  (newStateValue, theRule, immediate, tsunit) 

        #returns a dictionary that maps after x time, the device should change to newStateValue according to DO rule.
        return anticipatedChgs

    def checkViolation(self, currChg, stateChgs = []):
        ''' 
            @param: the current chg we would like to analyze
            @param: an optional list of stateChgs in the enviroinment we use to check
            for rule violation
            eachstateChg is a 4-tuple: (date, device name, state, value)

            Note: for stateChgs, the states should be inserted in time order for each device

            If both an immediate rule and PSTL rule are violated, we prioritize immediate rule first.
        '''
        currdate, currdevice, currState, currValue = currChg
        for date, device, state, value in stateChgs:
            #date_t = sec_diff(date, currdate)
            self.updateState(date, device, state, value)

        boolresult, shouldstate = self._checkRules(currChg)

        if self.immediateRules:
            immediateBoolResult, immediateShouldState = self.checkImmediateViolationDONT(currChg)

        if not immediateBoolResult:  #immediate rule is violated
            if not boolresult: #two conflicting rules, priotize immediate rule
                shouldstate = immediateShouldState
            else:
                boolresult = immediateBoolResult
                shouldstate = immediateShouldState
        
        anticipatedChgs = {}

        if self.doRules is not None: 
            anticipatedChgs = self._checkDoRules(currChg, self.doRules)
            self._checkImmediateDoRules(anticipatedChgs, currChg) #add in the immediate rules in anticipated changes

        self.updateState(currdate, currdevice, currState, currValue) #add the change after rule checking
        return boolresult, shouldstate, anticipatedChgs
    
    def _checkImmediateDoRuleOnce(self, currChg, ruledict, lastDeviceState):
        '''
            @param ruledict: a dictionary d, d[deviceName_state][keyTriple] = ruledict
            where key Triple = (negate?, stateBefore, stateAfter) and
            ruledict[device_state][(keyBefore, keyAfter)] = List of rules need to be satisfied 
            for device_state to change from keyBefore to keyAfter.

            @param lastDeviceState: Last device state before the current change for the device currChg is associated with
        '''
        currdate, currdevice, currState, currValue = currChg
        recordChgs = []

        keyname = '{0}_{1}'.format(currdevice, currState)
        try:
            gap = self.gapdict[keyname]
        except KeyError:
            gap = 5

        for keytriple in ruledict.keys():
            negate, statebefore, stateAfter = keytriple
            goodStateChange = (self._checkStateEql(lastDeviceState, statebefore, gap) and self._checkStateEql(stateAfter, currValue, gap))
            print("statebefore: {0}, lastDeviceState: {1}".format(statebefore, lastDeviceState))
            print("stateAfter: {0}, currValue: {1}".format(stateAfter, currValue))

            if negate and goodStateChange:
                continue
            elif not negate and not goodStateChange:
                continue
            else:
                for deviceName in ruledict[keytriple].keys():
                    for keytuple in ruledict[keytriple][deviceName].keys():
                        sb, sa = keytuple #state before, state after for the device we are checking whether should change state
                        de, st = deviceName.rsplit('_', 1)
                        _time, lastState = self.deviceStates[de][st][-1]
                        if sb != lastState:
                            continue #precondition not satisfied

                        rules = ruledict[keytriple][deviceName][keytuple]
                        for rule in rules:
                            rulecopy = copy.copy(rule)
                            for i in range(len(rulecopy)):
                                if rulecopy[i][0] == keyname:
                                    rulecopy.pop(i) #remove the rule corresponding to current device.
                                    break

                            satisfiedrule, tsunit = self._checkOneImmediateRule(rulecopy, currdate)
                            if satisfiedrule:
                                recordChgs.append((deviceName, sa, rulecopy, 0, tsunit))
                                break
                                #1 sec be the time offset to execute the do rule since the rule is supposed to be immediate
        return recordChgs

    def _checkImmediateDoRules(self, anticipateddict, currChg):
        '''
            @param anticipatedDict: dictionary of anticipated changed as in checking for STL DO rules
        '''
        _currdate, currdevice, currState, _currValue = currChg
        _time, lastDeviceState = None, None
        try:
            _time, lastDeviceState = self.deviceStates[currdevice][currState][-1]
        except KeyError:
            return anticipateddict #no information about previous state, nothing to be done here

        keyname = "{0}_{1}".format(currdevice, currState)
        if keyname not in self.doimmediateRules:
            return anticipateddict #nothing to be done here

        ruledict = self.doimmediateRules[keyname]

        for device, newStateValue, theRule, timedelay, tsunit in self._checkImmediateDoRuleOnce(currChg, ruledict, lastDeviceState):
            if timedelay in anticipateddict.keys():
                if device in anticipateddict[timedelay].keys(): #this device is also a device_state tuple.
                    #direct conflict occured
                    #TODO: maybe do something other than just raise a warning here?
                    val, rule, _imme = anticipateddict[timedelay][device]
                    print("WARNING: direct conflict between rules: {0} \n and rule: {1} \n, with the first rule changing \
                    device {2} to value {3}, second to value {4}".format(rule, theRule, device, val, newStateValue))
                #if multiple rules are satisfied for the same device, we pick the last one
                anticipateddict[timedelay][device] =  (newStateValue, theRule, True, tsunit) 
            else:
                anticipateddict[timedelay] ={}
                anticipateddict[timedelay][device] =  (newStateValue, theRule, True, tsunit) 
            return anticipateddict

    def _checkStateEql(self, value1, value2, gap):
        try:
            v1 = str(int(value1)//gap * gap)
            v2 = str(int(value2)//gap * gap)
            return v1 == v2
        except ValueError:
            return value1 == value2

    def _checkImmediate(self, currdate, startState, endState, stateChanged, negate, currentStates, gap, tsunit):
        if not currentStates:
            return False 

        lastChangedEndTime, lastChangedEndState = currentStates[-1]

        satisfied = False 
        if self._checkStateEql(lastChangedEndState, endState, gap):
            dur = sec_diff(lastChangedEndTime, currdate, tsunit)
            if not stateChanged:
                satisfied = dur > 1 #it stays in the state
            elif len(currentStates) > 1:
                _thetime, statebeforelastChg = currentStates[-2]
                satisfied = dur <= 1 and self._checkStateEql(statebeforelastChg, startState, gap) #immediate change and matches the state change
            else:
                return False #not enough info in states, simply ignore negate and return false
        if negate:
            satisfied = not satisfied
        return satisfied

    def _checkOneImmediateRule(self, rules, currdate):
        #immediate rule format: a list of (deviceName_state, startState, endState, stateChanged?, negate?)
        satisfied = True 
        for device_state_tuple, sState, eState, sChanged, negate, tsunit in rules:
            try:
                gap = self.gapdict[device_state_tuple]
            except KeyError:
                gap = 5 #default 5

            dname, dstate = device_state_tuple.rsplit('_', 1)

            if dname not in self.deviceStates.keys():
                return False #we have not encountered this continuous variable yet, dont know whats going on.

            statedict = self.deviceStates[dname]
            if dstate not in statedict.keys():
                return False #we don't know device state
        
            satisfied = satisfied and self._checkImmediate(currdate, sState, eState, sChanged, negate, statedict[dstate], gap, tsunit)
            print("Satisfied: {0}".format(satisfied))
        return satisfied, tsunit

    def checkImmediateViolationDONT(self, currChg):
        '''
            Checks whether our DONT immediate rules learned from TreeNoSTL is satisfied
        '''
        currdate, currdevice, currState, currValue = currChg
        keyname = "{0}_{1}".format(currdevice, currState)
        lastDeviceState = None
        try:
            lastDeviceState = self.deviceStates[currdevice][currState][-1] #date, value tuple
        except KeyError:
            return True, currValue #no info about past states of devices
        
        if keyname not in self.immediateRules:
            return True, currValue #no rules

        ruledict = self.immediateRules[keyname]

        try:
            gap = self.gapdict[keyname]
        except KeyError:
            gap = 5

        #same starting state but different ending state
        keys = [key for key in ruledict.keys() if (self._checkStateEql(key[0], lastDeviceState[1], gap) and not self._checkStateEql(key[1], currValue, gap))]

        for key in keys: 
            for rules in ruledict[key]:
                satisfiedrule, _tsunit = self._checkOneImmediateRule(rules, currdate)
                if satisfiedrule:
                    return False, key[1] #should be in this endState instead
        
        return True, currValue
        
    def checkCommand(self, dname, dstate, dvalue, rulestr, immediate, tsunit):
        '''
            As a final check for the rule before it is sent to Samsung Smartthings hub to change device state,
            this fuction does:
                1. Check whether preconditions for the rulestr is still satisfied
                2. Check if the device still have changed to the desired value
            
            if it is an immediate rule, only step 2 will be checked.

            @param tsunit:  whether the rule is trained under seconds or minutes as base timestamp unit,
            default is seconds. We wait for one tsunit for device to change state for non immediate rules.
        '''
        currDate = datetime.datetime.now(datetime.timezone.utc) #Smartthings uses UTC as time reference
        currDateToStr = currDate.strftime("%Y-%m-%dT%H:%M:%S") #convert to string for sec-diff.

        if immediate:
            try:
                _date, currValue = self.deviceStates[dname][dstate][-1] #last change 
                return currValue != dvalue 
            except KeyError: #no state change has happened.
                return True
        else:
            if self._checkOneRule(rulestr, currDateToStr):
                if tsunit == 'minutes':
                    time.sleep(60)
                else:
                    time.sleep(1) 
                
                try:
                    _date, currValue = self.deviceStates[dname][dstate][-1] #last change 
                    return currValue != dvalue 
                except KeyError: #no state change has happened.
                    return True
            
        return False 