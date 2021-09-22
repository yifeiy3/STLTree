
CAPABILITY_TO_COMMAND_DICT = {
    'switch': {'on' : 'on', 'off' : 'off'},
    'lock': {'locked': 'lock', 'unlocked': 'unlock'},
    'alarm': {'alarm': 'alarm', 'on': 'on', 'siren': 'siren'},
    'temperature':{}
}

def returnCommand(deviceState, deviceValue):
    valueCommands = {}
    try:
        valueCommands = CAPABILITY_TO_COMMAND_DICT[deviceState]
    except KeyError:
        raise Exception("Undable to find deviceState: {0} in capability dictionary".format(deviceState))
    
    if not valueCommands:
        #we have a continuous variable, by Samsung, the function is setState
        #ex: temperature => setTemperature
        return "set{0}".format(deviceState.capitalize()), deviceValue
    else:
        try:
            return valueCommands[deviceValue], ''
        except KeyError:
            raise Exception("Undable to find value: {0} for device state {1} in capability dictionary".format(deviceValue, deviceState))