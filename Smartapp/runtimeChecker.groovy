import groovy.util.Eval
import java.net.URLEncoder
/**
 *  RuntimeChecker
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
    name: "RuntimeChecker",
    namespace: "yifeiy3",
    author: "Eric Yang",
    description: "Checks the Samsung Smartthings environment after each state change to make sure it is safe.",
    category: "",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences {
	section("Switches") {
		input "switches",
        "capability.switch",
        title: "Switch",
        multiple: true,
        required: false
	}
    section("Door"){
    	input "door",
        "capability.lock",
        title: "locks in the house",
        multiple: true,
        required: false
    }
    section("Smoke Alarm"){
    	input "smokeAlarm",
        "capability.alarm",
        title: "Alarms in the house",
        multiple: true,
        required: false
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
    subscribe(switches, "switch", deviceChangeHandler)
    subscribe(door, "lock", deviceChangeHandler)
    subscribe(smokeAlarm, "alarm", deviceChangeHandler)
}

// TODO: implement event handlers
def deviceChangeHandler(evt){
	def evtDevice = URLEncoder.encode(evt.getDevice().toString(), 'UTF-8')
    def evtValue = evt.value
    def evtState = evt.name
    def evtDate = evt.isoDate
    log.debug "device: ${evtDevice}, state: ${evtState}, value: ${evtValue}, date:${evtDate}"
	def params = [
    	uri: "http://99.155.89.254:10001/?device=$evtDevice&state=$evtState&value=$evtValue&date=$evtDate",
    ]
    try{
        httpGet(params){resp -> 
            log.debug "response data: ${resp.data}"
        } 
    } catch (e){
        log.debug(e)
    }
}