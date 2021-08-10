from Fuzztesting.rulefuzz import ruleGeneration
from Fuzztesting.logfuzz import logGeneration
from ParseRules import convertDoRules, convertImmediateDoRules
from MonitorRules import MonitorRules
from datetime import datetime

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

with open(DontOutput, 'w') as dontfile:
    dontfile.write('Device dict: {0} \n\n'.format(device_dict))
    dontfile.write("STL Dont rules: {0} \n\n".format(STLrule))
    dontfile.write("Immediate Dont rules: {0} \n\n".format(immerule))

    for i in range(len(DontRuleLogs)):
        eventebefore, currChg, violationTag, rs = DontRuleLogs[i]
        dontfile.write("{0}. Events Before \n\t {1} \n\t Currchg: {2} (Generated with violation tag: {3})\n\n".format(
            i, eventebefore, currChg, violationTag
        ))
        dontfile.write("\tGenerated under ruleStr: {0}\n\n".format(rs))
        #we dont care about dont rules for now
        start = datetime.now()
        valid, shouldState, _chg = monitor.checkViolation(currChg, stateChgs=eventebefore)
        elapsed = 'Time elpased (hh:mm:ss.ms) {}'.format(datetime.now() - start)

        dontfile.write("Monitor Output: Valid: {0}, ShouldState: {1}, {2}\n\n".format(valid, shouldState, elapsed))

with open(DoOutput, 'w') as dofile:
    dofile.write('Device dict: {0} \n\n'.format(device_dict))
    dofile.write("STL Do rules: {0} \n\n".format(STLDOrule))
    dofile.write("Immediate Do rules: {0} \n\n".format(immeDOrule))

    for i in range(len(DoRuleLogs)):
        eventebefore, currChg, scheduleInfo, rs = DoRuleLogs[i]
        chg_device, chg_state, waitTime = scheduleInfo

        dofile.write("{0}. Events Before \n\t {1} \n\t Currchg: {2} (Generated with hopes of changing {3} to {4} after waittime {5})\n\n".format(
            i, eventebefore, currChg, chg_device, chg_state, waitTime
        ))
        dofile.write("\tGenerated under ruleStr: {0}\n\n".format(rs))

        #we need to care about dont rules, sicne if a dont rule happen, do rule will not be checked for current change.
        start = datetime.now()
        valid, shouldState, chg = monitor.checkViolation(currChg, stateChgs=eventebefore)
        elapsed = 'Time elpased (hh:mm:ss.ms) {}'.format(datetime.now() - start)

        dofile.write("Monitor Output: Valid: {0}, ShouldState: {1}, Chg:{2}\n {3}\n\n".format(valid, shouldState, chg, elapsed))
