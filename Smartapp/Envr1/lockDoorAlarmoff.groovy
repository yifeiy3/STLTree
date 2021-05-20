/**
 *  Lock Door and Turn off Smoke Alarm
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
    name: "Lock Door and Turn off Smoke Alarm",
    namespace: "yifeiy3",
    author: "Eric Yang",
    description: "When virtual switch 2 is off, turn of smoke alarm and lock door",
    category: "My Apps",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences {
	section("When this switch is off...") {
		input "switches",
        "capability.switch",
        required: true
	}
    section("Turn off this alarm") {
    	input "smokeAlarm",
        "capability.alarm",
        required: true
    }
    section("And after ... second") {
    	input "timer",
        "number",
        required: true,
        title: "seconds?"
    }
    section("Lock this door"){
    	input "door",
        "capability.lock",
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
	initialize()
}

def initialize() {
	// TODO: subscribe to attributes, devices, locations, etc.
    subscribe(switches, "switch.off", apphandler)
}

def apphandler(evt){
	log.debug "smokealarm got turned off"
    smokeAlarm.off()
    runIn(timer, doorhandler)
}

def doorhandler(evt){
	log.debug "door should be locked now"
    door.lock()
}

// TODO: implement event handlers