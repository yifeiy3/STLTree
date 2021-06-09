from apscheduler.schedulers.background import BackgroundScheduler
from dictUtil import addOrAppendDepth2
from capabilities import CAPABILITY_TO_COMMAND_DICT
import datetime
from MonitorRules import MonitorRules
from Samsung.getDeviceInfo import Monitor

class Scheduler():
    def __init__(self, deviceMonitor, devicedict, ruleMonitor):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.storedJobs = {} #TODO: Do we need this?
        self.dm = deviceMonitor #we would need this to execute our jobs
        self.rm = ruleMonitor #we would need this to check whether our command precondition is still satisfied
        self.devicedict = devicedict #we would need this to retrieve device id

    def _sendCommand(self, device, newStateValue, ruleStr):
        '''
            Sends a request to Samsung Smartthing hub to change device state according to DO rule
            @param device: deviceName_deviceState tuple
            @param newStateValue: the new state value device should change to
            @param ruleStr: The rule corresponding to the device change, we check for one last time if this is satisfied
            before sending command to monitor
        '''
        parseName = device.rsplit('_', 1)
        dname, dstate = parseName[0], parseName[1]

        #check if we still need to make the scheduled change
        if self.rm.checkCommand(dname, dstate, newStateValue, ruleStr):
            stateChgCmd = CAPABILITY_TO_COMMAND_DICT[dstate][newStateValue]
            deviceid = self.devicedict[dname][0]
            self.dm.changeDeviceState(deviceid, dname, stateChgCmd)

        print("sending command to change device: {0}, state: {1} to new value command {2}".format(deviceid, dstate, stateChgCmd))

    def scheduleDoRules(self, antChanges):
        '''
            This app modifies our scheduler by adding the anticipated
            changes to current scheduling
        '''
        #adds new changed to the already scheduled changes
        for timedelay in antChanges.keys():
            device, newStateValue, theRule = antChanges[timedelay]
            #give 2 seconds of react time on the Samsung hub, we only change state if
            #the Do rule is violated.
            newjob = self.scheduler.add_job(
                lambda: self._sendCommand(device, newStateValue, theRule),
                'date',
                run_date=datetime.datetime.now() + datetime.timedelta(seconds=timedelay)
            )
            addOrAppendDepth2(self.storedJobs, device, newStateValue, newjob)
    