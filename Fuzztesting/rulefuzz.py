import random 
import math


def addOrAppendDepth2(d, key1, key2, value):
    '''
        for a dictionary d, we either set d[key1][key2] = [value]
        or we let d[key1][key2].append(value)
    '''
    if key1 in d.keys():
        if key2 in d[key1].keys():
            d[key1][key2].append(value)
        else:
            d[key1][key2] = [value]
    else:
        d[key1] = {key2 : [value]}
'''
    randomly generate rules for the environment for testing purposes. Both STL and immediate
'''
class ruleGeneration():
    def __init__(self, devicedict, count = 10, maxDepth = 4):
        '''
            @param devicedict: a dictionary mapping device_state tuple to all the possible state value it may have
                         if it is of a continuous state, it will be a 2 item list of [lowerbound ,upperbound]
            @param count: the number of rules to generate per iteration
            @param maxDepth: the maximum number of primitives per rule, >= 1
        '''
        self.deviceInfo = devicedict
        self.count = count 
        self.maxDepth = max(1, maxDepth)
    
    def generateSTL(self, ruledict, timebound):
        '''
            @param ruledict: the current STLrules in the envirionment, a dictionary mapping device_state tuple
            to a dictionary mapping available values to ruleStrings.
        '''
        def handleSpaceParamDiscrete(values, ineq):
            possibleStates = []
            l = len(values)
            if ineq == '<':
                value_idx = random.randint(1, l - 1)
                possibleStates = [values[i] for i in range(0, value_idx)]
            elif ineq == '>':
                value_idx = random.randint(0, l - 2)
                possibleStates = [values[i] for i in range(value_idx + 1, l)]
            elif ineq == '>=':
                value_idx = random.randint(1, l-1)
                possibleStates = [values[i] for i in range(value_idx, l)]
            else:
                value_idx = random.randint(0, l - 2)
                possibleStates = [values[i] for i in range(0, value_idx+1)]
            return possibleStates

        def findSpaceParam(values):
            '''
                define the inequality and possible states for the device we found
            '''
            if len(values) < 2:
                raise Exception("There are less than 2 values for the device, no point to learn rule. Value: {0}".format(values))
            ineq, possibleStates = '', []
            lb, ub = -1, -1
            ineq_seed = random.randint(1, 4)
            if ineq_seed == 1:
                ineq = '<'
            elif ineq_seed == 2:
                ineq = '>'
            elif ineq_seed == 3:
                ineq = '>='
            else:
                ineq = '<='

            try:
                lb = int(values[0])
                ub = int(values[1])
            except ValueError:
                possibleStates = handleSpaceParamDiscrete(values, ineq)
            else:
                #handle continuous data, assuming ub - lb >> 1 so we wont have round edge cases, which is true in Smartthings environment
                #shrink value to be random within 0.25, 0.75 range to make rules less extreme.
                value = str(random.randint(math.ceil(lb + (ub - lb)*0.25), math.floor(lb + (ub - lb) * 0.75)))
                possibleStates = [value]
            return ineq, possibleStates
        
        def findTimeParam(timebound):
            '''
                define the oper and time interval for the device we found
            '''
            #for our case, timeparam is in [hi. lo, dur] by timestamps from current time.
            oper, timeparam = '', (-1, -1, -1)
            oper_seed = random.randint(1, 4)
            ub_seed = random.randint(1, timebound)
            if oper_seed == 1:
                oper = 'F'
                lb_seed = random.randint(0, ub_seed-1)
                timeparam = (ub_seed, lb_seed, -1)
            elif oper_seed == 2:
                oper = 'G'
                lb_seed = random.randint(0, ub_seed-1)
                timeparam = (ub_seed, lb_seed, -1)
            elif oper_seed == 3:
                oper = 'FG'
                lb_seed = random.randint(0, ub_seed-1)
                dur_seed = random.randint(1, max(1, (ub_seed - lb_seed)//2)) #no point to have very large duration intervals
                timeparam = (ub_seed, lb_seed, dur_seed)
            else:
                oper = 'GF'
                lb_seed = random.randint(0, ub_seed - 1)
                dur_seed = random.randint(1, max(1, (ub_seed - lb_seed)//2)) #no point to have very large duration intervals
                timeparam = (ub_seed, lb_seed, dur_seed)
            return oper, timeparam

        #specifying device_state and value for the rule, the rule can not be for continuous variable so we iterate until we encounter a non continuous one.
        continous = True 
        while continous:
            available_devices = [de for de in self.deviceInfo.keys()]
            device_idx = random.randint(0, len(available_devices)-1)
            device = available_devices.pop(device_idx) #this device can not be a part of the rulestring

            available_values = self.deviceInfo[device]
            value = available_values[random.randint(0, len(available_values) - 1)]
            try:
                int(value)
            except ValueError:
                continous = False #non continuous variable, we proceed.

        depth = random.randint(1, self.maxDepth)
        rulestr = []
        #generate our rule
        for i in range(depth):
            rule_device = available_devices[random.randint(0, len(available_devices)-1)]
            rule_values = self.deviceInfo[rule_device]
            ineq, possiblevalues = findSpaceParam(rule_values)
            oper, timeparam = findTimeParam(timebound)

            rulestr.append((rule_device, oper, ineq, timeparam, possiblevalues, 'seconds'))

        addOrAppendDepth2(ruledict, device, value, rulestr)

    def generateImmediate(self, ruledict, gapdict, timebound):
        '''
            @param gapdict: a dict used to handle continuous variables
        '''
        continuous = True 
        while continuous:
            available_devices = [de for de in self.deviceInfo.keys()]
            device_idx = random.randint(0, len(available_devices)-1)
            device = available_devices.pop(device_idx) #this device can not be a part of the rulestring
            available_values = self.deviceInfo[device]
            valueBefore = available_values[random.randint(0, len(available_values) - 1)]
            valueAfter = available_values[random.randint(0, len(available_values) - 1)]
            try:
                int(valueBefore)
            except ValueError:
                continuous = False

        depth = random.randint(1, self.maxDepth)
        rulestr = []
        avail_devices = [de for de in self.deviceInfo.keys() if de != device]

        for i in range(depth):
            rule_device = avail_devices[random.randint(0, len(avail_devices)-1)]
            rule_values = self.deviceInfo[rule_device]
            rule_Before = rule_values[random.randint(0, len(rule_values) - 1)]
            try:
                int(rule_Before)
            except ValueError: #discrete, we are ok.
                rule_After = rule_values[random.randint(0, len(rule_values) - 1)]
            else: #continuous case
                if rule_device in gapdict.keys():
                    gap = gapdict[rule_device]
                else:
                    gap = (int(rule_values[1]) - int(rule_values[0])) // 5 #at most 5 classes
                    gapdict[rule_device] = gap 
                before_seed = random.randint(0, 4)
                after_seed = random.randint(before_seed, 4)
                rule_Before = str(int(rule_values[0]) + before_seed * gap)
                rule_After = str(int(rule_values[0]) + after_seed * gap)

            statechange = rule_Before != rule_After
            falsebranch = True if random.randint(0, 1) == 0 else False 
            
            rulestr.append((rule_device, rule_Before, rule_After, statechange, falsebranch, 'seconds'))
        
        addOrAppendDepth2(ruledict, device, (valueBefore, valueAfter), rulestr)

    def generate(self, timebound):
        '''
            @param timebound: the bound for STLrules. i.e. the maximum number for hi
        '''
        if(timebound < 3):
            raise Exception("time bound insufficient, please give a value greater than 3")
        ruledict = {}
        immeruledict = {}
        gapdict = {}

        for i in range(self.count):
            seed = random.random()
            if seed < 0.65:
                self.generateSTL(ruledict, timebound)
            else:
                self.generateImmediate(immeruledict, gapdict, timebound)

        return ruledict, immeruledict, gapdict

if __name__ == '__main__':
    device_dict = {
        'Door_lock': ['locked', 'unlocked'],
        'Virtual Switch 2_switch': ['on', 'off'],
        'Virtual Switch1_switch': ['on', 'off'],
        'Thermostat_temperature': ['75', '95'],
    }
    timebound = 10

    rf = ruleGeneration(device_dict, count=5)

    STLrule, Immerule, gapdict = rf.generate(timebound)
    print("Temporal rule:")
    print(STLrule)
    print("\nImmediate rule:")
    print(Immerule)
    print("\nGap dict:")
    print(gapdict)