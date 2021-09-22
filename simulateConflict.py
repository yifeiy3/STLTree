from Samsung.getDeviceInfo import Monitor 
from capabilities import returnCommand
import pickle 
import time 
'''
    Given a log of learned from conflictVerification.py, we can 
    simulate a series of events on Samsung Smartthings according to
    the log to see the actual outcome for conflicts.

    Currently ts unit only support seconds, but it should not be too much of a issue.
'''

APIKey = "ff5c476f-1b99-4fc7-a747-0bed31268f11"
APIEndpt = "https://graph.api.smartthings.com/api/smartapps/installations/3158c036-1dec-4c1e-83cc-e466d59962ad"

md = Monitor(APIKey, APIEndpt)
timebound, conflicts = -1, []

outfile = 'extensions/simulationLog.txt'

#generate a dummy example#
STLrules = []
Immerules = []
log = [
    (10, 'Thermostat', 'temperature', '71'),
    (9, 'Virtual Switch1', 'switch', 'off'),
    (5, 'Door', 'lock', 'locked'),
    (1, 'Door', 'lock', 'unlocked'),
    (0, 'Door', 'lock', 'locked'),
]

# with open('extensions/analysisResult.pkl', 'rb') as logs: 
#     #same name as generated output in extensions/conflictVerification.py
#     timebound, conflicts = pickle.load(logs)

#Example conflict and timebound
conflicts = [(STLrules, Immerules, log)]
timebound = 10

if not conflicts:
    raise Exception("Unable to load conflict analysis result file")

with open(outfile, 'w') as out:
    for STLrules, Immerules, log in conflicts:
        out.write('Simulating the conflict with STL rules: \n {0}'.format(STLrules))
        out.write('\nAnd immediate rules: {0}'.format(Immerules))
        out.write('\nUnder Log\n {0} \n'.format(log))
    
        processedLog = [] #we need to generate timing with respect to the first event rather than last event.
        
        starttime = log[0][0] #first timestamp
        for timestamp, deviceName, deviceState, strVal in log:
            timediff = starttime - timestamp #how much time away
            #Todo: handle continuous variables...
            stateChgCmd, paramval = returnCommand(deviceState, strVal)
            processedLog.append((timediff+1, deviceName, stateChgCmd, paramval)) 
            #since time is relative, we add 1 so no events run immediately
            #easier to handle.
        
        res = md.simulateLog(processedLog)
        print("Got result: {0}".format(res))

        #time.sleep(timebound + 5) #make sure the scheduling is completed.


    
