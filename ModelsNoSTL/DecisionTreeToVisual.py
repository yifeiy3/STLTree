from sklearn import tree
import numpy as np

def printVariable(keywords, negate):
    '''
        since our variable name is processed for decision tree,
        use regex to convert back what it actually says
        @negate: whether we want to negate the statement for false branch
        @keywords: 4 tuple of (devicename, deviceState, value before, value after)
    '''
    try:
        if keywords[-1][-1:] == '0':
            #device did not change state.
            if negate:
                return "{0}'s {1} state is not {2} or changes from {2}".format(keywords[0], keywords[1], keywords[2])
            return "{0}'s {1} state stays {2}".format(keywords[0], keywords[1], keywords[2])
        else:
            if negate:
                return "{0}'s {1} state did not change from {2} to {3}".format(keywords[0], keywords[1], keywords[2], keywords[3][:-1])
            return "{0}'s {1} state change from {2} to {3}".format(keywords[0], keywords[1], keywords[2], keywords[3][:-1])
    except:
        raise Exception("This should not happen: {0}".format(keywords))

def convertImmediateRule(keywords, negate, tsunit):
    '''
        Generate immediate rule to be used by the runtime monitor.
        @keywords: 3 tuple of (devicename_deviceState, value before, value after)
        
        @return a 6-tuple representing the rule, consist of
        (deviceName, startState, endState, stateChanged?, negate?, tsunit)
    '''
    deviceName, startState, endState = keywords[0], keywords[1], keywords[2]

    return(deviceName, startState, endState[:-1], keywords[-1][-1:] == '1', negate, tsunit)
    

def tree_to_code(decisiontree, feature_names, class_label):
    tree_ = decisiontree.tree_
    feature_name = [
        feature_names[i] if i != tree._tree.TREE_UNDEFINED else "undefined!"
        for i in tree_.feature
    ]
    print("def tree({}):".format(", ".join(feature_names)))

    def recurse(node, depth):
        indent = "  " * depth
        if tree_.feature[node] != tree._tree.TREE_UNDEFINED:
            name = feature_name[node]
            fnme = name.find('_')
            name = name[fnme+1:]
            print(name)
            keywords = name.rsplit('_', 3)
            #print("{}if not {}:".format(indent, name))
            print("{0}if {1}:".format(indent, printVariable(keywords, False)))
            recurse(tree_.children_left[node], depth + 1)
            print("{}else:".format(indent))
            recurse(tree_.children_right[node], depth + 1)
        else:
            pred = np.argmax(tree_.value[node])
            keywords = class_label[pred].rsplit('_', 3)
            print("{}return {}".format(indent, printVariable(keywords, False)))

    recurse(0, 1)

def tree_to_rule(decisiontree, feature_names, class_label, threshold, outfile):
    '''
        @threshold: only rules with confidence exceeding this will be recorded
        @outfile: the file we write the learned rules to
    '''
    tree_ = decisiontree.tree_
    feature_name = [
        feature_names[i] if i != tree._tree.TREE_UNDEFINED else "undefined!"
        for i in tree_.feature
    ]
    ruledict = {}
    def recurse(node, rulestr):
        if tree_.feature[node] != tree._tree.TREE_UNDEFINED:
            name = feature_name[node]
            fnme = name.find('_')
            name = name[fnme+1:]
            keywords = name.rsplit('_', 3)
            if rulestr:
                leftrulestr = rulestr + " and\n\t\t" + printVariable(keywords, False)
                rightrulestr = rulestr + " and\n\t\t" + printVariable(keywords, True)
            else:
                leftrulestr = printVariable(keywords, False)
                rightrulestr = printVariable(keywords, True)

            recurse(tree_.children_left[node], leftrulestr)
            recurse(tree_.children_right[node], rightrulestr)
        else: #leafnode
            pred = np.argmax(tree_.value[node])
            prediction_accuracy = tree_.value[node][0, pred]/np.sum(tree_.value[node])
            keywords = class_label[pred].rsplit('_', 3)
            retstate =  printVariable(keywords, False)
            if prediction_accuracy > threshold:
                rulestr = rulestr + "(error: {0})".format(1 - prediction_accuracy)
                if retstate in ruledict:
                    ruledict[retstate].append(rulestr)
                else:
                    ruledict[retstate] = [rulestr]

    recurse(0, "")
    with open(outfile, "w") as out:
        out.write("Rules: \n")
        for keys in ruledict.keys():
            out.write("{0}, under: \n".format(keys))
            for i in range(len(ruledict[keys])-1):
                the_rulestr = ruledict[keys][i]
                out.write("\t{0}. {1} \n".format(i, the_rulestr))
                out.write("or \n")
            last_rulestr = ruledict[keys][len(ruledict[keys])-1]
            out.write("\t{0}. {1} \n".format(len(ruledict[keys])-1, last_rulestr))
            out.write("\n\n")

def tree_to_rule_store(decisiontree, feature_names, class_label, threshold, tsunit):
    '''
        @param threshold: only rules with confidence exceeding this will be recorded
        @param tsunit:  whether the rule is trained under seconds or minutes as base timestamp unit,
            default is seconds. 
        @return a dictionary mapping device, state value, to the rules
    '''
    tree_ = decisiontree.tree_
    feature_name = [
        feature_names[i] if i != tree._tree.TREE_UNDEFINED else "undefined!"
        for i in tree_.feature
    ]
    ruledict = {}
    def recurse(node, rulestr):
        if tree_.feature[node] != tree._tree.TREE_UNDEFINED:
            name = feature_name[node]
            fnme = name.find('_')
            name = name[fnme+1:]
            keywords = name.rsplit('_', 2)
            leftrulestr = (rulestr + [convertImmediateRule(keywords, False, tsunit)])
            rightrulestr = (rulestr + [convertImmediateRule(keywords, True, tsunit)])

            recurse(tree_.children_left[node], leftrulestr)
            recurse(tree_.children_right[node], rightrulestr)
        else: #leafnode
            pred = np.argmax(tree_.value[node])
            prediction_accuracy = tree_.value[node][0, pred]/np.sum(tree_.value[node])
            keywords = class_label[pred].rsplit('_', 2)

            #6 tuple: (deviceName_state, startState, endState, stateChanged?, negate?, tsunit)
            retstate =  convertImmediateRule(keywords, False, tsunit)
            if prediction_accuracy > threshold:
                # map device to (startState, endState, stateChanged?, associated rule)
                ruletuple = (retstate[1], retstate[2], retstate[3], rulestr)
                if retstate[0] in ruledict:
                    ruledict[retstate[0]].append(ruletuple)
                else:
                    ruledict[retstate[0]] = [ruletuple]
    
    recurse(0, [])
    print(ruledict)
    return ruledict