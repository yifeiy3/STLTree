import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt
from sklearn.preprocessing import OneHotEncoder
from sklearn import tree
from DecisionTreeToVisual import tree_to_code, tree_to_rule

def checkint(s):
    try:
        int(s)
        return str(int(s)//5 * 5) #every category separate by a magnitude of 5
    except ValueError:
        return str(s)

def processSingle(s1, s2):
    d1 = checkint(s1)
    d2 = checkint(s2)
    if d1 == d2:
        return d1 + "_" + d2 + "0"
    else:
        return d1 + "_" + d2 + "1"

def processTimed(s1):
    '''
        for example, if on for 5 seconds, return "on_5", if differ, return "different_5"
    '''
    timeframe = str(len(s1))
    state = ''
    for entries in s1:
        e1 = checkint(entries)
        if not state:
            state = e1
        else:
            if e1 != state:
                state = 'different'
                break
    return state + "_" + timeframe


def aggregate(ar, heads, timeperiod, maxtime):
    '''
        timeperiod: #seconds
        aggregate data based on the time period, every 1 second/5second etc
    '''
    #data process to list of lists
    record = []
    #zip current state and the state after time period to see change relations.
    if timeperiod > 1:
        for i in range(0, ar.shape[0] - maxtime):
            record.append(
                [str(heads[j]) + "_" + processTimed(ar[i:i+timeperiod, j]) for j in range(ar.shape[1])])
    else:
        for i in range(0, ar.shape[0] - maxtime):
            record.append(
                [str(heads[j]) + "_" + processSingle(ar[i, j], ar[i+1, j]) for j in range(ar.shape[1])])
    return record

def genlabel(col):
    '''
        col is a list of label classes, convert them to int
    '''
    total_class = list(set(col))
    res_label = []
    for items in col:
        for j in range(len(total_class)):
            if items == total_class[j]:
                res_label.append(j)
                break
    return res_label, total_class

def gen_train_label(device, col, label_time, maxtime):
    '''
        label for change state to do something after x seconds
        maxtime determines the number of labels we can generate
        to make sure training data and label are of same shape
    '''

    labels = []
    for i in range(0, col.shape[0]-maxtime):
        labels.append(
            str(device) + "_" + processSingle(col[i], col[i + label_time])
        )
    return labels

def data_process(header, store_data, timeperiod, label_time):
    '''
        timeperiod: check do something after something been at a state for some time
        label_time: check do something after some time
    '''
    maxtime = max(timeperiod, label_time)
    rec = aggregate(store_data, header, timeperiod, maxtime)
    class_dict = {}
    for i in range(len(header)):
        try:
            int(ar[1][i])
        except ValueError: #if our data not integer valued, we train a tree on it
            train_data = []
            train_label = []
            for rows in range(len(rec)):
                data_row = []
                for cols in range(len(rec[0])):
                    if cols != i:
                        data_row.append(rec[rows][cols])
                train_data.append(data_row)
            label_col = store_data[:, i]
            train_label = gen_train_label(header[i], label_col, label_time, maxtime)
            y, class_label = genlabel(train_label)
            enc = OneHotEncoder(handle_unknown='ignore')
            trans_res = enc.fit_transform(train_data).toarray()
            class_dict[header[i]] = (trans_res, y, enc, class_label)
    return class_dict

def train_tree(class_dict, max_d):
    tree_dict = {}
    for data_header in class_dict.keys():
        trans_res, y, enc, class_label = class_dict[data_header]
        clf = tree.DecisionTreeClassifier(max_depth=max_d)
        clf = clf.fit(trans_res, y)
        tree_dict[data_header] = clf
        feature_names = enc.get_feature_names()
        tree.plot_tree(clf, feature_names = feature_names, class_names= class_label)
        plt.show()
        tree_to_code(clf, feature_names, class_label)
        tree_to_rule(clf, feature_names, class_label, 0.85, "../LearnedModel/{0}.txt".format(data_header))
    return tree_dict

def evaluate(treemodel, feature_set, gt, encoder, class_label, writefile):
    with open(writefile, "w") as outfile:
        yhat = treemodel.predict_proba(feature_set)
        for i in range(len(yhat)):
            yi = yhat[i]
            yp = 0 #predicted confidence percentage
            yc = '' #predicted class
            for j in range(len(yi)):
                if yi[j] > yp:
                    yp = yi[j]
                    yc = j
            if yc != gt[i]:
                actual_class = class_label[yc]
                if yp > 0.9: #very confident
                    conditions = encoder.inverse_transform([feature_set[i]])
                    outfile.write("Predicted Behavior: " + actual_class + "\n")
                    outfile.write("Actual Behavior: " + class_label[gt[i]] + "\n")
                    outfile.write("Under Conditions: \n")
                    for cond in conditions:
                        outfile.write("\t" + str(cond) + "\n")


store_data = pd.read_csv("../Samsung/event.csv", index_col=0)
ar = store_data.to_numpy()
#do a decision tree for each class? we only care about discrete variables for now
heads = list(store_data.columns.values)
cd = data_process(heads, ar, 1, 1) #header, data, timeperiod, label_time
treemodels = train_tree(cd, 3)

eval_data = pd.read_csv("../Samsung/validate.csv", index_col=0)
evar = store_data.to_numpy()
evhd = list(eval_data.columns.values)
eval_cd = data_process(heads, ar, 1, 1)
outfile = "DecisionTreeLog.txt"
for data_header in eval_cd.keys():
    trans_res, y, enc, class_label = eval_cd[data_header]
    treeT = treemodels[data_header]
    evaluate(treeT, trans_res, y, enc, class_label, outfile)
