/**
 *  UnlockDoor
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
    name: "UnlockDoor",
    namespace: "yifeiy3",
    author: "Eric Yang",
    description: "Virtual Switch 1 on implies Door unlock after 2 seconds",
    category: "",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences {
	section("When this switch turns on") {
		input "switchon", "capability.switch", required: true
	}
    section("Unlock this door"){
    	input "thedoor", "capability.lock", required:true
    }
    section("Other switches for reference"){
    	input "otherSwitches", "capability.switch", required: true, multiple: true
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
	subscribe(switchon, "switch.on", appHandler)
}

def appHandler(evt){
	runIn(2, unlockDoor)
}

def unlockDoor(){
	thedoor.unlock()
}
