/**
 *  TurnSwitch2off
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
    name: "TurnSwitch2off",
    namespace: "yifeiy3",
    author: "Eric Yang",
    description: "Switch3 on -->; Switch 2 off after 2 seconds",
    category: "",
    iconUrl: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience.png",
    iconX2Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png",
    iconX3Url: "https://s3.amazonaws.com/smartapp-icons/Convenience/Cat-Convenience@2x.png")


preferences {
	section("When this gets turned on...") {
		input "switches", "capability.switch", multiple: true
	}
    section("Turn off..."){
    	input "switchesoff", "capability.switch", multiple: true
    }
    section("After..."){
    	input "timer", "number", required: true, title: "seconds?"
    }
}

def installed()
{
	subscribe(switches, "switch.on", timedExec)
}

def updated()
{
	unsubscribe()
    subscribe(switches, "switch.on", timedExec)
}

def turnoff(){
	switchesoff?.off()
}

def timedExec(evt){
	log.debug "a timed modification of this app"
    runIn(timer, turnoff)
}