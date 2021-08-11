from Fuzztesting.rulefuzz import ruleGeneration
from Fuzztesting.logfuzz import logGeneration
from ParseRules import convertDoRules, convertImmediateDoRules
from MonitorRules import MonitorRules, sec_diff
from datetime import datetime

def EventsBeforeToString(events, currchg):
    currChg_date = currchg[0]
    #add a column relative timestamps rather than true time for better visualization
    for i in range(len(events)):
        time, device, state, value = events[i]
        events[i] = (sec_diff(time, currChg_date, 'seconds'), time, device, state, value)

    s = ''
    for items in events:
        s += '{0},\n\t'.format(items)
    return s 

def DontRuleDictToString(ruledict):
    s = ''
    for devices in ruledict.keys():
        s += '\n\t{0}:'.format(devices)
        for values in ruledict[devices].keys():
            s += '\n\t\t{0}:'.format(values)
            for rules in ruledict[devices][values]:
                s+= '\n\t\t\t{0}'.format(rules)
    return s 

def DoRuleDictToString(ruledict):
    s = ''
    for devices in ruledict.keys():
        s += '\n\t{0}:'.format(devices)
        for values in ruledict[devices].keys():
            s += '\n\t\t{0}:'.format(values)
            for chg_devices in ruledict[devices][values].keys():
                s+= '\n\t\t\t{0}'.format(chg_devices)
                for chg_values in ruledict[devices][values][chg_devices].keys():
                    s+= '\n\t\t\t\t{0}'.format(chg_values)
                    for rules in ruledict[devices][values][chg_devices][chg_values]:
                        s+= '\n\t\t\t\t\t{0}'.format(rules)
    return s 

#dictionary mapping device_state tuple to their available states. In the case for continuous variables,
#the list will be length 2, with lowerbound, upperbound.
device_dict = {
        'Door_lock': ['locked', 'unlocked'],
        'Virtual Switch 2_switch': ['on', 'off'],
        'Virtual Switch1_switch': ['on', 'off'],
        'Thermostat_temperature': ['75', '95'],
    }

#maximum number for hi can be in each STLTree rules, thus we only generate device changes that is within the last
#timebound seconds.
timebound = 10

maxDepth = 4 #depth, maximum number of primitive per rule, >=1
count = 10 # number of rules we generate per iteration of rf.generate

rf = ruleGeneration(device_dict)

#we generate a dictionary of STL and immediate DONT rules. The gap dict maps device_state tuples to the gap
#amount it used for state classification.
STLrule, immerule, gapdict = rf.generate(timebound)

#add in the DO dicts also
STLDOrule = convertDoRules(STLrule)
immeDOrule = convertImmediateDoRules(immerule)

lf = logGeneration(device_dict, STLrule, immerule, STLDOrule, immeDOrule, gapdict, timebound)

amountPerRule = 2 #how many logs we generate per rule for log fuzzing

DontRuleLogs = lf.generateDontLog(amountPerRule)
DoRuleLogs = lf.generateDoLog(amountPerRule)

monitor = MonitorRules(STLrule, immerule, None, device_dict.keys(), 5, True)

DontOutput = 'Fuzztesting/dontrule.txt'
DoOutput = 'Fuzztesting/do.txt'
DictOutput = 'Fuzztesting/dictraw.txt' #add a raw file for dictionaries to be easy to copy over for debugging

with open(DictOutput, 'w') as dictfile:
    dictfile.write('Device dict: {0} \n\n'.format(device_dict))
    dictfile.write("STL Dont rules: {0} \n\n".format(STLrule))
    dictfile.write("Immediate Dont rules: {0} \n\n".format(immerule))
    dictfile.write("STL Do rules: {0} \n\n".format(STLDOrule))
    dictfile.write("Immediate Do rules: {0} \n\n".format(immeDOrule))

with open(DontOutput, 'w') as dontfile:
    dontfile.write('Device dict: {0} \n\n'.format(device_dict))
    dontfile.write("STL Dont rules: {0} \n\n".format(DontRuleDictToString(STLrule)))
    dontfile.write("Immediate Dont rules: {0} \n\n".format(DontRuleDictToString(immerule)))

    for i in range(len(DontRuleLogs)):
        eventebefore, currChg, violationTag, rs = DontRuleLogs[i]
        #we dont care about dont rules for now
        start = datetime.now()
        valid, shouldState, respectiveRule, _chg = monitor.checkViolation(currChg, stateChgs=eventebefore)
        elapsed = 'Time elpased (hh:mm:ss.ms) {}'.format(datetime.now() - start)

        dontfile.write("{0}. Events Before \n\t{1}\n\t Currchg: {2} (Generated with violation tag: {3})\n\n".format(
            i, EventsBeforeToString(eventebefore, currChg), currChg, violationTag
        ))
        dontfile.write("\tGenerated under ruleStr: {0}\n\n".format(rs))

        dontfile.write("Monitor Output: Valid: {0}, ShouldState: {1}, \n Under Rule: {2} \n {3}\n\n".format(valid, shouldState, respectiveRule, elapsed))

with open(DoOutput, 'w') as dofile:
    dofile.write('Device dict: {0} \n\n'.format(device_dict))
    dofile.write("STL Do rules: {0} \n\n".format(DoRuleDictToString(STLDOrule)))
    dofile.write("Immediate Do rules: {0} \n\n".format(DoRuleDictToString(immeDOrule)))

    for i in range(len(DoRuleLogs)):
        eventebefore, currChg, scheduleInfo, rs = DoRuleLogs[i]
        chg_device, chg_state, waitTime = scheduleInfo

        #we need to care about dont rules, sicne if a dont rule happen, do rule will not be checked for current change.
        start = datetime.now()
        valid, shouldState, resrule, chg = monitor.checkViolation(currChg, stateChgs=eventebefore)
        elapsed = 'Time elpased (hh:mm:ss.ms) {}'.format(datetime.now() - start)

        dofile.write("{0}. Events Before \n\t{1}\n\t Currchg: {2} (Generated with hopes of changing {3} to {4} after waittime {5})\n\n".format(
            i, EventsBeforeToString(eventebefore, currChg), currChg, chg_device, chg_state, waitTime
        ))
        dofile.write("\tGenerated under ruleStr: {0}\n\n".format(rs))

        dofile.write("Monitor Output: Valid: {0}, ShouldState: {1}, \n Under Rule: {2} \n Chg:{3}\n {4}\n\n".format(valid, shouldState, resrule, chg, elapsed))
