/**
 *  Unlock door when light on and smoke alarm siren
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
    name: "Unlock door when light on and smoke alarm siren",
    namespace: "yifeiy3",
    author: "Eric Yang",
    description: "Smoke Alarm Siren and Virtual Switch 1 on ----&gt; Door unlock after 2 seconds ",
    category: "",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences {
	section("Door") {
		input "door",
        "capability.lock",
        required: true,
        multiple: false
	}
    section("Smoke Alarm"){
    	input "smokealarm",
        "capability.alarm",
        required: true,
        multiple: false
   }
   section("Switch"){
   		input "switches",
        "capability.switch",
        required: true,
        multiple: false
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
	// TODO: subscribe to attributes, devices, locations, etc.
    subscribe(switches, "switch.on", apphandler)
    subscribe(smokealarm, "alarm.siren", apphandler)
}

def apphandler(evt){
	if (switches.currentSwitch == 'on' && smokealarm.currentAlarm != 'off'){
    	door.unlock()
    }
}
// TODO: implement event handlers