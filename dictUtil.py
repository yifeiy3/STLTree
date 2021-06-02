
def addOrAppendDepth2(d, key1, key2, value):
    '''
        for a dictionary d, we either set d[key1][key2] = [value]
        or we let d[key1][key2].append(value)
    '''
    if key1 in d.keys():
        if key2 in d[key1].keys():
            d[key1][key2].append(value)
        else:
            d[key1][key2] = [value]
    else:
        d[key1] = {key2 : [value]}