/**
 *  Turn on Smoke Alarm
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
    name: "Turn on Smoke Alarm",
    namespace: "yifeiy3",
    author: "Eric Yang",
    description: "Turn on Smoke Alarm when Light A and B are on",
    category: "",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences {
	section("When these switches are on....") {
		input "switches",
        "capability.switch",
        multiple: true,
        required: true
	}
    section("Turn on ...."){
    	input "smokeAlarm",
        "capability.alarm"
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
}

def apphandler(evt){
    def dosth = true
    def switchlist = switches?: []
    log.debug(switchlist)
    for(switchi in switchlist){
    	log.debug(switchi.currentSwitch)
    	dosth = dosth && !(switchi.currentSwitch == 'off')
    }
    if(dosth)
    {
    	log.debug "Smoke alarm should be rang"
		smokeAlarm.siren()
   	}
}

// TODO: implement event handlers