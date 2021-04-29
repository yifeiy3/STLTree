
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
    def __init__(self, rules, devices, max_states = 5):
        '''
            @param: max_states: maximum number of states for each device our monitor stores
        '''
        self.devices = devices 
        self.deviceStates = self._initializeState(devices)
        self.rules = rules #dont rules received from ParseRules.py 
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
            for i in range(len(currentStates)):
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate)
                if datediff >= lo and datediff <= hi:
                    if first_idx < 0:
                        first_idx = i 
                    satisfied = satisfied and value in possibleStates
                if first_idx < 0 and i > 0:
                    if datediff > hi:
                        first_idx = i+1
                    else:
                        first_idx = i 
            if first_idx < 0:
                return False #we have no idea what happens within date range
            elif first_idx == 0:
                satisfied = satisfied and currentStates[first_idx][0] == hi 
            else:
                date, value = currentStates[first_idx-1]
                satisfied = satisfied and value in possibleStates #last state change before date range is valid 
            return satisfied

        elif oper == 'FG':
            for i in range(len(currentStates)):
                date, value = currentStates[i]
                datediff = sec_diff(date, currdate)
                print("datediff: {0}".format(datediff))
                if datediff <= hi and datediff >= lo:
                    j = i+1 
                    while j < len(currentStates):
                        t_date, t_value = currentStates[j]
                        t_datediff = sec_diff(t_date, currdate)
                        if datediff - t_datediff > gap:
                            return True 
                        else:
                            if t_value not in possibleStates:
                                return False
                            j = j+1
                    if datediff >= gap: #no state change has happened since
                        return True 
            return False #no F has happend

        else: #GF case 
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
            if device == 'Virtual Switch 2':
                print("date: {0}, currdate: {1}, value:{2}".format(date, currdate, value))
            #date_t = sec_diff(date, currdate)
            self.updateState(date, device, state, value)
        
        self.updateState(currdate, currdevice, currState, currValue)

        boolresult, shouldstate = self._checkRules(currChg)
        if boolresult:
            #for debugging
            if shouldstate != currValue:
                print("This should not happen with shouldstate: {0}, currValue: {1}".format(shouldstate, currValue))
                raise NotImplementedError
        return boolresult, shouldstate