import random
import numpy as np
from abc import ABC
import pandas as pd
'''
    Weakness of this data generation: It only shows 1 device change per time stamp, so some immediate
    interactions may appear later than they should be. In real data, the each time stamp would also show
    1 device change, however, the time stamp between the device change will be very small instead of
    incrementing by 1.
'''
#event define
Temp_Chg_H,ThermoGT85,LightA_OFF,LightA_ON,LightB_OFF,LightB_ON = 1,2,3,4,5,6
PersonAway,PersonHome,SmokeSiren,Door_Lock,Door_Open,Smokeoff,Temp_Chg_L = 7,8,9,10,11,12,13
#state define 
A_ON,A_OFF,B_ON,B_OFF,P_Away,P_Home,D_Lock,D_Open,SA_OFF,SA_SIREN = 1,2,3,4,5,6,7,8,9,10
T_High,T_Normal = 11,12
event_table = [
   #(In_Event,      In_State,  Out_State, Out_Event,    time_delay) 
    (Temp_Chg_H,       None,   T_High,    ThermoGT85,       0), #if temperture > 85, it sends event
    (Temp_Chg_L,       None,   T_Normal,  Smokeoff,         0), #if temperture < 85, it sends event
    (ThermoGT85,     T_High,   None,      SmokeSiren,       5),
    (LightA_OFF,     A_ON,     A_OFF,    LightB_ON,       5),
    (LightA_ON,      A_OFF,    A_ON,      None,             0),
    (LightB_OFF,     B_ON,     B_OFF,     None,             0),
    (LightB_ON,      B_OFF,     B_ON,     None,             0),
    (PersonAway,     None  ,   P_Away,    LightB_ON,        0),
    (PersonAway,     None  ,   P_Away,    Door_Lock,        2),
    (PersonHome,     None  ,   P_Home,    None,             0),
    (SmokeSiren,     P_Home,   SA_SIREN,  Door_Open,        0),
    (SmokeSiren,     P_Away,   SA_SIREN,  Door_Lock,        0),
    (Smokeoff,       None,     SA_OFF,    None,             0),
    (Door_Lock,      D_Open,     D_Lock,    None,           0),
    (Door_Open,      D_Lock,     D_Open,    None,           0),    
]

def genEvent():
    times = 0
    while times < 10000: #how many data points we are generating
        Timer.Run()
        
        rd = random.randint(1,100) #randomly set event happen
        #thermostat event
        if Event.devices[0].curState() >= 85:
            Event.setEvent(Temp_Chg_H)
        else:
            Event.setEvent(Temp_Chg_L)
            
        #LightA event
        
        if Event.devices[2].curState() == A_ON and rd > 60:
            Event.setEvent(LightA_OFF)
        elif Event.devices[2].curState() == A_OFF and Event.devices[3].curState() == B_OFF:
            Event.setEvent(LightA_OFF)
        else:
            Event.setEvent(LightA_ON)
        
        #person event
        if Event.devices[5].curState() == P_Away:
            if rd > 90:
                Event.setEvent(PersonHome)
        elif rd > 90:
            Event.setEvent(PersonAway)
        
        #Door Event
        if Event.devices[4].curState() == D_Open and Event.devices[5].curState() == P_Home:
            if rd >90:
                Event.setEvent(Door_Lock)
        # if Event.devices[4].curState() == D_Lock and Event.devices[5].curState() == P_Home:
        #     if rd >90:
        #         Event.setEvent(Door_Lock)
        
        #LightB Event
        if Event.devices[3].curState() == B_ON and Event.devices[5].curState() == P_Home:
            if rd > 70:
                Event.setEvent(LightB_OFF)
        if Event.devices[3].curState() == B_OFF and Event.devices[5].curState() == P_Home:
            if rd > 90:
                Event.setEvent(LightB_ON)
                
        
            
        times +=1
        yield Event.event_tbl
        
def EventHandle():    
    for evs in genEvent():
        while len(evs) > 0:          
            ev = evs.pop(0)
            for ev_tuple in event_table:
                in_ev = ev_tuple[0]
                in_st = ev_tuple[1]
                out_st = ev_tuple[2]
                out_ev = ev_tuple[3]
                delay = ev_tuple[4]
                if ev == in_ev:
                    in_ev_dev = None
                    in_st_dev = None
                    out_st_dev = None
                    out_ev_dev = None
                    for dev in Event.devices:
                        if dev.isAvailable_event(in_ev):
                            in_ev_dev = dev
                        if dev.isAvailable_state(in_st):
                            in_st_dev = dev
                        if dev.isAvailable_Out_state(out_st):
                            out_st_dev = dev
                    if in_ev_dev !=None and in_st_dev != None:
                        if out_st != None:
                            out_st_dev.setState(out_st)
                        if delay > 0:
                            in_ev_dev.timer.registerTimer(delay,out_ev,in_ev_dev.callback)
                        else:
                            if out_ev != None:
                                in_ev_dev.setEvent(out_ev)
                                
        sta_tbl = []
        for de in Event.devices:
            sta_tbl += [de.state]
        Event.showState(sta_tbl)  
    df = pd.DataFrame(Event.state_tbl,columns=['Thermostat','Smoke_Alarm','Light A','Light B','Door','Person'])
    df.to_csv("event.csv")
            
            
class Timer:
    timer_queue = []
    def __init__(self):
        pass
    def registerTimer(self,delay,event,callback):
        if self not in Timer.timer_queue:
            self.delay = delay
            self.event = event
            self.callback = callback
            Timer.timer_queue.append(self)
    def cancelTimer(self):
        for i,t in enumerate(Timer.timer_queue):
            if t == self:
                Timer.timer_queue.pop(i)
                
    @staticmethod
    def Run():
        for i, t in enumerate(Timer.timer_queue):
            Timer.timer_queue[i].delay -= 1
            if Timer.timer_queue[i].delay == 0:
                Event.setTimerEvent(t.callback,t.event)
                Timer.timer_queue.pop(i)
        
class device(ABC):
    def __init__(self):
        self.timer = Timer()
    def callback(self,event):
        pass        
    def set_delay(self,event,delay):
        self.timer.registerTimer(delay,event,self.callback)
    def isAvailable_state(self,state):
        if self.state == state or state == None:
            return True
        return False
    def setState(self,state):
        self.state = state
    def setEvent(self,event):
        Event.setEvent(event)
        
    def curState(self):
        return self.state

        
class Thermostat(device):
    #scaler = 86
    def __init__(self):
        self.state = 84
        print("Thermostat start at temperature: {0}".format(self.state))
        self.timer = Timer()
     
    def isAvailable_event(self,event):
        if event == Temp_Chg_H or event == ThermoGT85 or event == Temp_Chg_L:
            return True
        return False
    def isAvailable_Out_state(self,state):
        if self.timer in Timer.timer_queue and self.state < 85:
            self.timer.cancelTimer()
        if state == None:
            return True
        if state == T_High or state == T_Normal:
            return True
        return False

    def isAvailable_state(self,state):
        if self.state >=85:
            tempState = T_High
        else:
            tempState = T_Normal
        if state == None:
            return True
        if tempState == state:
            return True
        return False
    
    def setEvent(self,event):
        if self.state > 105:
            tempchg = [-1,0]
        elif self.state < 25:
            tempchg = [0, 1]
        else:
            tempchg = [-1, 0, 1]
        t = random.choice(tempchg)
        self.state += t
        #print(self.state)
        #Thermostat.scaler = self.state
        Event.setEvent(event)

    
    def setState(self,state):
        pass
    def callback(self,event):
        if self.timer in Timer.timer_queue and self.state < 85:
            self.timer.cancelTimer()
        else:
            Event.setEvent(event)
    
            

class Smoke_Alarm(device):
    def __init__(self):
        self.state = SA_OFF
        self.timer = Timer()

    def isAvailable_Out_state(self,state):
        if state == None:
            return True
        if state == SA_SIREN or state ==SA_OFF:
            return True
        return False 
    def isAvailable_event(self,event):
        if event == SmokeSiren or event == Smokeoff:
            return True
        return False

        

        
class Light_A(device):
    def __init__(self):
        self.state = A_OFF
        self.timer = Timer()

    def isAvailable_event(self,event):
        if event == LightA_ON or event == LightA_OFF:
            return True
        return False
    def isAvailable_Out_state(self,state):
        if self.timer in Timer.timer_queue and self.state == A_ON:
            self.timer.cancelTimer()
        if state == None:
            return True
        if state == A_OFF or state ==A_ON:
            return True
        return False
    def callback(self,event):
        Event.setEvent(event)
        


class Light_B(device):
    def __init__(self):
        self.state = B_OFF
        self.timer = Timer()

    def isAvailable_event(self,event):
        if event == LightB_ON or event == LightB_OFF:
            return True
        return False
    def isAvailable_Out_state(self,state):
        if state == None:
            return True
        if state == B_OFF or state ==B_ON:
            return True
        return False
    
class Door(device):
    def __init__(self):
        self.state =D_Open
        self.timer = Timer()
    def isAvailable_Out_state(self,state):
        if state == None:
            return True
        if state == D_Open or state ==D_Lock:
            return True
        return False

    def isAvailable_event(self,event):
        if event == Door_Open or event == Door_Lock:
            return True
        return False
    


class Person(device):
    def __init__(self):
        self.state =P_Home
        self.timer = Timer()
    def isAvailable_Out_state(self,state):
        if self.timer in Timer.timer_queue and self.state == P_Home:
            self.timer.cancelTimer()
        if state == None:
            return True
        if state == P_Home or state == P_Away:
            return True
        return False
    def isAvailable_event(self,event):
        if event == PersonAway or event == PersonHome:
            return True
        return False
    def callback(self,event):
        Event.setEvent(event)


class Event:
    event_tbl = []
    state_tbl =[]
    devices = [Thermostat(),Smoke_Alarm(),Light_A(),Light_B(),Door(),Person()]
    @staticmethod
    def showState(stb):
        for i,item in enumerate(stb):
            if item == A_ON or item == B_ON or item ==SA_SIREN:
                stb[i] = 'ON'
            if item == A_OFF or item == B_OFF or item == SA_OFF:
                stb[i] = 'OFF'
            if item == P_Away:
                stb[i] = 'Away'
            if item == P_Home:
                stb[i] = 'Home'
            if item == D_Lock:
                stb[i] = 'LOCKED'
            if item == D_Open:
                stb[i] = 'OPEN'  
            stb[i] = str(stb[i])  
        Event.state_tbl.append(stb)
    @staticmethod
    def setEvent(event):
        Event.event_tbl.append(event)
    @staticmethod
    def setTimerEvent(callback,event):
        if callback != None:
            callback(event)

EventHandle()        
