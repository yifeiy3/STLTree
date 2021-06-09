import getDeviceInfo as gd 
import json 
import pandas as pd
import IgnoredAttributes 
from datetime import datetime, timedelta


def sec_diff(date_ref, date):
    '''
        compute the second diff between date timestamps
    '''
    #we would at most have last 7 days of data so no need to worry about year 
    month_diff = int(date[5:7]) - int(date_ref[5:7])
    month_gap = 30
    if month_diff > 0:
        if int(date_ref[5:7]) in [1, 3, 5, 7, 8, 10, 12]:
            month_gap = 31 
        elif int(date_ref[5:7]) == 2:
            if(int(date_ref[0:4]) % 4 == 0):
                month_gap = 29
            else:
                month_gap = 28 
    day_diff = int(date[8:10]) - int(date_ref[8: 10]) + month_diff * month_gap
    hour_diff = int(date[11:13]) - int(date_ref[11:13])
    minute_diff = int(date[14:16]) - int(date_ref[14:16])
    sec_diff = int(date[17: 19]) - int(date_ref[17:19])
    # +10 for padding so we can analyze the first event with 10 second intervals.
    return day_diff * 86400 + hour_diff * 3600 + minute_diff * 60 + sec_diff + 10

def initialState(length):
    return ["bot"] * length

#Used to generate data from the Samsung Smartthings Environment for STL Tree learning
monitorid = "9793402f-fcb7-42af-8461-da541b539f01" #arbitrary id for a device called monitor
stdattrribute = IgnoredAttributes.IgnoredAttributeList
APIKey = "ff5c476f-1b99-4fc7-a747-0bed31268f11"
APIEndpt = "https://graph.api.smartthings.com/api/smartapps/installations/54017165-5332-4a80-8e93-b23dc7d5af78"

md = gd.Monitor(APIKey, APIEndpt)
devices = md.getThings("all")
#deviceCol = [device["name"] for device in devices]
since = None 
since = datetime.utcnow() - timedelta(minutes=150) #last 20 hour's stuff.

statechgs = []
deviceCol = []
for device in devices: 
    attris = list(set(device["attri"]))
    attrivalues = device["attrival"]
    print(attrivalues)
    for attribute in attris: 
        if attribute in stdattrribute:
            continue
        else:
            deviceCol.append(device["name"] + "_" + attribute)
            #print("Attribute Name: {0}".format(attribute))
            states = md.getStates(attribute, device["id"], since=since)
            print(device["name"])
            print((states)) 
            #for each device, at most 200 states is stored....
            for state in states:
                statechgs.append((state["date"], device["name"], state["state"], state["value"]))

if not statechgs:
    raise Exception("We have no data in the environment")

mindate = min(statechgs, key=lambda x: x[0])

for i in range(len(statechgs)):
    try:
        deviceidx = deviceCol.index(statechgs[i][1] + "_" + statechgs[i][2])
    except:
        print(deviceCol)
        print(statechgs[i][1] + "_" + statechgs[i][2])
        raise Exception("Should not happen")
    statechgs[i] = (sec_diff(mindate[0], statechgs[i][0]), deviceidx, statechgs[i][3])

statedict = {}
for item in statechgs:
    timeStamp, deviceidx, value = item
    try:
        curState = statedict[timeStamp]
        curState[deviceidx] = value
    except KeyError:
        curState = initialState(len(deviceCol))
        curState[deviceidx] = value 
        statedict[timeStamp] = curState
    for i in range(1, 10):
        if timeStamp - i > 0 and timeStamp - i not in statedict:
            statedict[timeStamp - i] = initialState(len(deviceCol)) 
        #also initialize the state for 10 seconds prior, since we learn data in a 10 second interval

lastState = initialState(len(deviceCol))
hasInfo = [False] * len(deviceCol) 
#for the device states that is always bot, we filter the columns out later on since we have no info on them
datalist = []

#unfortunately, dictionaries are not sorted, we would need to convert to list so that our data is sorted on
#time stamps.
the_timestamps = sorted(statedict.keys())
for ts in the_timestamps:
    roomState = statedict[ts]
    for i in range(len(roomState)):
        if roomState[i] == 'bot': 
            if hasInfo[i]:
                roomState[i] = lastState[i]
        else:
            hasInfo[i] = True 
        
            
    lastState = roomState 
    datalist.append(roomState)

tag = [False] * len(roomState)
#backfill the bot at the start
for i in range(len(datalist), 0, -1):
    roomState = datalist[i - 1]
    for j in range(len(roomState)):
        if roomState[j] == 'bot': 
            if hasInfo[j] and not tag[j]:
                if lastState[j] == 'siren' or lastState[j] == 'both': #smoke alarm is kinda weird
                    roomState[j] = 'off'
                elif lastState[j] == 'on':
                    roomState[j] = 'off'
                elif lastState[j] == 'off':
                    roomState[j] = 'on'
                elif lastState[j] == 'locked':
                    roomState[j] = 'unlocked'
                elif lastState[j] == 'unlocked':
                    roomState[j] = 'locked'
                tag[j] = True
            elif tag[j]:
                roomState[j] = lastState[j]
    lastState = roomState 

df = pd.DataFrame(datalist, index=the_timestamps, columns = deviceCol)
drop_cols = [deviceCol[i] for i in range(len(deviceCol)) if not hasInfo[i]]
print("dropped columns: {0}".format(drop_cols))
df = df.drop(drop_cols, axis = 1)
df.to_csv("benchmark1.csv")


