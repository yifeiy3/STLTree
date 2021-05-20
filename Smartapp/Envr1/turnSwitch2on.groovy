/**
 *  Turn Virtural Switch 2 on
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
    name: "Turn Virtural Switch 2 on",
    namespace: "yifeiy3",
    author: "Eric Yang",
    description: "If Virtual Switch 1 on, turn virtual switch 2 on after 3 seconds\r\n\r\n",
    category: "My Apps",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences {
	section("Turn on...") {
		input "switches", "capability.switch", multiple: false
	}
    section("When ... is on"){
    	input "switcheson", "capability.switch", multiple: false
    }
    section("After ... seconds"){
    	input "timer", "number", required: true, title: "seconds?"
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
    subscribe(switcheson, "switch.on", apphandler)
}

def apphandler(evt){
	log.debug "the switch should be on after 3 seconds"
    runIn(timer, onhandler)
}

def onhandler(evt){
	log.debug "the switch should be on now"
    switches?.on()
}

// TODO: implement event handlers