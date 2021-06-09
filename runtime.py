from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from ParseRules import convertRules
from MonitorRules import MonitorRules
from Samsung.getDeviceInfo import Monitor
from capabilities import CAPABILITY_TO_COMMAND_DICT
from scheduling import Scheduler

import argparse
import pickle 

hostName = "192.168.1.107"
serverPort = 10001
APIKey = "ff5c476f-1b99-4fc7-a747-0bed31268f11"
APIEndpt = "https://graph.api.smartthings.com/api/smartapps/installations/54017165-5332-4a80-8e93-b23dc7d5af78"

class MyServer(BaseHTTPRequestHandler):
    def __init__(self, RuleMonitor, DeviceMonitor, devicedict, important, *args):
        '''
            @param: devicedict: a dictionary between devicename, deviceid, and corresponding attributes
            @param: important: bool, whether we check only important state changes or all changes
        '''
        self.rm = RuleMonitor
        self.dm = DeviceMonitor
        self.devicedict = devicedict
        self.important = important
        self.scheduler = Scheduler(self.dm, self.devicedict, self.rm) #scheduler to change device states according to DO rules
        BaseHTTPRequestHandler.__init__(self, *args)

    def do_GET(self):
        print(self.path)
        query = parse_qs(urlparse(self.path).query)
        print(query)
        currentquery = (query['date'][0], query['device'][0], query['state'][0], query['value'][0])
        stateChgs = []
        if self.important:
            for devices in devicedict.keys():
                deviceid, states = devicedict[devices]
                for attri in states:
                    laststates = self.dm.getStates(attri, deviceid, max_sts=5)
                    for res in laststates:
                        stateChgs.append((res['date'], devices, res['state'], res['value']))

        valid, should, antChgs = self.rm.checkViolation(currentquery, stateChgs=stateChgs)
        print("{0}, {1}".format(valid, should))

        #handling DONT rules
        if not valid:
            device = query['device'][0]
            deviceid = devicedict[device][0]
            #get the command corresponding to state and value that the device should be.
            stateChgCmd = CAPABILITY_TO_COMMAND_DICT[currentquery[2]][currentquery[3]]
            self.dm.changeDeviceState(deviceid, device, stateChgCmd)
               
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(bytes("event received with no violation set to {0}".format(valid), "utf-8"))

        #handling DO rules
        self.scheduler.scheduleDoRules(antChgs)

class my_http_server:
    def __init__(self, rm, dm, deviceids, important):
        def runServer(*args):
            MyServer(rm, dm, deviceids, important, *args)
        server = HTTPServer((hostName, serverPort), runServer)
        self.server = server

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Start a server that monitor\
     either all state changes or state changes for important devices only')
    parser.add_argument('--important', action = 'store', dest = 'important', default=False,
        help='Set to True if we only want to monitor important state changes')
    args = parser.parse_args()

    cdict = {}
    with open("LearnedModel/training_classdict.pkl", "rb") as dictfile:
        cdict = pickle.load(dictfile)
        print(cdict)
    if not cdict:
        raise Exception("Learned class dict not found")

    #ruledict = convertRules(cdict, error_threshold = 0.05, cap = 10, user_defined='UserDefinedRules/rule.txt')
    #print(ruledict)
    #print(ruledict['Virtual Switch 2_switch']['on'][0])
    #for testing purpose
    ruledict = {'Door_lock': {'locked':[[('Virtual Switch 2_switch', 'G', '<=', (5, 3, 2), ['off'])]]}}

    md = Monitor(APIKey, APIEndpt)
    devices = md.getThings("all")
    alldevices = []
    devicedict = {}
    tempdict = {}

    for key in cdict.keys():
        parseKey = key.rsplit('_', 1)
        dname, dstate = parseKey[0], parseKey[1]
        if dname in tempdict:
            tempdict[dname].append(dstate)
        else:
            tempdict[dname] = [dstate]
    
    for device in devices:
        if device["name"] in tempdict: #only device with interesting states we need to concern.
            alldevices.append(device["name"])
            devicedict[device["name"]] = (device["id"], tempdict[device["name"]])

    md_rules = MonitorRules(ruledict, alldevices)
    webServer = my_http_server(md_rules, md, devicedict, args.important)
    print("Server started with ip http://{0}:{1}".format(hostName, serverPort))

    try:
        webServer.server.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server.server_close()
    print("Server stopped")

