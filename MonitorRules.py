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

    def _checkValid(self, possibleStates, ineq, value):
        '''
            check if the current value satisfies the rule. 
            
            if value discrete, simply check if it is in the possibleStates
            otherwise, convert it to int to compare value with oper
        '''
        intval, cmpval = -1, -1
        try:
            intval = int(value)
            cmpval = int(possibleStates[0])
        except ValueError: #discrete value
            return value in possibleStates
        if ineq == '<':
            return intval < cmpval
        elif ineq == '<=':
            return intval <= cmpval
        elif ineq == '>':
            return intval > cmpval
        else:
            return intval >= cmpval

    def _checkPTSL(self, currdate, oper, interval, possibleStates, currentStates, tsunit, ineq):
        hi, lo, gap = interval

        if oper == 'F':
            first_idx = -1
            for i in range(len(currentStates)):
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate, tsunit)
                if datediff >= lo and datediff < hi:
                    if first_idx < 0:
                        first_idx = i 
                    if self._checkValid(possibleStates, ineq, value):
                        return True 
                if first_idx < 0 and datediff < lo:
                    first_idx = i
            if first_idx < 0:
                first_idx = len(currentStates)
            lastoccur = first_idx - 1
            if lastoccur < 0:
                return False 
            else:
                _ld, lastvalue = currentStates[lastoccur]
                return self._checkValid(possibleStates, ineq, lastvalue) 

        elif oper == 'G':
            satisfied = True 
            first_idx = -1 #first occurence of the index greater or equal date range. i.e what the device is like before date range

            for i in range(len(currentStates)):
                #Note current states is stored such that the first element is farthest away.
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate, tsunit)
                if datediff >= lo and datediff < hi:
                    if first_idx < 0:
                        first_idx = i
                    satisfied = satisfied and self._checkValid(possibleStates, ineq, value)
                if first_idx < 0 and datediff < lo:
                    first_idx = i
            
            if first_idx < 0:
                first_idx = len(currentStates)
            lastoccur = first_idx - 1

            if lastoccur < 0:
                return False #we have no idea what happens within date range
            else:
                date, value = currentStates[lastoccur]
                satisfied = satisfied and self._checkValid(possibleStates, ineq, value) #last state change before date range is valid 
            return satisfied

        elif oper == 'FG':
            first_idx = -1
            first_invalid_date = -1

            for i in range(len(currentStates)):
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate, tsunit)
                if datediff < hi and datediff >= lo:
                    if first_idx < 0:
                        first_idx = i
                    if self._checkValid(possibleStates, ineq, value):
                        j = i+1
                        if j >= len(currentStates) and datediff - lo >= gap:
                            return True # no state change has happend since. 
                        while j < len(currentStates):
                            t_date, t_value = currentStates[j]
                            t_datediff = sec_diff(t_date, currdate, tsunit)
                            if datediff - t_datediff >= gap:
                                return True 
                            else:
                                if not self._checkValid(possibleStates, ineq, t_value):
                                    break 
                                j = j+1
                    elif first_invalid_date < 0: #first invalid state change
                        first_invalid_date = datediff

                if first_idx < 0 and datediff < lo:
                    first_idx = i

            if first_idx < 0:
                first_idx = len(currentStates)
            if first_idx - 1 >= 0:
                _ld, lastvalue = currentStates[first_idx - 1]
                longenough = first_invalid_date < 0 or hi - first_invalid_date >= gap #we are valid for at least gap seconds.
                return self._checkValid(possibleStates, ineq, lastvalue) and longenough 
                
            return False #no F has happend

        else: #GF case 
            last_satisfied_time = math.inf #last state change from a not satisfied state to satisfied state
            last_notsatisfied_time = math.inf #last change from a satisfied state to not satisfied state
            possibleIntervals = [(x - gap, x) for x in range(hi, lo + gap - 1, -1)] #we need 1 satisfying state change for each of these intervals
            #need to be in this order since we analyzing the most recent state changes last. lo + gap - 1 >= 0 since gap > 0
            #possibleIntervals = [(x, x + gap) for x in range(lo, hi - gap + 1, 1)] 
            currentintvalidx = 0
            currentStateidx = 0

            while currentintvalidx < len(possibleIntervals) and currentStateidx < len(currentStates):
                currintvallo, currintvalhi = possibleIntervals[currentintvalidx]
                date, value = currentStates[currentStateidx]
                datediff = sec_diff(date, currdate, tsunit)
                if datediff < currintvallo: #too recent for our current interval, we can check next state change
                    #last_satisfied_time cant be < currintvallo already since this is the first time we see a more recent state change.
                    if last_notsatisfied_time >= currintvalhi and last_notsatisfied_time <= last_satisfied_time:
                        #last change is in a not satisfied state for the entire interval, GF rule not satisfied for the interval
                        return False
                    else:
                        currentintvalidx = currentintvalidx + 1 #we check next interval 
                else:
                    #we continue to update our state changes for the interval, we need last_satisfied_time > last_notsatisfied_time to show
                    #we are currently in not satisfied state and want to change to a satisfied state.
                    if self._checkValid(possibleStates, ineq, value) and last_satisfied_time >= last_notsatisfied_time:
                        last_satisfied_time = datediff
                    elif not self._checkValid(possibleStates, ineq, value) and last_notsatisfied_time >= last_satisfied_time:
                        last_notsatisfied_time = datediff 
                    currentStateidx = currentStateidx + 1

            while currentintvalidx < len(possibleIntervals):
                #all the state changes did not cover all the intervals, we check rest of the interval if they are satisfied
                currintvallo, currintvalhi = possibleIntervals[currentintvalidx]
                if not(last_notsatisfied_time >= currintvallo and last_notsatisfied_time < currintvalhi):
                    #no nonsatisfying state change within the interval
                    return last_satisfied_time < last_notsatisfied_time #last change is a satisfactory change, valid.
                currentintvalidx += 1
            return True #we have checked all the intervals and found no violations

    def _checkOneRule(self, rule, currdate):
        satisfied = True 
        for keyname, oper, ineq, intval, stateList, tsunit in rule: 
            parseName = keyname.rsplit('_', 1)
            dname, dstate = parseName[0], parseName[1]
            if dname not in self.deviceStates:
                return False #continuous variable not encountered, we dont know states
            statedict = self.deviceStates[dname]
            if dstate not in statedict:
                return False #we don't know the device state, so we can't infer anything
            satisfied = satisfied and self._checkPTSL(currdate, oper, intval, stateList, statedict[dstate], tsunit, ineq)
        return satisfied

    def _checkRules(self, currChg):
        currdate, currdevice, currState, currValue = currChg
        keyname = "{0}_{1}".format(currdevice, currState)
        if keyname not in self.rules:
            return True, currValue, [] #no rules about this device, we can just continue, this should also skip all continuous variable devices
        ruledict = self.rules[keyname]
        keys = [key for key in ruledict.keys() if key != currValue]
        #we only need to worry about the rules that does not match curr value being satisfied
        resvalue = currValue
        satisfied = True
        checkedrule = []
        for key in keys:
            for rules in ruledict[key]:
                if self._checkOneRule(rules, currdate):
                    satisfied = False
                    resvalue = key #the device should be in this state instead 
                    checkedrule = rules
        return satisfied, resvalue, checkedrule

    def _checkPTSLonDO(self, currdate, oper, interval, possibleStates, currentStates, offsetInfo, tsunit, ineq):
        '''
            @return a tuple: (Rule satisfied?, Possible starting intervals for rule to be satisfied)
        '''
        offsethi, offsetlo, offsetgap, offsetPSTL = offsetInfo
        offsetgap = max(0, offsetgap) #since for first level PSTL we set offsetgap to be -1
        offsethi, offsetlo = offsethi - offsetgap, offsetlo + offsetgap #add gap for FG rules, for F rules, we can also wait for as long as possible assuming no state changes

        hi, lo, gap = interval 
        satisfied = False 
        #if its of rule G or GF, we have to wait at least offsethi seconds for our action rule
        #to be true, but we can wait for as long as we want assuming no state change happens.
        if offsetPSTL == 'G' or offsetPSTL == 'GF': 
            offsetlo = offsethi
            offsethi = math.inf
        else:
            offsethi = math.inf 
            
        if oper == 'G': 
            satisfied = True 
            first_idx = -1
            modifiedintvalhi, modifiedintvallo = (max(0, hi - offsetlo), max(0, lo - offsethi))

            intvStart = -1
            startDate = -1
            satisfyingIntvList = []
            for i in range(len(currentStates)):
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate, tsunit)
                if datediff >= modifiedintvallo and datediff < modifiedintvalhi:
                    if first_idx < 0:
                        first_idx = i 
                    if intvStart < 0 and self._checkValid(possibleStates, ineq, value):
                        #have to wait hi amount of seconds for G.
                        intvStart = max(offsetlo, hi - datediff)
                        startDate = datediff 
                    elif intvStart >= 0 and not self._checkValid(possibleStates, ineq, value):
                        satisfyingIntvList.append((intvStart, intvStart + (startDate - datediff) - 1))
                        intvStart = -1
                        startDate = -1
                if first_idx < 0 and datediff < modifiedintvallo:
                    first_idx = i 

            if first_idx < 0:
                first_idx = len(currentStates)

            lastoccur = first_idx - 1

            if intvStart >= 0:
                satisfyingIntvList.append((intvStart, offsethi)) #check behavior before the first interval

            firstStart, firstEnd = -1, -1
            if satisfyingIntvList:
                firstStart, firstEnd = satisfyingIntvList[0]

            if lastoccur < 0:
                return False, [] 
            elif first_idx == len(currentStates): #no state change within interval
                date, value = currentStates[lastoccur]
                if self._checkValid(possibleStates, ineq, value): 
                    satisfyingIntvList.append((offsetlo, offsethi))
            else:
                date, value = currentStates[lastoccur]
                nextdate, _nextvalue = currentStates[first_idx]

                if self._checkValid(possibleStates, ineq, value):                
                    if nextdate == firstStart: #then any time before our first interval also works, extend our interval.
                        satisfyingIntvList.pop(0)
                        satisfyingIntvList.insert(0, (offsetlo, firstEnd))
                    else:
                        satisfyingIntvList.insert(0, (offsetlo, hi - sec_diff(nextdate, currdate, tsunit) - 1))

            reslist = []
            #for each found interval, we need to know that they have to be at least the size of [lo, hi].
            for start, end in satisfyingIntvList:
                duration = (end - start) - (hi - lo)
                if duration >= 0:
                    reslist.append((start, start + duration))
            print("Returned from G rule with satisfied: {0}, result list: {1}".format(len(reslist) > 0, reslist))
            return len(reslist) > 0, reslist
            
        elif oper == 'F':
            #Since the action rule for F or FG can be immediately satisfied after offsetlo seconds have passed.
            modifiedintvalhi, modifiedintvallo = (max(0, hi - offsetlo), max(0, lo - offsethi))
            intvStart = -1
            startDate = -1
            first_idx = -1
            satisfyingIntvList = []
            for i in range(len(currentStates)):
                realdate, realvalue = currentStates[i]
                date, value = sec_diff(realdate, currdate, tsunit), realvalue
                if date < modifiedintvalhi and date >= modifiedintvallo:
                    if first_idx < 0:
                        first_idx = i
                    if intvStart < 0 and self._checkValid(possibleStates, ineq, value):
                        #we have to wait at least lo - date seconds to satisfy rule
                        intvStart = lo - date
                        startDate = date
                        satisfied = True 
                    elif intvStart >= 0 and not self._checkValid(possibleStates, ineq, value):
                        #we need to stop once the non-satisfying state would last the entire interval.
                        #intvStart + (startDate- date) makes the currchange to be at lo, add (hi -lo) to make it at hi, -1 to make inclusive
                        endpoint = min(intvStart + (startDate - date) + (hi - lo), offsethi)
                        satisfyingIntvList.append((intvStart, endpoint))
                        intvStart = -1
                        startDate = -1
                        #overlaps may happen here, since the not satisfying state may not last the entire interval, we could
                        #change back to a satisfying state quickly, and this invalid state may not matter at all.

                elif first_idx < 0 and date < modifiedintvallo:
                    if i == 0: #we have no idea what is going on before
                        return False, []
                    else: #we need the last state change to be in a valid state.
                        _lastdate, lastvalue = currentStates[i-1]
                        if self._checkValid(possibleStates, ineq, lastvalue):
                            print("Returned from F rule with satisfied: {0}, result list: {1}".format(True, [(offsetlo, offsethi)]))
                            return True, [(offsetlo, offsethi)]
                        else: 
                            return False, []
            if first_idx < 0:
                first_idx = len(currentStates)

            if first_idx <= 0:
                return False, []
            elif first_idx == len(currentStates):
                _ld, lv = currentStates[first_idx - 1]
                if self._checkValid(possibleStates, ineq, lv):
                    satisfyingIntvList.append((offsetlo, offsethi))
            else:
                firstdate, _firstvalue = currentStates[first_idx] #dont care about value being valid or not, since we will merge overlap
                _ld, lv = currentStates[first_idx - 1]
                if self._checkValid(possibleStates, ineq, lv):
                    firstStart = hi - sec_diff(firstdate, currdate, tsunit)
                    satisfyingIntvList.append((offsetlo, firstStart))

            if intvStart >= 0:
                satisfyingIntvList.append((intvStart, offsethi))

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
            print("Returned from F rule with satisfied: {0}, result list: {1}".format(satisfied, reslist[1:]))
            return satisfied, reslist[1:]
        
        elif oper == 'FG':
            satisfyingIntvList = []
            modifiedintvalhi, modifiedintvallo = (max(0, hi - offsetlo), max(0, lo - offsethi))
            print('modifiedhi: {0}, modifiedlo: {1}'.format(modifiedintvalhi, modifiedintvallo))

            first_idx = -1
            first_invalid_date = -1
            intvStart = -1
            startDate = -1

            for i in range(len(currentStates)):
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate, tsunit)
                if datediff < modifiedintvalhi and datediff >= modifiedintvallo:
                    if first_idx < 0:
                        first_idx = i 
                    if intvStart < 0 and self._checkValid(possibleStates, ineq, value):
                        j = i+1
                        if j >= len(currentStates): #our device is currently in a valid state
                            satisfied = True 
                            intvStart = lo - datediff + gap #anytime after this would work.
                            startDate = datediff
                        else:
                            while j < len(currentStates):
                                t_date, t_value = currentStates[j]
                                t_datediff = sec_diff(t_date, currdate, tsunit)
                                if intvStart < 0 and datediff - t_datediff >= gap:
                                    satisfied = True 
                                    intvStart = lo - datediff + gap
                                    startDate = datediff
                                    break
                                elif not self._checkValid(possibleStates, ineq, t_value):
                                    break #valid state not lasting long enough, break.
                                j = j+1
                    elif not self._checkValid(possibleStates, ineq, value):
                        #similar to how it is done in F, with addition of gap
                        if intvStart >= 0: 
                            endpoint = min(intvStart + (startDate - datediff) + (hi - lo), offsethi)
                            if endpoint >= intvStart:
                                satisfyingIntvList.append((intvStart, endpoint))
                            intvStart = -1
                        if first_invalid_date < 0:
                            first_invalid_date = datediff

                elif first_idx < 0 and datediff < modifiedintvallo:
                    if i == 0: #we have no idea what is going on before
                        return False, []
                    else: #we just need the last state change to be in a valid state.
                        _lastdate, lastvalue = currentStates[i-1]
                        if self._checkValid(possibleStates, ineq, lastvalue):
                            print("Returned from FG rule with satisfied: {0}, result list: {1}".format(True, [(offsetlo, offsethi)]))
                            return True, [(offsetlo, offsethi)]
                        else:
                            return False, []
            if first_idx < 0:
                first_idx = len(currentStates)
            if first_idx <= 0:
                return False, []
            else:
                _ld, lv = currentStates[first_idx - 1]
                longenough = first_invalid_date < 0 or hi - first_invalid_date - offsetlo >= gap #we are valid for at least gap seconds after waiting offsetlo
                if self._checkValid(possibleStates, ineq, lv) and longenough:
                    if first_invalid_date < 0:
                        satisfyingIntvList.append((offsetlo, offsethi))
                    else:
                        firstStart = lo - first_invalid_date + gap
                        firstendpt = firstStart + hi - lo  #there will be at least a valid state lasting gap time stamps since start if we wait this long
                        satisfyingIntvList.append((offsetlo,firstendpt)) 

            if intvStart >= 0:
                satisfyingIntvList.append((intvStart, offsethi))

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
            print("Returned from FG rule with satisfied: {0}, result list: {1}".format(satisfied, reslist[1:]))
            return satisfied, reslist[1:]
        
        else: #GF case
            intvStart = -1
            satisfyingIntvList = []

            validtimes = [] #a list of time intervals with no wait time such that our device is in valid state
            validStart = -1
            for i in range(len(currentStates)):
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate, tsunit)
                if validStart < 0 and self._checkValid(possibleStates, ineq, value):
                    validStart = datediff + gap #it will be of the valid state within the gap window.
                elif validStart >= 0 and not self._checkValid(possibleStates, ineq, value):
                    endpoint = datediff
                    validtimes.append((validStart, max(0, endpoint - gap)))
                    validStart = -1
            
            if validStart >= 0:
                validtimes.append((validStart, 0))
            
            #there will be overlaps, we remove accordingly, we note the interval is in (hi, lo) order, differing from other cases
            vlist = []
            currstartpt, currendpt = math.inf, math.inf
            for startpt, endpt in validtimes:
                if startpt > currendpt: 
                    if endpt < currendpt:
                        currendpt = endpt 
                else:
                    vlist.append((currstartpt, currendpt))
                    currstartpt = startpt
                    currendpt = endpt 
            vlist.append((currstartpt, currendpt))
            vlist.pop(0) #pop the first dummy interval.

            if len(vlist) == 0: #no valid intervals
                return False, []

            waitTime = offsetlo #we have to wait at least offsetlo timestamps
            res_int_start = -1
            while waitTime <= hi:
                 #there is no point to wait more than hi timestamps as we have no idea what is going on in the future.
                modifiedhi, modifiedlo = (hi - waitTime, lo - waitTime)
                possibleIntervals = [(x - gap, x) for x in range(modifiedhi, modifiedlo + gap - 1, -1)]
                intervalidx = 0
                valididx = 0
                satisfied = True
                while intervalidx < len(possibleIntervals) and valididx < len(vlist) - 1: #we leave the last valid interval for special case
                    intlo, inthi = possibleIntervals[intervalidx]
                    validhi, validlo = vlist[valididx]

                    if inthi < validlo: #the interval appears after current valid interval
                        valididx = valididx + 1
                    elif validhi < intlo: #valid interval appears after current interval, this means the interval is not satisfied
                        if res_int_start >= 0:
                            satisfyingIntvList.append((res_int_start, waitTime-1))
                            res_int_start = -1
                        satisfied = False
                        break
                    else: #there is an intersection, check next interval
                        intervalidx += 1

                if satisfied:
                    if intervalidx < len(possibleIntervals):
                        #still have interval not checked, then we check last valid interval
                        intlo, inthi = possibleIntervals[intervalidx]
                        lastvalidhi, lastvalidlo = vlist[-1]

                        if not(lastvalidhi < intlo or inthi < lastvalidlo):
                            if intervalidx == 0 and lastvalidlo == 0: #we are still at first intval but at the last valid state interval
                                #if this is valid, we can wait for as long as we want since no more state changes
                                res_int_start = res_int_start if res_int_start >= 0 else waitTime
                                satisfyingIntvList.append((res_int_start, offsethi))
                                break
                            elif res_int_start < 0:
                                res_int_start = waitTime
                        else:
                            if res_int_start >= 0:
                                satisfyingIntvList.append((res_int_start, waitTime-1))
                                res_int_start = -1
                            if inthi < lastvalidlo:
                                #any waittime after would not be satisfied either since last valid interval already appeared before this
                                break
                    else: #a satisfactory assignment
                        if res_int_start < 0:
                            res_int_start = waitTime
                waitTime += 1 #increment our waitTime
            
            #print("Returned from GF rule with satisfied: {0}, result list: {1}".format(len(satisfyingIntvList) > 0, satisfyingIntvList))
            return len(satisfyingIntvList) > 0, satisfyingIntvList            

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
                
        if offsetInfo[3] == 'G' or offsetInfo[3] == 'GF':
            offsetlo = offsetInfo[0]
        else:
            offsetlo = offsetInfo[1] + max(0, offsetInfo[2])

        timeIntervals.append([(offsetlo, math.inf)]) #add in the interval needed for current change, we need to wait at least offsetlo seconds

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
        print("checking rule: {0}".format(rule))
        for keyname, oper, ineq, intval, stateList, tsunit in rule: 
            parseName = keyname.rsplit('_', 1)
            dname, dstate = parseName[0], parseName[1]
            if dname not in self.deviceStates:
                return False, -1 #we have not yet encountered this continous variable
            statedict = self.deviceStates[dname]
            if dstate not in statedict:
                return False, -1 #we don't know the device state, so we can't infer anything
            ruleSatisfied, satisfyingIntval = self._checkPTSLonDO(currdate, oper, intval, stateList, statedict[dstate], offsetInfo, tsunit, ineq)
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
        def computeoffset(intval, oper):
            '''
                given a primitive with [hi, lo, dur] and its oper, we compute the minimum number of timestamps we need to wait
            '''
            offsethi, offsetlo, offsetdur = intval 
            if oper == 'G' or oper == 'GF':
                return offsethi + max(0, offsetdur)
            else:
                return offsetlo + max(0, offsetdur)

        def checkDoRuleOnce(stateDict, currentDate, device, chgedvalue, continuous):
            '''
                @param stateDict = ruledict[device]
                @param currentDate = currDate
                @param device = device_state name as in key of the dictionary
                @param chgedvalue = the changed value for device's state, used to find the primitive with offset.
                @param continuous = whether our device change is corresponding to a continuous variable

                returns list of (Rule satisfied?, State Value it should change to, # of seconds needed to perform this action
                if the action has not been done)
            '''
            recordedChgs = []

            for newStateValues in stateDict.keys():
                for rules in stateDict[newStateValues]:
                    #we first iterate through the rules to find the offset interval.
                    valid_idx = [] #there could be multiple primitives associated with the same device and state, we just need to check
                                   #the rule that we need to wait the longest, since earlier rules will always be satisfied at that point.
                    tunit = 'seconds'
                    maxoffsetNum = -1 #some arbitrary start value
                    offset = (-1, -1, -1 ,'')
                    for i in range(len(rules)): 
                        keyname, oper, ineq, intval, stateList, tsunit = rules[i]
                        if keyname == device and not continuous and chgedvalue in stateList: #matching primitive
                            offsetval = computeoffset(intval, oper)
                            if offsetval > maxoffsetNum:
                                maxoffsetNum = offsetval
                                offset = (intval[0], intval[1], intval[2], oper)
                            valid_idx.append(i)
                        elif keyname == device and continuous and chgedvalue == (stateList[0] + '_' + ineq): 
                            offsetval = computeoffset(intval, oper)
                            if offsetval > maxoffsetNum:
                                maxoffsetNum = offsetval
                                offset = (intval[0], intval[1], intval[2], oper)
                            valid_idx.append(i)
                        tunit = tsunit #we assume each primitive would have the same timestamp unit to be same.
                    
                    #we don't need to check validity of the current action itself, it will be valid as long as offset is satisfied
                    temprule = [rules[i] for i in range(len(rules)) if i not in valid_idx]
                    satisfactory, timeWait = self._checkOneDoRule(temprule, currentDate, offset)
                    if satisfactory:
                        recordedChgs.append((True, newStateValues, timeWait, rules, tunit))

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
        dicts = [] #there could be multiple rule dicts about continuous variables changing state, we need to check all satsifying
        try:
            value = int(currValue)
        except ValueError:
            try:
                dicts = [(self.doRules[keyname][currValue], currValue, False)]
            except KeyError:
                return anticipatedChgs #no rules about this device_state's value, we continue.

        else:
            for keyvalues in self.doRules[keyname].keys():
                if checkValidValue(keyvalues, value):
                    dicts.append((self.doRules[keyname][keyvalues], keyvalues, True))
        
        for ruledict, chgedvalue, continuous in dicts:
            for device in ruledict.keys():
                for _tag, newStateValue, timedelay, theRule, tsunit in checkDoRuleOnce(ruledict[device], currdate, keyname, chgedvalue, continuous):
                    immediate = timedelay == 0 #it is possible to have immediate rules due to user defined.
                    
                    if timedelay in anticipatedChgs.keys():
                        if device in anticipatedChgs[timedelay].keys(): #this device is also a device_state tuple.
                            #direct conflict occured
                            #TODO: maybe do something other than just raise a warning here?
                            val, rule, _imme, _tsunit = anticipatedChgs[timedelay][device]
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

            @return: (is Dont rule violated?, Should be state, the rule being violated, anticipated Changes for Do rules)
        '''
        currdate, currdevice, currState, currValue = currChg
        for date, device, state, value in stateChgs:
            #date_t = sec_diff(date, currdate)
            self.updateState(date, device, state, value)

        boolresult, shouldstate, respectiveRule = self._checkRules(currChg)

        if self.immediateRules:
            immediateBoolResult, immediateShouldState, immediateRespectiveRule = self.checkImmediateViolationDONT(currChg)

        if not immediateBoolResult:  #immediate rule is violated
            if not boolresult: #two conflicting rules, priotize immediate rule
                shouldstate = immediateShouldState
                respectiveRule = immediateRespectiveRule
            else:
                boolresult = immediateBoolResult
                shouldstate = immediateShouldState
                respectiveRule = immediateRespectiveRule

        anticipatedChgs = {}

        if boolresult: #we should only mark the change as valid and consider DO rules if the change does not violate DONT rule already.
            self.updateState(currdate, currdevice, currState, currValue) 
            if self.doRules is not None: 
                anticipatedChgs = self._checkDoRules(currChg, self.doRules)
                self._checkImmediateDoRules(anticipatedChgs, currChg) #add in the immediate rules in anticipated changes

        return boolresult, shouldstate, respectiveRule, anticipatedChgs
    
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
                            satisfiedrule, tsunit = self._checkOneImmediateRule(rule, currdate)
                            if satisfiedrule:
                                recordChgs.append((deviceName, sa, rule, 0, tsunit))
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
                #if multiple rules are satisfied for the same device, we prioritize immediate rule and pick the last one
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
                satisfied = dur >= 1 #it stays in the state
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
                return False, '' #we have not encountered this continuous variable yet, dont know whats going on.

            statedict = self.deviceStates[dname]
            if dstate not in statedict.keys():
                return False, '' #we don't know device state
        
            satisfied = satisfied and self._checkImmediate(currdate, sState, eState, sChanged, negate, statedict[dstate], gap, tsunit)
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
            return True, currValue, [] #no info about past states of devices
        
        if keyname not in self.immediateRules:
            return True, currValue, [] #no rules

        ruledict = self.immediateRules[keyname]

        try:
            gap = self.gapdict[keyname]
        except KeyError:
            gap = 5

        #same starting state but different ending state
        keys = [key for key in ruledict.keys() if (self._checkStateEql(key[0], lastDeviceState[1], gap) and not self._checkStateEql(key[1], currValue, gap))]

        resvalue = currValue
        satisfied = True 
        respectiveRule = []

        for key in keys: 
            for rules in ruledict[key]:
                satisfiedrule, _tsunit = self._checkOneImmediateRule(rules, currdate)
                if satisfiedrule:
                    satisfied = False 
                    resvalue = key[1] #should be in this endState instead
                    respectiveRule = rules
        
        return satisfied, resvalue, respectiveRule
        
    def checkCommand(self, dname, dstate, dvalue, rulestr, immediate, tsunit, nextsecond):
        '''
            As a final check for the rule before it is sent to Samsung Smartthings hub to change device state,
            this fuction does:
                1. Check whether preconditions for the rulestr is still satisfied
                2. Check if the device still have changed to the desired value
            
            if it is an immediate rule, only step 2 will be checked.

            @param tsunit:  whether the rule is trained under seconds or minutes as base timestamp unit,
            default is seconds.
            @param nextsecond: to avoid race condition, we sometimes need to check nextsecond events, this = 1 if we
            check next second, 0 otherwise
        '''
        currDate = datetime.datetime.now(datetime.timezone.utc)
        if immediate:
            try:
                date, currValue = self.deviceStates[dname][dstate][-1] #last change 
                currDateToStr = currDate.strftime("%Y-%m-%dT%H:%M:%S")
                if currValue != dvalue:
                    if sec_diff(date, currDate, tsunit) <= 1: #direct conflict
                        print("WARNING: conflict occurs for rule: {0}".format(rulestr))
                        return False #some conflict behavior is already executed
                    else:
                        return True 
            except KeyError: #no state change has happened.
                return True
        else:
            if tsunit == 'minutes':
                offset = datetime.timedelta(seconds = 60)
            else:
                offset = datetime.timedelta(seconds = 1 + nextsecond)
            currDate = currDate - offset 
            #Smartthings uses UTC as time reference, we subtract an offset that we used to wait for device change to happen
            # if no violation occur
            currDateToStr = currDate.strftime("%Y-%m-%dT%H:%M:%S") #convert to string for sec-diff.

            if self._checkOneRule(rulestr, currDateToStr):
                try:
                    date, currValue = self.deviceStates[dname][dstate][-1] #last change 
                    if currValue != dvalue:
                        if sec_diff(date, currDateToStr, tsunit) <= 1: #direct conflict
                            print("WARNING: conflict occurs for rule: {0}".format(rulestr))
                            return False #some conflict behavior is already executed
                        else:
                            return True 
                except KeyError: #no state change has happened.
                    return True
            
        return False 