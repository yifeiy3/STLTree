/**
 *  TurnBothSwitchon
 *
 *  Copyright 2021 Eric Yang
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
    name: "TurnBothSwitchon",
    namespace: "yifeiy3",
    author: "Eric Yang",
    description: "Virtual Switch 1 off for 3 seconds ---> Virtual Switch 2 and Virtual Switch 3 on",
    category: "",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences {
	section("Turn on these two switches") {
		input "switcheson", "capability.switch", required: true, multiple:true
	}
    section("When this switch is off") {
		input "switches", "capability.switch", required: true
	}
    section("For this many seconds") {
		input "timer", "number", required: true
	}
}

def installed() {
	log.debug "Installed with settings: ${settings}"

	initialize()
}

def updated() {
	log.debug "Updated with settings: ${settings}"

	unsubscribe()
	initialize()
}

def initialize() {
	subscribe(switches, "switch.off", offhandler)
    subscribe(switches, "switch.on", onhandler)
    state.hasChangedState = false
}

def offhandler(evt){
	state.hasChangedState = false
	runIn(timer, turnOff) //The if another off event happens within the runIn timer, it will
    					  //overwrite the previous runIn timer.
}

def onhandler(evt){
	state.hasChangedState = true
}

def turnOff(){
	if(!state.hasChangedState){
    	switcheson?.on()
    }
}