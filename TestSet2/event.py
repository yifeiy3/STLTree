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
Temp_Chg_H,ThermoGT85,LightA_OFF,LightA_ON,LightB_OFF,LightB_ON = 101,102,103,104,105,106
AC_off, AC_on, Window_Open, Window_Closed, LightSensor_GT8 ,LightSensor_LT6, Temp_Chg_L, ThermoLT60 = 107,108,109,110,111,112,113,114
Temp_Chg_N, LightSensor_H, LightSensor_L, LightSensor_N, ThermoNorm, LightNorm, LightA_ON_COND = 115,116,117,118, 119,120, 121
LightB_MAKE_A_ON = 122
#state define 
A_ON,A_OFF,B_ON,B_OFF,AC_ON,AC_OFF,W_OPEN,W_CLOSED = 201,202,203,204,205,206,207,208
T_HIGH, T_LOW, T_NORM, L_HIGH, L_LOW, L_NORM = 209,210,211,212,213,214
event_table = [
   #(In_Event,      In_State,  Out_State, Out_Event,    time_delay) 
    (Temp_Chg_H,       None,   T_HIGH,      ThermoGT85,       0), #if temperture > 85, it sends event
    (Temp_Chg_L,       None,   T_LOW,       ThermoLT60,       0), #if temperture < 85, it sends event
    (Temp_Chg_N,       None,   T_NORM,      ThermoNorm,       0),
    (ThermoNorm,       T_NORM,   None,      None,             0),       #need a default normal event to change temp state.
    (ThermoGT85,       AC_OFF,   None,      Window_Open,      4),
    (ThermoLT60,       T_LOW,    None,      Window_Closed,    3),
    (ThermoLT60,       T_LOW,    None,      AC_on,            3),
    (LightA_OFF,       A_ON,     A_OFF,     None,             0),
    (LightA_ON,        A_OFF,    A_ON,      None,             0),
    (LightB_OFF,       B_ON,     B_OFF,     None,             0),
    (LightB_ON,        B_OFF,    B_ON,      None,              0),
    (LightA_ON_COND,   A_OFF,    None,      LightA_ON,         0),
    # (LightB_MAKE_A_ON,   A_OFF,    A_ON,     None,         0),
    (LightSensor_GT8,  L_HIGH,   None,     LightA_OFF,         0),
    (LightSensor_GT8,  L_HIGH,   None,     LightB_OFF,         0),
    (LightSensor_LT6,  T_HIGH,   L_LOW,      LightB_ON,         0),
    (AC_on,            AC_OFF,   AC_ON,     Window_Closed,     2),
    (AC_off,           AC_ON,    AC_OFF,     None,             0),
    (Window_Closed,    W_OPEN,   W_CLOSED,  None,              0),
    (Window_Open,      W_CLOSED, W_OPEN,    None,              0),
    (LightSensor_H,     None,     L_HIGH,    LightSensor_GT8,  0), 
    (LightSensor_L,    None,     L_LOW,      LightSensor_LT6,  0),
    (LightSensor_N,    None,     L_NORM,     LightNorm,         0),
    (LightNorm,       L_NORM,   None,      None,                0), 
]

def genEvent():
    #devices [Thermostat, LightSensor, LightA, LightB, AC, Window]
    times = 0
    while times < 1000: #how many data points we are generating
        Timer.Run()
        
        rd = random.randint(1,100) #randomly set event happen
        rd2 = random.randint(1,100)

        #thermostat event
        if Event.devices[0].curState() >= 85:
            Event.setEvent(Temp_Chg_H)
        elif Event.devices[0].curState() <= 60:
            Event.setEvent(Temp_Chg_L)
        else:
            Event.setEvent(Temp_Chg_N)
        
        #LightSensor event
        if Event.devices[1].curState() > 8:
            Event.setEvent(LightSensor_H)
        elif Event.devices[1].curState() < 6:
            Event.setEvent(LightSensor_L)
        else:
            Event.setEvent(LightSensor_N)

        #LightA event
        
        if Event.devices[2].curState() == A_ON and rd2 > 80:
            Event.setEvent(LightA_OFF)
        elif Event.devices[2].curState() == A_OFF and Event.devices[1].curState() < 9:
            if rd2 > 99:
                Event.setEvent(LightA_ON)
            else:
                Event.setEvent(LightA_ON_COND)
        
        #Window event
        if Event.devices[5].curState() == W_OPEN:
            if Event.devices[0].curState() < 85 and rd > 98:
                Event.setEvent(Window_Closed)
        elif rd > 0:
            if Event.devices[0].curState() > 80 and Event.devices[4].curState() == AC_OFF:
                Event.setEvent(Window_Open)
        
        #AC Event
        if Event.devices[4].curState() == AC_ON:
            if rd2 > 98 and Event.devices[0].curState() > 60 :
                Event.setEvent(AC_off)
        else:
            if rd2 > 95:
                Event.setEvent(AC_on)

        #LightB Event
        if Event.devices[3].curState() == B_ON:
            if rd > 70 and Event.devices[0].curState() < 85 and Event.devices[1].curState() > 6:
                Event.setEvent(LightB_OFF)
            else:
                Event.devices[3].pastfive.pop(0) #pop last event of light B, should be @ front
                Event.devices[3].pastfive.append(Event.devices[3].pastfive[-1])
        if Event.devices[3].curState() == B_OFF:
            if rd > 95 and Event.devices[1].curState() < 9:
                Event.setEvent(LightB_ON)
            else:
                Event.devices[3].pastfive.pop(0)
                Event.devices[3].pastfive.append(Event.devices[3].pastfive[-1])
            
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
    df = pd.DataFrame(Event.state_tbl,columns=['Thermostat','LightSensor','LightA','LightB','AC','Window'])
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
        if event == Temp_Chg_H or event == ThermoGT85 or event == Temp_Chg_L \
            or event == Temp_Chg_N or event == ThermoLT60:
            return True
        return False
    def isAvailable_Out_state(self,state):
        if self.timer in Timer.timer_queue and self.state < 85 and self.state > 60:
            self.timer.cancelTimer()
        if state == None:
            return True
        if state == T_HIGH or state == T_NORM or state == T_LOW:
            return True
        return False

    def isAvailable_state(self,state):
        if self.state >=85:
            tempState = T_HIGH
        elif self.state <= 60:
            tempState = T_LOW
        else:
            tempState = T_NORM
        if state == None:
            return True
        if tempState == state:
            return True
        return False
    
    def setEvent(self,event):
        if self.state > 100:
            tempchg = [-1,0]
        elif self.state < 45:
            tempchg = [0, 1]
        else:
            tempchg = [-1, 0, 1]
        t = random.choice(tempchg)
        self.state += t
        #Thermostat.scaler = self.state
        Event.setEvent(event)

    
    def setState(self,state):
        pass

    def callback(self,event):
        if self.timer in Timer.timer_queue and self.state < 85 and self.state > 60:
            self.timer.cancelTimer()
        else:
            Event.setEvent(event)
    
class LightSensor(device):
    #scaler = 86
    def __init__(self):
        self.state = 7 #5-10
        print("LightSensor start at temperature: {0}".format(self.state))
        self.timer = Timer()
     
    def isAvailable_event(self,event):
        if event == LightSensor_H or event == LightSensor_GT8 or event == LightSensor_L \
            or event == LightSensor_LT6 or event == LightSensor_N:
            return True
        return False
    def isAvailable_Out_state(self,state):
        if self.timer in Timer.timer_queue and self.state < 9 and self.state > 5:
            self.timer.cancelTimer()
        if state == None:
            return True
        if state == L_HIGH or state == L_NORM or state == L_LOW:
            return True
        return False

    def isAvailable_state(self,state):
        if self.state >= 9:
            tempState = L_HIGH
        elif self.state <= 5:
            tempState = L_LOW
        else:
            tempState = L_NORM
        if state == None:
            return True
        if tempState == state:
            return True
        return False
    
    def setEvent(self,event):
        if self.state > 9:
            tempchg = [-1,0]
        elif self.state < 3:
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
        if self.timer in Timer.timer_queue and self.state < 9 and self.state > 5:
            self.timer.cancelTimer()
        else:
            Event.setEvent(event)

        
        
class Light_A(device):
    def __init__(self):
        self.state = A_OFF
        self.timer = Timer()

    def isAvailable_event(self,event):
        if event == LightA_ON or event == LightA_OFF:
            return True
        return False
    def isAvailable_Out_state(self,state):
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
        self.pastfive = ["off", "off", "off", "off", "off", "off", "off"]

    def isAvailable_event(self,event):
        if event == LightB_ON or event == LightB_OFF or event == LightA_ON_COND:
            return True
        return False
    def isAvailable_Out_state(self,state):
        if state == None:
            return True
        if state == B_OFF:
            self.pastfive.pop(0) 
            self.pastfive.append('off')
            return True
        if state == B_ON:
            self.pastfive.pop(0) 
            self.pastfive.append('on')
            return True
        return False

    def setEvent(self,event):
        if event == LightA_ON and sum([x == 'on' for x in self.pastfive]) < 4:
            return 
        Event.setEvent(event)

    def callback(self,event):
        Event.setEvent(event)
    
class AC(device):
    def __init__(self):
        self.state = AC_OFF
        self.timer = Timer()

    def isAvailable_Out_state(self,state):
        if state == None:
            return True
        if state == AC_ON or state == AC_OFF:
            return True
        return False

    def isAvailable_event(self,event):
        if event == AC_on or event == AC_off:
            return True
        return False
    def callback(self,event):
        Event.setEvent(event)


class Window(device):
    def __init__(self):
        self.state = W_OPEN
        self.timer = Timer()
    def isAvailable_Out_state(self,state):
        if state == None:
            return True
        if state == W_CLOSED or state == W_OPEN:
            return True
        return False
    def isAvailable_event(self,event):
        if event == Window_Closed or event == Window_Open:
            return True
        return False
    def callback(self,event):
        Event.setEvent(event)


class Event:
    event_tbl = []
    state_tbl =[]
    devices = [Thermostat(), LightSensor(),Light_A(),Light_B(),AC(),Window()]
    @staticmethod
    def showState(stb):
        for i,item in enumerate(stb):
            if item == A_ON or item == B_ON or item == AC_ON:
                stb[i] = 'ON'
            if item == A_OFF or item == B_OFF or item == AC_OFF:
                stb[i] = 'OFF'
            if item == W_CLOSED:
                stb[i] = 'Closed'
            if item == W_OPEN:
                stb[i] = 'Open' 
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
