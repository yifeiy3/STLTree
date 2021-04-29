import requests, json

class Monitor():
    def __init__(self, tkey, tendpoint):
        self._key = tkey #device's api key
        self._endpoint = tendpoint #device's api endpoint

    def _retrieveInfo(self, param):
        url = self._endpoint + "/endpoint"
        headers = {"Authorization":"Bearer {0}".format(self._key)}
        res = requests.get(url, headers = headers, params = param)
        return res.json()
    
    def getThings(self, thing):
        param = {"function":"things",
            "kind":thing}
        return self._retrieveInfo(param)
    
    def getStates(self, stateName, thing_id, since=None, max_sts = 50000):
        if since is None:
            param = {"function":"states",
                "state":stateName,
                "thing_id":thing_id,
                "max":max_sts}
        else:
            param = {"function":"states",
                "state":stateName,
                "thing_id":thing_id,
                "since":since,
                "max":max_sts}
        return self._retrieveInfo(param)
    
    def getEvents(self, thing_id, max_evts=50000, since=None):
        param = {"function":"events",
            "max":max_evts,
            "since":since,
            "id":thing_id}
        return self._retrieveInfo(param)

    def getHomeMode(self):
        param = {"function":"mode"}
        return self._retrieveInfo(param)

    def modifyState(self, thing_id, stateName, stateValue):
        url = "https://api.smartthings.com/v1/devices/{0}/commands".format(thing_id)
        headers = {"Authorization":"Bearer {0}".format(self._key), "content-type" : "application/json","accept" : "application/json"}
        postdata = {
            "commands": [
                {
                    "component":"main",
                    "capability":stateName,
                    "command":"lock",
                    "arguments":[]
                }
            ]
        }
        res = requests.post(url, json=postdata, headers = headers)
        print(json.dumps(postdata))
        print("request status code: {0}".format(res.status_code))
        print("request result: {0}".format(res.json()))