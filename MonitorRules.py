from ParseRules import convertDoRules

def sec_diff(date_ref, date):
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
    return day_diff * 86400 + hour_diff * 3600 + minute_diff * 60 + sec_diff

class MonitorRules():
    def __init__(self, rules, devices, max_states = 5, do=True):
        '''
            @param: max_states: maximum number of states for each device our monitor stores
            @param: whether we track for DO rules, that is, if a rule condition gets satisfied but no device change has
            happened, the monitor automatically commands the device to change after a fixed amount of time.
        '''
        self.devices = devices 
        self.deviceStates = self._initializeState(devices)
        self.rules = rules #dont rules received from ParseRules.py 
        self.doRules = convertDoRules(rules) if do else None
        self.max_states = max_states
    
    def _initializeState(self, devices):
        deviceState = {}
        for device in devices:
            deviceState[device] = {}
        return deviceState 
    
    def updateState(self, date, device, state, value):
        if state not in self.deviceStates[device]:
            self.deviceStates[device][state] = [(date, value)]
        else:
            st = self.deviceStates[device][state]
            if len(st) >= self.max_states:
                st.pop(0)
            st.append((date, value))

    def _checkPTSL(self, currdate, oper, interval, possibleStates, currentStates):
        hi, lo, gap = interval

        if oper == 'F':
            validStates = [(sec_diff(date, currdate), value) for (date, value) in currentStates if value in possibleStates]
            for date, value in validStates:
                if date <= hi and date >= lo:
                    return True  
            return False 

        elif oper == 'G':
            satisfied = True 
            first_idx = -1 #first occurence of the index greater or equal date range. i.e what the device is like before date range
            last_idx_outside_range = -1 #last idx happens before hi, used when no state change has happened within the data range
            for i in range(len(currentStates)):
                #Note current states is stored such that the first element is farthest away.
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate)
                if datediff >= lo and datediff <= hi:
                    if first_idx < 0:
                        first_idx = i 
                    satisfied = satisfied and value in possibleStates
                if datediff > hi:
                    last_idx_outside_range = i 

            first_idx = last_idx_outside_range if first_idx < 0 else first_idx

            if first_idx < 0:
                return False #we have no idea what happens within date range
            elif first_idx == 0:
                satisfied = currentStates[first_idx][1] in possibleStates
                satisfied = satisfied and sec_diff(currentStates[first_idx][0], currdate) >= hi 
            else:
                date, value = currentStates[first_idx-1]
                satisfied = satisfied and value in possibleStates #last state change before date range is valid 
            return satisfied

        elif oper == 'FG':
            for i in range(len(currentStates)):
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate)
                print("datediff: {0}".format(datediff))
                if datediff <= hi and datediff >= lo and value in possibleStates:
                    j = i+1
                    if j >= len(currentStates):
                        return True # no state change has happend since. 
                    while j < len(currentStates):
                        t_date, t_value = currentStates[j]
                        t_datediff = sec_diff(t_date, currdate)
                        if datediff - t_datediff > gap:
                            return True 
                        else:
                            if t_value not in possibleStates:
                                break 
                            j = j+1
            return False #no F has happend

        else: #GF case 
            if ((hi - lo) // gap > self.max_states):
                #simply not possible
                return False 
            possibleIntervals = [(x, x+gap) for x in range(lo, hi, 1)] #we need 1 satisfying state change for each of these intervals
            validStates = [(sec_diff(date, currdate), value) for (date, value) in currentStates if value in possibleStates]
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
        for keyname, oper, _ineq, intval, stateList in rule: 
            parseName = keyname.rsplit('_', 1)
            dname, dstate = parseName[0], parseName[1]
            statedict = self.deviceStates[dname]
            if dstate not in statedict:
                return False #we don't know the device state, so we can't infer anything
            satisfied = satisfied and self._checkPTSL(currdate, oper, intval, stateList, statedict[dstate])
        return satisfied

    def _checkRules(self, currChg):
        currdate, currdevice, currState, currValue = currChg
        keyname = "{0}_{1}".format(currdevice, currState)
        if keyname not in self.rules:
            return True, currValue #no rules about this device, we can just continue
        ruledict = self.rules[keyname]
        keys = [key for key in ruledict.keys() if key != currValue]
        #we only need to worry about the rules that does not match curr value being satisfied
        for key in keys:
            for rules in ruledict[key]:
                if self._checkOneRule(rules, currdate):
                    return False, key #the device should be in this state instead 
        return True, currValue

    def _checkPTSLonDO(self, currdate, oper, interval, possibleStates, currentStates, offsetInfo):
        '''
            @return a tuple: (Rule satisfied?, Possible starting intervals for rule to be satisfied)
        '''
        offsethi, offsetlo, offsetgap, offsetPSTL = offsetInfo
        offsetgap = max(0, offsetgap) #since for first level PSTL we set offsetgap to be -1
        offsethi, offsetlo = offsethi + offsetgap, offsetlo + offsetgap #add gap for FG rules.

        hi, lo, gap = interval 
        satisfied = False 
        #if its of rule G or GF, we have to wait at least offsethi seconds for our action rule
        #to be true, thus we can just call checkPSTL on modified interval.
        if offsetPSTL == 'G' or offsetPSTL == 'GF': 
            modifiedintval = (max(0, hi - offsethi), max(0, lo - offsethi), gap)
            satisfied = self._checkPTSL(currdate, oper, modifiedintval, possibleStates, currentStates)
            return satisfied, [(offsethi, offsethi)]
        else:
            if oper == 'G': 
                satisfied = True 
                first_idx = -1
                last_idx_outside_range = -1
                modifiedintvalhi, modifiedintvallo = (max(0, hi - offsetlo), max(0, lo - offsethi))
                intvStart = -1
                startDate = -1
                satisfyingIntvList = []
                for i in range(len(currentStates)):
                    date, value = currentStates[i]
                    datediff = sec_diff(date, currdate)
                    if datediff >= modifiedintvallo and datediff <= modifiedintvalhi:
                        if first_idx < 0:
                            first_idx = i 
                        if intvStart < 0 and value in possibleStates:
                            intvStart = max(offsetlo, lo - date)
                            startDate = datediff 
                        elif intvStart >= 0 and value not in possibleStates:
                            #we need to know that we are in the satisfying state for at least hi - lo + 1 seconds.
                            duration = (datediff - startDate) - (hi - lo + 1)
                            if duration > 0:
                                satisfied = True 
                                satisfyingIntvList.append((intvStart, intvStart + duration))
                            intvStart = -1
                            startDate = -1
                    if datediff > hi:
                        last_idx_outside_range = i 

                first_idx = last_idx_outside_range if first_idx < 0 else first_idx

                if first_idx < 0:
                    return False, [] 
                elif first_idx == 0:
                    if sec_diff(currentStates[first_idx][0], currdate) >= hi:
                        return True, [(offsetlo, offsethi)] #always will be satisfied
                    else:
                        return False, [] 
                else:
                    if intvStart >= 0: #everything after will be satisfied, append this
                        satisfied = True
                        satisfyingIntvList.append((intvStart, offsethi)) #check behavior before the first interval
                    date, value = currentStates[first_idx - 1]
                    if value in possibleStates: #then any time before our first interval also works, extend our interval.
                        if not satisfyingIntvList: #no interval yet, we can wait for as long as we can
                            return True, [(offsetlo, offsethi)]
                        else:
                            _firstIntvlo, firstIntvhi = satisfyingIntvList.pop(0)
                            if not satisfied:
                                satisfied = ((hi - lo + 1) <= (firstIntvhi - offsetlo + 1)) #check if this interval satisfies our condition.
                            satisfyingIntvList.insert(0, (offsetlo, firstIntvhi))
                    return satisfied, satisfyingIntvList
                
            elif oper == 'F':
                pStates = [(sec_diff(date, currdate), value) for (date, value) in currentStates]
                #Since the action rule for F or FG can be immediately satisfied after offsetlo seconds have passed.
                modifiedintvalhi, modifiedintvallo = (max(0, hi - offsetlo), max(0, lo - offsethi))
                intvStart = -1
                startDate = -1
                satisfyingIntvList = []
                for date, value in pStates:
                    if date <= modifiedintvalhi and date >= modifiedintvallo:
                        if intvStart < 0 and value in possibleStates:
                            #we can't wait less than offsetlo, and we have to wait at least lo - date seconds to satisfy rule
                            intvStart = max(offsetlo, lo - date)
                            startDate = date
                            satisfied = True 
                        elif intvStart >= 0 and value not in possibleStates:
                            #we can't wait more than (hi - lo + 1) seconds from intvStart, since then the intvStart event won't
                            #satisfy our rule anymore.
                            endpoint = min(intvStart + (hi - lo + 1), intvStart + (date - startDate), offsethi)
                            satisfyingIntvList.append((intvStart, endpoint))
                            intvStart = -1
                            startDate = -1

                if intvStart >= 0: #need to handle the last interval, we can't wait more than offsethi seconds.
                    satisfyingIntvList.append((intvStart, min(intvStart + (hi - lo + 1), offsethi)))
                return satisfied, satisfyingIntvList
            
            elif oper == 'FG':
                intvStart = -1
                startDate = -1
                satisfyingIntvList = []

                for i in range(len(currentStates)):
                    date, value = currentStates[i]
                    modifiedintvalhi, modifiedintvallo = (max(0, hi - offsetlo), max(0, lo - offsethi))
                    datediff = sec_diff(date, currdate)
                    if datediff <= modifiedintvalhi and datediff >= modifiedintvallo:
                        if intvStart < 0 and value in possibleStates:
                            j = i+1
                            if j >= len(currentStates):
                                satisfied = True 
                                intvStart = max(offsetlo, lo - datediff)
                                startDate = datediff
                            else:
                                while j < len(currentStates):
                                    t_date, t_value = currentStates[j]
                                    t_datediff = sec_diff(t_date, currdate)
                                    if intvStart < 0 and datediff - t_datediff > gap:
                                        satisfied = True 
                                        intvStart = max(offsetlo, lo - datediff)
                                        startDate = datediff
                        elif intvStart >= 0 and value not in possibleStates:
                            #we also need to account the time needed for the gap due to second level PSTL here.
                            endpoint = min(intvStart + (hi - lo + 1), intvStart + (datediff - startDate) - gap, offsethi)
                            satisfyingIntvList.append((intvStart, endpoint))
                            intvStart = -1
                            startDate = -1

                if intvStart > 0:
                    satisfyingIntvList.append((intvStart, min(intvStart + (hi - lo + 1), offsethi)))
                return satisfied, satisfyingIntvList
            
            else: #GF case
                intvStart = -1
                satisfyingIntvList = []

                for i in range(offsetlo, offsethi, 1):

                    modifiedhi, modifiedlo = (max(0, hi - i), max(0, lo - i))
                    validStates = []
                    for date, value in currentStates[: -1]:
                        datediff = sec_diff(date, currdate)
                        if datediff <= modifiedhi and datediff >= modifiedlo and value in possibleStates:
                            validStates.append((datediff, value))

                    lastStateAdded = False 
                    dateLast, dateValue = currentStates[-1]
                    dateLastDiff = sec_diff(dateLast, currdate)
                    if dateLastDiff <= modifiedhi and dateLastDiff >= modifiedlo:
                        if dateValue in possibleStates:
                            validStates.append((dateLastDiff, dateValue))    
                        lastStateAdded = True 
                
                    if ((hi - lo) // gap > len(validStates)): #have more non overlapping intervals than state changes
                        if lastStateAdded:
                            return satisfied, satisfyingIntvList 
                            #any interval happening after will not satisfy our rule since not enough changes for intervals
                        continue

                    possibleIntervals = [(x, x+gap) for x in range(modifiedlo, modifiedhi, 1)]
                    for lo_int, hi_int in possibleIntervals:
                        hasSatisfied = False
                        for date, value in validStates:
                            if date >= lo_int and date <= hi_int:
                                hasSatisfied = True 
                                break
                        #None of the valid states satisfies our rule
                        if not hasSatisfied:
                            if intvStart >= 0:
                                satisfyingIntvList.append((intvStart, i))
                                intvStart = -1
                            continue 
                    
                    #all intervals have been satisfied.
                    if intvStart < 0:
                        intvStart = i 
                        satisfied = True

                if intvStart > 0:
                    satisfyingIntvList.append((intvStart, min(intvStart + (hi - lo + 1), offsethi)))
                return satisfied, satisfyingIntvList
        
    def _findWaitTime(self, timeIntervals):
        '''
            Given a list of interval constraint list, check for a wait time that satisfy at least one
            interval constraint for each list.

            @param: The time interval constraint list list
            @return: A satisfactory wait time, -1 if none found
        '''
        if not timeIntervals:
            print("Warning: Time interval list is empty, this should not happen")
            return -1 

        #we note each interval with in a list would not overlap by our construction, our goal is simply to check
        #if there is len(timInterval) amount of interval overlap in the provided intervals.
        allIntVals = [item for sublist in timeIntervals for item in sublist] #flattens our list.
        startFinishList = []
        for intStart, intEnd in allIntVals:
            startFinishList.append((intStart, 'L'))
            startFinishList.append((intEnd, 'R'))
        sortedIntVals = sorted(startFinishList) 

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
            @optional param: offsetinfo for checking do rules, a tuple of (offsethi, offsetlo, offsetgap, actionType) 
            for the interval of the rule for current action. To check if the DO rule is satisfied, we need to shift the PSTL 
            to the timeframe corresponding to when the part for the rule respective to the current action is satisfied.

            @return: 2-tuple: (rule satisfied?, Number of seconds to wait to check on Rule)
        '''
        satisfied = True
        waitTimeIntvals = [] 
        for keyname, oper, _ineq, intval, stateList in rule: 
            parseName = keyname.rsplit('_', 1)
            dname, dstate = parseName[0], parseName[1]
            statedict = self.deviceStates[dname]
            if dstate not in statedict:
                return False #we don't know the device state, so we can't infer anything
            ruleSatisfied, satisfyingIntval = self._checkPTSLonDO(currdate, oper, intval, stateList, statedict[dstate], offsetInfo)
            satisfied = satisfied and ruleSatisfied
            waitTimeIntvals.append(satisfyingIntval)

        #if it is G or GF rule for our offsetInfo, we know we have to wait offsethi amount of time.
        if offsetInfo[3] == 'G' or offsetInfo[3] == 'GF': #3rd param is actiontype
            return satisfied, offsetInfo[0] #0th param is offsethi 
        else: #otherwise, we have to check there is a satisfying waitTime to satisfy all rules
            if not satisfied:
                return False, -1
            else:
                satisfyingWaitime = self._findWaitTime(waitTimeIntvals)
                if satisfyingWaitime >= 0:
                    return satisfied, satisfyingWaitime
                else:
                    return False, -1 #there is no wait time that satisfies all the rules, so the rule is not satisfied.

    def _checkDoRules(self, currChg, doRuleDict):
        
        def checkDoRuleOnce(stateDict, currentDate, device):
            '''
                @param stateDict = ruledict[device]
                @param currentDate = currDate
                @param device = device_state name as in key of the dictionary

                returns (Rule satisfied?, State Value it should change to, # of seconds needed to perform this action
                if the action has not been done)
            '''
            offset = (0, 0)
            for newStateValues in stateDict.keys():
                for rules in stateDict[newStateValues]:
                    #we first iterate through the rules to find the offset interval.
                    for i in range(len(rules)): 
                        keyname, oper, _ineq, intval, _stateList = rules[i]
                        if keyname == device:
                            #(hi, lo)
                            offset = (intval[0], intval[1], intval[2], oper)
                            rules.pop(i) #we don't need to check validity of the current action itself.
                            break
                    satisfactory, timeWait = self._checkOneDoRule(rules, currentDate, offset)
                    if satisfactory:
                        return True, newStateValues, timeWait
            return False, '', -1
                        
        currdate, currdevice, currState, currValue = currChg 
        keyname = "{0}_{1}".format(currdevice, currState)
        if keyname not in self.doRules:
            return True, currValue #no rules about this device and this state, we can just continue
        ruledict = self.doRules[keyname][currValue]
        
        anticipatedChgs = {}
        for device in ruledict.keys():
            tag, newStateValue, timedelay = checkDoRuleOnce(ruledict[device], currdate, keyname)
            if tag:
                anticipatedChgs[timedelay] = (device, newStateValue)
        #returns a dictionary that maps after x time, the device should change to newStateValue according to DO rule.
        return anticipatedChgs

    def checkViolation(self, currChg, stateChgs = []):
        ''' 
            @param: the current chg we would like to analyze
            @param: an optional list of stateChgs in the enviroinment we use to check
            for rule violation
            eachstateChg is a 4-tuple: (date, device name, state, value)

            Note: for stateChgs, the states should be inserted in time order for each device
        '''
        currdate, currdevice, currState, currValue = currChg
        for date, device, state, value in stateChgs:
            #date_t = sec_diff(date, currdate)
            self.updateState(date, device, state, value)
        
        self.updateState(currdate, currdevice, currState, currValue)

        boolresult, shouldstate = self._checkRules(currChg)
        if boolresult:
            #for debugging
            if shouldstate != currValue:
                print("This should not happen with shouldstate: {0}, currValue: {1}".format(shouldstate, currValue))
                raise NotImplementedError
        
        anticipatedChgs = {}
        if self.doRules: #TODO: Need Debugging.
            anticipatedChgs = self._checkDoRules(currChg, self.doRules)
        
        return boolresult, shouldstate, anticipatedChgs