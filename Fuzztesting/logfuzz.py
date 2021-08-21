import random 
import datetime

'''
    randomly generate logs based on a set of immediate and PSTL rules
'''
def find_timediff(currTime, amount, tsunit):
    if tsunit == 'seconds':
        res = currTime - datetime.timedelta(seconds = amount)
    else:
        res = currTime - datetime.timedelta(minutes = amount)
    return res

class logGeneration():
    def __init__(self, devicedict, STLDontdict, immeDontdict, STLDodict, immeDoDict, gapdict, timebound):
        '''
            @param devices: the dictionary mapping device state tuple to their possible state values we used in rulefuzz.
            @param gapdict: dictionary mapping continuous variable to the gap it used to handle classfication
            for immediate rules
            @param timebound: the maximum timebound for STL rules we used to generate the dictionary,
            upper bounds the value for hi in STL rules, assume it is > 2.
        '''
        self.devices =  [de for de in devicedict.keys()]
        self.devicedict = devicedict
        self.STLDont = STLDontdict
        self.immeDont = immeDontdict
        self.STLDo = STLDodict if STLDodict else {}
        self.immeDo = immeDoDict if immeDoDict else {}
        self.gapdict = gapdict
        self.timebound = timebound 

    def generateDontLog(self, amountPerRule):
        '''
            @param: # of logs generated per rule

            generate random logs for DONT rules.
            for each rule, we generate a log that 'highly likely' satisfies the rule conditions,
            and our current change will have a random chance to violate the rule if rule conditions are satisfied
        '''
        GeneratedLogs = []
        for devices in self.STLDont.keys():
            for values in self.STLDont[devices].keys():
                for ruleStr in self.STLDont[devices][values]:
                    for i in range((amountPerRule)):
                        violation_seed = random.random()
                        GeneratedLogs.append(self._generateDontForOneSTLRule(devices, values, ruleStr, (violation_seed<=0.6)))

        for devices in self.immeDont.keys():
            for valuebefore, valueafter in self.immeDont[devices].keys():
                for ruleStr in self.immeDont[devices][(valuebefore, valueafter)]:
                    for i in range((amountPerRule)):
                        violation_seed = random.random()
                        GeneratedLogs.append(self._generateForOneImmediateRule(devices, valuebefore, valueafter, ruleStr, (violation_seed<=0.6)))

        return GeneratedLogs
    
    def generateDoLog(self, amountPerRule):
        GeneratedLogs = []

        for devices in self.STLDo.keys():
            for values in self.STLDo[devices].keys():
                for chg_devices in self.STLDo[devices][values].keys():
                    for chg_values in self.STLDo[devices][values][chg_devices].keys():
                        for ruleStr in self.STLDo[devices][values][chg_devices][chg_values]:
                            for i in range((amountPerRule)):
                                Events, currChg, waitTime, rs = self._generateDOForOneSTLRule(devices, values, ruleStr)
                                GeneratedLogs.append((Events, currChg, (chg_devices, chg_values, waitTime), rs))
        
        for devices in self.immeDo.keys():
            for keytriples in self.immeDo[devices].keys():
                #negate branch gives us whether we want our current change to violate the rule.
                negateBranch, beforeState, afterState = keytriples
                for chg_devices in self.immeDo[devices][keytriples].keys():
                    for chg_before, chg_after in self.immeDo[devices][keytriples][chg_devices].keys():
                        for ruleStr in self.immeDo[devices][keytriples][chg_devices][(chg_before, chg_after)]:
                            for i in range(amountPerRule):
                                #handle continuous variable by assigning them a valid value, since Dont rules do not handle continuous variables
                                Events, currChg, waitTime = [], '', ''
                                try:
                                    int(beforeState)
                                except ValueError:
                                    Events, currChg, waitTime, rs = self._generateForOneImmediateRule(devices, beforeState, afterState, ruleStr, negateBranch)
                                else:
                                    gap = self.gapdict[devices]
                                    beforeSt = str(random.randint(int(beforeState), int(beforeState) + gap - 1))
                                    afterSt = str(random.randint(int(afterState), int(afterState) + gap - 1))
                                    Events, currChg, waitTime, rs = self._generateForOneImmediateRule(devices, beforeSt, afterSt, ruleStr, negateBranch)
                                GeneratedLogs.append((Events, currChg, (chg_devices, chg_after, 0), rs)) #for immediate time.

        return GeneratedLogs

    def _generateDOForOneSTLRule(self, device, value, ruleStr):
        '''
            @param: offset information for the device, value state we picked

            @return: A 4-tuple of, (list of events happening before, curr change, DO rule change that should be satisfied
            if no influence from random events, ruleStr used to generate)
        '''
        def computeoffset(intval, oper):
            '''
                given a primitive with [hi, lo, dur] and its oper, we compute the minimum number of timestamps we need to wait
            '''
            offsethi, offsetlo, offsetdur = intval 
            if oper == 'G' or oper == 'GF':
                return offsethi - max(0, offsetdur)
            else:
                return offsetlo + max(0, offsetdur)

        continuous = True
        try:
            split_cont = value.rsplit('_', 1) #for continuous variables, the value is in format {Value}_{Ineq}
            int(split_cont[0])
        except ValueError:
            continuous = False 

        maxoffsetNum = -1 #account for multiple primitives associated with same device and state, we just need to check for 
                          #the primitive that requires us to wait the longest.
        valid_idx = []

        for i in range(len(ruleStr)):
            keyname, oper, ineq, intval, statelist, _ts_unit = ruleStr[i]
            if keyname == device and not continuous and value in statelist:
                offsetval = computeoffset(intval, oper)
                maxoffsetNum = offsetval if offsetval > maxoffsetNum else maxoffsetNum
                valid_idx.append(i)
            elif keyname == device and continuous and value == (statelist[0] + '_' + ineq):
                offsetval = computeoffset(intval, oper)
                maxoffsetNum = offsetval if offsetval > maxoffsetNum else maxoffsetNum
                valid_idx.append(i)
            
        temprule = [ruleStr[i] for i in range(len(ruleStr)) if i not in valid_idx]
        offset_seed = random.randint(maxoffsetNum, self.timebound)

        #we are ok as long as we wait more than offset timestamps, no point to wait more than timebound,
        #but the rule can be satisfied before the offset_seed since it is not the minimum
        for i in range(len(temprule)):
            keyname, oper, ineq, intval, statelist, ts_unit = temprule[i]
            #adjust our intval for rule to be satisfied after witing offset_seed timestamps
            modified_intval = (max(intval[0] - offset_seed, 0), max(intval[1] - offset_seed, 0), intval[2])
            temprule[i] = keyname, oper, ineq, modified_intval, statelist, ts_unit

        if not continuous:
            Events, currChg, _vio, _rs = self._generateDontForOneSTLRule(device, value, ruleStr, False)
        else:
            thevalue, theineq = value.rsplit('_', 1)
            tval = int(thevalue)
            genvalue = -1
            if theineq == '<':
                genvalue = random.randint(tval-10, tval-1)
            elif theineq == '<=':
                genvalue = random.randint(tval-10, tval)
            elif theineq == '>=':
                genvalue = random.randint(tval, tval+10)
            else:
                genvalue = random.randint(tval+1, tval+10)
            
            #the tempcurChg currently is generated with a dummy value, as we dont handle continuous data in DONT rules.
            Events, tempcurChg, _vio, _rs = self._generateDontForOneSTLRule(device, value, ruleStr, False)
            currChg = (tempcurChg[0], tempcurChg[1], tempcurChg[2], genvalue)

        return Events, currChg, offset_seed, ruleStr

    def _generateDontForOneSTLRule(self, device, value, ruleStr, violation):
        '''
            @param device: the device_state tuple specified by the rule
            @param value: the value specified by the rule
            @param ruleStr: the rule
            @param violation: whether we create a dont rule violation if no random change impacts our 
            setup.

            @return: A 4-tuple of, (list of events happening before, current change, whether we set it to violate, ruleStr we used to generate)
        '''
        def getValidContinuousState(ineq, value):
            if ineq == '<':
                return random.randint(value-10, value-1)
            elif ineq == '<=':
                return random.randint(value-10, value)
            elif ineq == '>=':
                return random.randint(value, value+10)
            else:
                return random.randint(value+1, value+10)

        currentDate = datetime.datetime.now(datetime.timezone.utc)
        date_seed = random.randint(0, 86400) #any time within 24 hours from now
        startDate = currentDate + datetime.timedelta(seconds = date_seed)

        Events = []
        ts_unit = ''
        for rule_device, oper, ineq, interval, possibleStates, ts in ruleStr:
            dname, dstate = rule_device.rsplit('_', 1)
            ts_unit = ts #all time stamp unit should be the same

            hi, lo, dur = interval
            offsetmax = -1
            if oper == 'G' or oper == 'GF':
                offsetmax = hi - max(0, dur)
            else:
                offsetmax = lo + max(0, dur)

            #have a satisfying change at a timestamp before offsetmax, so that the condition is likely to be
            #satisfied if no other changes happens in the interval.
            timestampseed = random.randint(offsetmax, self.timebound)
            date_str = find_timediff(startDate, timestampseed, ts)

            vtemp, stateval = -1, ''

            try:
                vtemp = int(possibleStates[0])
            except ValueError:
                stateval = possibleStates[random.randint(0, len(possibleStates)-1)]
            else:
                stateval = str(getValidContinuousState(ineq, vtemp))
            
            Events.append((date_str, dname, dstate, stateval))
        
        startDate_str = startDate.strftime("%Y-%m-%dT%H:%M:%S")
        specifiedname, specifiedstate = device.rsplit('_', -1)

        if not violation: #make it satisfied if no random events before has tampered with our setup
            currChg = (startDate_str, specifiedname, specifiedstate, value)

        else: #create a violation
            #we assume devicedict has at least 2 values for each tuple, so this will not be empty
            possible_values = [va for va in self.devicedict[device] if va != value]
            violate_value = possible_values[random.randint(0, len(possible_values) - 1)]
            currChg = (startDate_str, specifiedname, specifiedstate, violate_value)

        return self._postProcess(Events, ts_unit, startDate), currChg, violation, ruleStr

    def _generateForOneImmediateRule(self, device, beforeValue, afterValue, ruleStr, violation):

        def getValidState(device, possibleStates):
            pickState = possibleStates[random.randint(0, len(possibleStates)-1)]
            intval = 1
            try:
                intval = int(pickState)
            except ValueError: #discrete
                return pickState
            except TypeError:
                print(possibleStates)
                print(pickState)
                raise Exception("this should not happen")
            else:
                gap = self.gapdict[device]
                return str(random.randint(intval, intval+gap-1))

        currentDate = datetime.datetime.now(datetime.timezone.utc)
        date_seed = random.randint(0, 86400) #any time within 24 hours from now
        startDate = currentDate + datetime.timedelta(seconds = date_seed)

        Events = []
        ts_unit = ''
        for rule_device, beforeState, afterState, stateChange, negate, ts in ruleStr:
            dname, dstate = rule_device.rsplit('_', 1)
            ts_unit = ts 

            if not stateChange and not negate: #device stays the same state, just pick a random time for the event
                timestampseed = random.randint(1, self.timebound) #has to be the state for at lest 1 second
                date_str = find_timediff(startDate, timestampseed, ts)
                stateval = getValidState(rule_device, [beforeState])
                Events.append((date_str, dname, dstate, stateval))
            
            elif not negate:
                timestampseed_after = random.randint(0, 1)
                date_str_after = find_timediff(startDate, timestampseed_after, ts)
                timestampseed_before = random.randint(timestampseed_after, self.timebound)
                date_str_before = find_timediff(startDate, timestampseed_before, ts)

                stateval_before = getValidState(rule_device, [beforeState])
                stateval_after = getValidState(rule_device, [afterState])
                #python sort is stable, guarentee to have stateval before appear before stateval after
                Events.append((date_str_before, dname, dstate, stateval_before))
                Events.append((date_str_after, dname, dstate, stateval_after))
            
            elif not stateChange:
                stateChange_seed = random.random() #the device can either perform an immediate change or not
                rulestates = self.devicedict[rule_device]
                if stateChange_seed < 0.35: #not perform a change
                    timestampseed = random.randint(1, self.timebound) #has to be the state for at lest 1 second
                    date_str = find_timediff(startDate, timestampseed, ts)
                    avail_states = [va for va in rulestates if va != beforeState]
                    stateval = getValidState(rule_device, avail_states)
                    Events.append((date_str, dname, dstate, stateval))
                else:
                    picked_start = rulestates[random.randint(0, len(rulestates)-1)]
                    avail_states = [va for va in rulestates if va != picked_start]
                    stateval_before = getValidState(rule_device, [picked_start])
                    stateval_after = getValidState(rule_device, avail_states)

                    timestampseed_after = random.randint(0, 1)
                    date_str_after = find_timediff(startDate, timestampseed_after, ts)
                    timestampseed_before = random.randint(timestampseed_after, self.timebound)
                    date_str_before = find_timediff(startDate, timestampseed_before, ts)
                    
                    Events.append((date_str_before, dname, dstate, stateval_before))
                    Events.append((date_str_after, dname, dstate, stateval_after))

            else:
                stateChange_seed = random.random() #the device can either perform an immediate change or not
                rulestates = self.devicedict[rule_device]
                if stateChange_seed < 0.35: #not perform a change
                    timestampseed = random.randint(1, self.timebound) #has to be the state for at lest 1 second
                    date_str = find_timediff(startDate, timestampseed, ts)
                    stateval = getValidState(rule_device, rulestates)
                    Events.append((date_str, dname, dstate, stateval))
                else:
                    picked_start = rulestates[random.randint(0, len(rulestates)-1)]
                    if picked_start == beforeState:
                        avail_states = [va for va in rulestates if va != picked_start and va != afterState]
                    else:
                        avail_states = [va for va in rulestates if va != picked_start]
                    stateval_before = getValidState(rule_device, [picked_start])
                    stateval_after = getValidState(rule_device, avail_states)

                    timestampseed_after = random.randint(0, 1)
                    date_str_after = find_timediff(startDate, timestampseed_after, ts)
                    timestampseed_before = random.randint(timestampseed_after, self.timebound)
                    date_str_before = find_timediff(startDate, timestampseed_before, ts)

                    Events.append((date_str_before, dname, dstate, stateval_before))
                    Events.append((date_str_after, dname, dstate, stateval_after))
        
        startDate_str = startDate.strftime("%Y-%m-%dT%H:%M:%S")
        specifiedname, specifiedstate = device.rsplit('_', -1)

        currbefore_timestamp = random.randint(1, self.timebound)
        currbefore_datestr = find_timediff(startDate, currbefore_timestamp, ts)
        Events.append((currbefore_datestr, specifiedname, specifiedstate, getValidState(device, [beforeValue])))

        if not violation: #make it satisfied if no random events has tampered with our setup
            currChg = (startDate_str, specifiedname, specifiedstate, afterValue)
        else:
            possible_values = [va for va in self.devicedict[device] if va != afterValue]
            violation_value =  getValidState(device, possible_values)
            currChg = (startDate_str, specifiedname, specifiedstate, violation_value)

        return self._postProcess(Events, ts_unit, startDate), currChg, violation, ruleStr

    def _postProcess(self, Events, ts_unit, startDate):
        '''
            We have the necessity for the highly likely true factor from previous steps, 
            now we add in random states and convert Event date to correct format as output
        '''
        for ts_diff in range(self.timebound, -1, -1):
            number_seed = random.random()
            #for simplicity, at most 2 random device changes can happen at the same timestamp
            if number_seed < 0.5:
                number_picked = 0
            elif number_seed < 0.9:
                number_picked = 1
            else:
                number_picked = 2

            for i in range(number_picked):
                picked_device = self.devices[random.randint(0, len(self.devices)-1)]
                dname, dstate = picked_device.rsplit('_', 1)

                poss_values = self.devicedict[picked_device]
                try:
                    int(poss_values[0])
                except ValueError:
                    picked_value = poss_values[random.randint(0, len(poss_values)-1)]
                else:
                    #TODO: this random value for continuous variable may need refine, lets see how it goes for now.
                    picked_value = str(random.randint(int(poss_values[0]), int(poss_values[1])))

                date_str = find_timediff(startDate, ts_diff, ts_unit)
                Events.append((date_str, dname, dstate, picked_value))

        #sort event base on timestamps
        Events = sorted(Events, key = lambda x: x[0])

        #convert Event date to string format
        for i in range(len(Events)):
            dateobj, dname, dstate, picked_device = Events[i]
            Events[i] = dateobj.strftime("%Y-%m-%dT%H:%M:%S"), dname, dstate, picked_device
        return Events 