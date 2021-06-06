/**
 *  TurnSwitch1on
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
    name: "TurnSwitch1on",
    namespace: "yifeiy3",
    author: "Eric Yang",
    description: "Switch 2 off -->; Switch 1 on after 1 second",
    category: "",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences {
	section("When This switch is off") {
    
		input "switches", "capability.switch", multiple: true
	}
    section("Turn this switch on") {
    
		input "switcheson", "capability.switch", multiple: true
	}
    section ("After..."){
    	input "timer", "number", required: true, title: "seconds?"
    }
}

def installed(){
	subscribe(switches, "switch.off", apphandler)
}

def updated()
{
	unsubscribe()
	installed()
}

def apphandler(evt) {
	log.debug "appTouch: $evt"
	runIn(timer, turnOn)
}

def turnOn(){
	switcheson?.on()
}