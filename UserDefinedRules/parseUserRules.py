import re

def parse(rulestr):
    '''
        Simple parser based on the DONT rule syntax.
    '''
    try:
        req, cond = rulestr.split(' WHEN ')
        conditions = cond.split(' AND ')
        require, timer = parsereq(req)
        conf = []
        for items in conditions:
            condlist = parsecond(items)
            conf.append(condlist)
        return (require, timer), conf
    except:
        print("Parse Error for rule string: " + rulestr)
        return None, []

def parsereq(req):
    '''
        parse the requirement rules according to the format. 

        IS specifies the state value when rule is satisfied.
        AFTER means event dont change state after some seconds.
        If no AFTER is supported in rule, we assume immediate action with after 0 seconds.
        return (deviceMethod, device), (Time duration, Time unit)
    '''
    domethod, device = re.findall(r'(^\w*)\s+(.*)(?= IS )|((?<= IS ).*)', req)
    res = (domethod[0], domethod[1], device[2])
    try:
        dev, rr = res[2].split(' AFTER ')
    except ValueError:
        dev, rr = res[2], ''
        dur, timeMethod = ('0', 'SECONDS')
    else:
        dur, timeMethod = rr.split(' ')
    result = (res[1], dev)
    return result, (dur, timeMethod)
 
def parsecond(conditions):
    '''
        For the conditions, the 'AFTER' key word is meaning less, just need to look out for 'FOR'|'IN LAST'
        return similar result to parsereq

        if no 'IN LAST' is specified, we default to last second (immediate action), we must have a 'FOR'
        for G rule since otherwise it is the same as F rule otherwise.

        IS xxx FOR xxx SECONDS correspond to STL : G
        BECOME xxx IN LAST xxx SECONDS correspond to STL: F
        BECOME xxx IN LAST xxx SECONDS FOR xxx SECONDS corrrespond to STL: FG

        IF continuous variable, we have GREATER THAN xxx
                                        LESS THAN xxx
                                        GREATER EQUAL THAN xxx
                                        LESS EQUAL THAN xxx
    
        return a list of lists. Each item in the list is 'and relation', each item within each item in the list
        is 'or relation'.

        The 'or' relation is a 6 tuple of (deviceState, device, deviceStateCondition), (timeDur, timeUnit, PTSLRule)
    '''
    condlist = conditions.split(' OR ')
    reslist = []
    for cond in condlist:
        if ' IS ' in cond: #we have G rule
            attr, device, value = re.findall(r'(^.*)(?= OF )|((?<= OF ).*)(?= IS )|((?<= IS ).*)', cond)
            res = (attr[0], device[1], value[2])
            try:
                dev, rr = res[2].split(' FOR ')
                res = (res[0], res[1], dev)
            except:
                print("You need to specify duration for G rules, use F rule instead for immediate action")
            else:
                dur, timeMethod = rr.split(' ')
                reslist.append((res, (dur, timeMethod, "G")))
        else:
            attr, device, value = re.findall(r'(^.*)(?= OF )|((?<= OF ).*)(?= BECOME )|((?<= BECOME ).*)', cond)
            res = (attr[0], device[1], value[2])
            stl = 'F'
            dur_g, timeMethod_g = '', ''
            before = res[2]
            if ' FOR ' in res[2]: #we have FG rule
                stl = 'FG'
                before, tail = res[2].split(' FOR ')
                dur_g, timeMethod_g = tail.split(' ')
                dur_g += '+'
                timeMethod_g += '+'
            try:
                dev, rr = before.split(' IN LAST ')
                res = (res[0], res[1], dev)
            except:
                reslist.append((res, ("1", 'SECONDS', 'F')))
            else:
                dur, timeMethod = rr.split(' ')
                reslist.append((res, (dur_g + dur, timeMethod_g + timeMethod, stl)))
    return reslist

if __name__ ==  "__main__":
    rule = 'THE Door_lock STAYS unlock AFTER 3 SECONDS WHEN alarm OF Smoke Alarm IS siren FOR 5 SECONDS'
    reqrule = 'DONT unlock THE Door'
    reqcond = 'alarm OF Smoke Alarm BECOME siren IN LAST 5 SECONDS FOR 2 SECONDS OR alarm OF Smoke Alarm IS siren FOR 5 SECONDS'
    print(parse(rule))