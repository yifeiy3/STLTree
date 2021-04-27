from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from ParseRules import convertRules
from MonitorRules import MonitorRules
from Samsung.getDeviceInfo import Monitor
import argparse

hostName = "192.168.1.107"
serverPort = 10001
APIKey = "ff5c476f-1b99-4fc7-a747-0bed31268f11"
APIEndpt = "https://graph.api.smartthings.com/api/smartapps/installations/29b89160-cf6b-470d-b3e6-c524a48cd124"

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
                        stateChgs.append((res['date'], res['name'], res['state'], res['value']))

        valid, should = self.rm.checkViolation(currentquery, stateChgs=stateChgs)
        if valid == 'False':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes("{0}.{1}()".format(currentquery[1], should), "utf-8"))
        else:   
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(bytes("good", "utf-8"))

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

    ruledict = convertRules()
    md = Monitor(APIKey, APIEndpt)
    devices = md.getThings("all")
    alldevices = []
    devicedict = {}
    tempdict = {}

    for key in ruledict.keys():
        parseKey = key.rsplit('_', 1)
        dname, dstate = parseKey[0], parseKey[1]
        if dname in tempdict:
            tempdict[dname].append(dstate)
        else:
            tempdict[dname] = [dstate]
    
    for device in devices:
        alldevices.append(device["name"])
        devicedict[device["name"]] = (device["id"], tempdict[device["name"]])
        
    md_rules = MonitorRules(ruledict, alldevices)
    webServer = my_http_server(md_rules, md, devicedict, args.important)
    try:
        webServer.server.serve_forever()
        print("Server started with ip http://{0}:{1}".format(hostName, serverPort))
    except KeyboardInterrupt:
        pass

    webServer.server.server_close()
    print("Server stopped")

