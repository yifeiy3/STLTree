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
    
    def getStates(self, stateName, thing_id, since=None, max_sts = 1000):
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
    
    def getEvents(self, thing_id, max_evts=1000, since=None):
        param = {"function":"events",
            "max":max_evts,
            "since":since,
            "id":thing_id}
        return self._retrieveInfo(param)

    def getHomeMode(self):
        param = {"function":"mode"}
        return self._retrieveInfo(param)
