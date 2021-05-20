/**
 *  Change Thermostat Temperature
 *
 *  Copyright 2020 Eric Yang
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the License at:
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 *  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 *  for the specific language governing permissions and limitations under the License.
 *
 */
definition(
    name: "Change Thermostat Temperature",
    namespace: "yifeiy3",
    author: "Eric Yang",
    description: "Change thermostat temperature to use it with data generation, when > 80 for 3 seconds, turn on smoke alarm, when < 65 for 3 seconds, turn off switch 1",
    category: "My Apps",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences {
  section ("Thermostat access") {
    input "thermostats",
        "capability.thermostat",
        title: "Thermostat",
        multiple: false,
        required: true
  }
  section ("Smoke Alarm"){
  	input "smokealarm",
    	"capability.alarm",
        multiple: false,
        required: true
  }
  section ("Light Switch"){
  	input "switches",
    	"capability.switch",
        multiple: false,
        required: true
  }
  section ("Door") {
  	input "door",
    	"capability.lock",
        multiple: false,
        required: true
  }
}

def installed() {
	log.debug "Installed with settings: ${settings}"

	initialize()
}

def updated() {
	log.debug "Updated with settings: ${settings}"
	
	unsubscribe()
    thermostats.setTemperature(78)
	initialize()
}

def initialize() {
	subscribe(app, appTouch)
    state.hightempcounter = 0
    state.lowtempcounter = 0
}

def appTouch(evt){
	def curTemp = thermostats.currentTemperature?: 75
    def randomVal = Math.random()
    if (curTemp < 85 && randomVal > 0.7){
    	curTemp = curTemp + 1
    }
    else if (curTemp > 60 && randomVal < 0.3){
    	curTemp = curTemp - 1
   	}
    if (curTemp >= 80){
    	if(state.hightempcounter < 3){
    		state.hightempcounter = state.hightempcounter + 1
        }
        else if (smokealarm.currentAlarm == 'off'){
        	smokealarm.siren()
       	}
        state.lowtempcounter = 0
    }
    else{
    	if (smokealarm.currentAlarm != 'off'){
        	smokealarm.off()
       	}
        state.hightempcounter = 0
        if(curTemp < 65){
        	if(state.lowtempcounter < 3){
            	state.lowtempcounter = state.lowtempcounter + 1
            }
            else{
            	switches.off()
            }
       	}
        else{
        	state.lowtempcounter = 0
        }
    }
    thermostats.setTemperature(curTemp)
    log.debug("current temp" + curTemp + " high counter" + state.hightempcounter + " low counter" + state.lowtempcounter)
}
// TODO: implement event handlers