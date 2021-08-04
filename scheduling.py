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
        self.JobsLastSecond = {} #map device to a dictionary of mapping date to corresponding scheduled state changes within the last second of current change
        self.JobsNextSecond = {} #Same map for next second
        self.dm = deviceMonitor #we would need this to execute our jobs
        self.rm = ruleMonitor #we would need this to check whether our command precondition is still satisfied
        self.devicedict = devicedict #we would need this to retrieve device id

    def _sendCommand(self, device, newStateValue, ruleStr, immediate, tsunit):
        '''
            Sends a request to Samsung Smartthing hub to change device state according to DO rule
            @param device: deviceName_deviceState tuple
            @param newStateValue: the new state value device should change to
            @param ruleStr: The rule corresponding to the device change, we check for one last time if this is satisfied
            before sending command to monitor
            @param tsunit:  whether the rule is trained under seconds or minutes as base timestamp unit,
            default is seconds.
            @param immediate: whether the rule is immediate or not
            
        '''
        parseName = device.rsplit('_', 1)
        dname, dstate = parseName[0], parseName[1]

        #check if we still need to make the scheduled change
        if self.rm.checkCommand(dname, dstate, newStateValue, ruleStr, immediate, tsunit, 0):
            stateChgCmd = CAPABILITY_TO_COMMAND_DICT[dstate][newStateValue]
            deviceid = self.devicedict[dname][0]
            self.dm.changeDeviceState(deviceid, dname, stateChgCmd)

            print("sending command to change device: {0}, state: {1} to new value command {2} under rule \n {3}".format(dname, dstate, stateChgCmd, ruleStr))

    def scheduleDoRules(self, antChanges):
        '''
            This app modifies our scheduler by adding the anticipated
            changes to current scheduling
        '''
        #adds new changed to the already scheduled changes
        for timedelay in antChanges.keys():
            for device in antChanges[timedelay].keys():
                newStateValue, theRule, immediate, tsunit = antChanges[timedelay][device]
                #give 2 seconds of react time on the Samsung hub, we only change state if
                #the Do rule is violated.
                if tsunit == 'minutes':
                    timedelay = (timedelay + 1)*60 #we give 1 tsunit room for environment to perform change
                else:
                    timedelay = timedelay + 1
                _newjob = self.scheduler.add_job(
                    lambda: self._sendCommand(device, newStateValue, theRule, immediate, tsunit),
                    'date',
                    run_date=datetime.datetime.now() + datetime.timedelta(seconds=timedelay)
                )
                #addOrAppendDepth2(self.storedJobs, device, newStateValue, newjob)
        
    #TODO: Consider Race conditions. Maybe we add all the jobs for the same device at same time to the self.storedJobs, and then each time sendCommand we look at all of them
    #sequentially instead of what we are doing right now.
    def scheduleDoRules_NEW(self, antChanges):
        for timedelay in antChanges.keys():
            for device in antChanges[timedelay].keys():
                newStateValue, theRule, immediate, tsunit = antChanges[timedelay][device]
                if tsunit == 'minutes':
                    timedelay = (timedelay + 1)*60 #we give 1 tsunit room for environment to perform change
                else:
                    timedelay = timedelay + 1
                
                rundatelast = datetime.datetime.now() + datetime.timedelta(seconds = timedelay)
                rundatenext = datetime.datetime.now() + datetime.timedelta(seconds = timedelay + 1)

                rundatelastkey = str(rundatelast)[:-7] #keep at nearest second
                rundatenextkey = str(rundatenext)[:-7]

                addOrAppendDepth2(self.JobsLastSecond, device, rundatelastkey, (newStateValue, theRule, immediate, tsunit))
                addOrAppendDepth2(self.JobsNextSecond, device, rundatenextkey, (newStateValue, theRule, immediate, tsunit))

                rundatelastidx = len(self.JobsLastSecond[device][rundatelastkey])
                rundatenextidx = len(self.JobsLastSecond[device][rundatenextkey])

                _newjob = self.scheduler.add_job(
                    lambda: self._sendCommand_NEW(device, rundatelastkey, rundatelastidx, rundatenextkey, rundatenextidx),
                    'date',
                    run_date=datetime.datetime.now() + datetime.timedelta(seconds=timedelay)
                )

    def _sendCommand_NEW(self, device, rundatelastkey, rundatelastidx, rundatenextkey, rundatenextidx):
        '''
            @param: rundatelastkey: the date time for the scheduled change rounded down to the second
            @param: rundatelastidx: the current index our job is in the JobsLast dictionary, to avoid race condition, only first idx will be processed
            @param: rundatenextkey: rundatelastkey + 1 second
            @param: rundatenextidx: same as rundatelastidx, but for JobsNext dictionary
        '''
        if rundatelastidx > 1 and rundatenextidx > 1:
            return #nothing need to be done
        
        parseName = device.rsplit('_', 1)
        dname, dstate = parseName[0], parseName[1]

        if rundatelastidx == 1:
            for newStateValue, theRule, immediate, tsunit in self.JobsLastSecond[device][rundatelastkey]:
                if self.rm.checkCommand(dname, dstate, newStateValue, theRule, immediate, tsunit, 0):
                    stateChgCmd = CAPABILITY_TO_COMMAND_DICT[dstate][newStateValue]
                    deviceid = self.devicedict[dname][0]
                    self.dm.changeDeviceState(deviceid, dname, stateChgCmd)
                    print("sending command to change device: {0}, state: {1} to new value command {2} under rule \n {3}".format(deviceid, dstate, stateChgCmd, theRule))

        
        if rundatenextidx == 1:
            for newStateValue, theRule, immediate, tsunit in self.JobsLastSecond[device][rundatelastkey]:
                if self.rm.checkCommand(dname, dstate, newStateValue, theRule, immediate, tsunit, 1):
                    stateChgCmd = CAPABILITY_TO_COMMAND_DICT[dstate][newStateValue]
                    deviceid = self.devicedict[dname][0]
                    self.dm.changeDeviceState(deviceid, dname, stateChgCmd)
                    print("sending command to change device: {0}, state: {1} to new value command {2} under rule \n {3}".format(deviceid, dstate, stateChgCmd, theRule))