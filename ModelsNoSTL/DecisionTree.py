import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt
from sklearn.preprocessing import OneHotEncoder
from sklearn import tree
from DecisionTreeToVisual import tree_to_code, tree_to_rule, tree_to_rule_store

import pickle 
import argparse 

def checkint(s, gap):
    try:
        int(s)
        return str(int(s)//gap * gap) #every category separate by a magnitude of gap
    except ValueError:
        return str(s)

def processSingle(s1, s2, gap):
    d1 = checkint(s1, gap)
    d2 = checkint(s2, gap)
    if d1 == d2:
        return d1 + "_" + d2 + "0"
    else:
        return d1 + "_" + d2 + "1"

def aggregate(ar, heads, gap_dict):
    '''
        timeperiod: #seconds
        aggregate data based change of every second

        @param gap_dict: used to separate continuous variables into categories.
    '''
    #data process to list of lists
    record = []
    #zip current state and the state after time period to see change relations.
    for dar in ar:
        temprecord = [[''] * dar.shape[1]] * (dar.shape[0] -1)
        for j in range(0, dar.shape[1]):
            try:
                gap = gap_dict[heads[j]]
            except KeyError:
                gap = 5
            for i in range(0, dar.shape[0] - 1):
                temprecord[i][j] = str(heads[j]) + "_" + processSingle(dar[i, j], dar[i+1, j], gap)
        record += temprecord
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

def gen_train_label(device, col, gap):
    '''
        @param gap: ueed to classify continuous variable, has no effect if not continuous
        label for change state at the next second
    '''

    labels = []
    for cols in col:
        for i in range(0, cols.shape[0]-1):
            labels.append(
                str(device) + "_" + processSingle(cols[i], cols[i + 1], gap)
            )
    return labels

def data_process(header, store_data, gap_dict):
    '''
        @param gap_dict: A dictionary used to define the gaps for classifying continuous variables. Map device to a number

        @return: classdict: A dictionary that maps the label of the tree to all the information needed in training 
        a tree.
    '''
    rec = aggregate(store_data, header, gap_dict)
    class_dict = {}
    for i in range(len(header)):
        try:
            int(store_data[0][1][i]) 
        except ValueError: #if our data not integer valued, we train a tree on it
            train_data = []
            train_label = []
            for rows in range(len(rec)):
                data_row = []
                for cols in range(len(rec[0])):
                    if cols != i:
                        data_row.append(rec[rows][cols])
                train_data.append(data_row)
            label_col = [sd[:, i] for sd in store_data]#note
            try:
                gap = gap_dict[header[i]]
            except KeyError:
                gap = 5 #default to be 5
            train_label = gen_train_label(header[i], label_col, gap)
            y, class_label = genlabel(train_label)
            enc = OneHotEncoder(handle_unknown='ignore')
            trans_res = enc.fit_transform(train_data).toarray()
            print(trans_res)
            class_dict[header[i]] = (trans_res, y, enc, class_label)
    return class_dict

def eval_data_process(header, eval_data, classdict, gap_dict):
    rec = aggregate(eval_data, header, gap_dict)
    eval_class_dict = {}
    for i in range(len(header)):
        try:
            int(eval_data[0][1][i]) 
        except ValueError: #if our data not integer valued, we train a tree on it
            train_data = []
            _trainres, y, enc, classlabel = classdict[header[i]]
            for rows in range(len(rec)):
                data_row = []
                for cols in range(len(rec[0])):
                    if cols != i:
                        data_row.append(rec[rows][cols])
                train_data.append(data_row)
            trans_res = enc.transform(train_data).toarray()
            eval_class_dict[header[i]] = (trans_res, y, enc, classlabel)
    return eval_class_dict

def train_tree(class_dict, max_d, threshold):
    '''
        Train the tree and print out the learned rules
        @param max_d: maximum depth of the tree
        @param threshold: only rules with accuracy more than this will be printed
    '''
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
        tree_to_rule(clf, feature_names, class_label, threshold, "../LearnedModel/{0}.txt".format(data_header))

        #convert our learned rules to a dictionary for runtime monitor, store it in pickle
        convertedRules = tree_to_rule_store(clf, feature_names, class_label, threshold)
        with open("../LearnedModel/treeNoSTLRules/{0}.pkl".format(data_header), 'wb') as outmodel:
            pickle.dump(convertedRules, outmodel, pickle.HIGHEST_PROTOCOL)

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
                if yp > 0.1: #very confident
                    conditions = encoder.inverse_transform([feature_set[i]])
                    outfile.write("Predicted Behavior: " + actual_class + "\n")
                    outfile.write("Actual Behavior: " + class_label[gt[i]] + "\n")
                    outfile.write("Under Conditions: \n")
                    for cond in conditions:
                        outfile.write("\t" + str(cond) + "\n")

if __name__ == '__main__':
    data_csv = ['../Samsung/test.csv', '../Samsung/test1.csv', '../Samsung/test2.csv', '../Samsung/test3.csv',
    '../Samsung/test4.csv', '../Samsung/test5.csv', '../Samsung/test6.csv', '../Samsung/test7.csv']

    parser = argparse.ArgumentParser(description='Train a tree to learn the immediate rules in an IoT environment')
    parser.add_argument('--maxDepth', action = 'store', type=int, dest = 'depth', default = 3,
        help = 'Maximum depth of the learned tree, default is 3')
    parser.add_argument('--threshold', action = 'store', type=float, dest = 'threshold', default = 0.90,
        help='only rules with a higher accuracy in prediction than this will be printed, default 0.90')
    args = parser.parse_args()

    #a dictionary specifiying the gap for separating continuous variable into categories. if none provided for
    #the continuous variable, use 5 as a default.
    gap_dict = {}
    with open("../LearnedModel/treeNoSTLgapDict/gap.pkl", 'wb') as outmodel:
        pickle.dump(gap_dict, outmodel, pickle.HIGHEST_PROTOCOL)
        
    ar = []
    for csv_file in data_csv:
        store_data = pd.read_csv(csv_file, index_col=0)
        ar.append(store_data.to_numpy())
    #do a decision tree for each class? we only care about discrete variables for now
    heads = list(store_data.columns.values)
    cd = data_process(heads, ar, gap_dict) #header, data

    treemodels = train_tree(cd, args.depth, args.threshold)
    eval_csv = ['../Samsung/test.csv']
    evar = []
    for csv_file in eval_csv:
        eval_data = pd.read_csv(csv_file, index_col=0)
        evar.append(eval_data.to_numpy())
    eval_cd = eval_data_process(heads, evar, cd, gap_dict)
    for data_header in cd.keys():
        outfile = "logs/DecisionTreeLog{0}.txt".format(data_header)
        trans_res, y, enc, class_label = eval_cd[data_header]
        treeT = treemodels[data_header]
        evaluate(treeT, trans_res, y, enc, class_label, outfile)
