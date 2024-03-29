# STLTree
STLTree for learning IoT security rules. A detailed description about our current implementation and how
to run the model can be found under `Documentation.pdf`

## Data Generation
To generate training\evaluation data, run:
```
  python3 event.py
```
under directory `TestSet1` and `TestSet2`. The environment for data generation in each directory is defined in `DataEnvironment.text`.

The size of data generated is determined by the number of iterations described in function `genEvent`, and output file is specified 
in funciton `EventHandle`.

To generate data with Samsung Smartthings devices, you would need to
form a Smart environment on Samsung hub: https://graph.api.smartthings.com/ide/apps

The device data can be either directly simulated, or generated with an automated framework with Selenium. The Smartapps used for the 
three data generation can be found in `Smartapp/Envr1`,`Smartapp/Envr2`, and `Smartapp/Envr3`.

To obtain the simulated data, run:
```
  python3 getDeviceInfo.py
```
under `Samsung` directory. You would also need to have `Smartapp/monitor.groovy` installed in your Samsung hub, and have APIToken
and APIEndpoint corresponding to what is installed in your environment in `getDeviceInfo.py`.

## Running Decision Tree Models

### STLTree
To run training on the tree model, run:
```
  python3 training.py
```
The data is separated into intervals with length sepcified by the function `trainingset` in the file.

Available Command Line Flags:
- `--interval=n`      Number of timestamps per training data interval, default 10
- `--offset=m `       Number of timestamps we skip between training data intervals, default 2
- `--Tmax=t`         Temperature for Simulated Annealing, default 20000
- `--Steps=s`         Steps for Simulated Annealing, default 20000
- `--maxDepth=d, --fracSame=f, --minObj=n`      Tree Stop condition, we stop splitting when we reached depth
                    d, or accruacy for current node reach f, or there are less than n objects in the node

We learn a pruned tree and unpruned tree for the rules, which the printed version can be found under 
`LearnedModel/Treepostprunemodel` and `LearnedModel/Treemodel` correspondingly with a output format 
`{deviceName}_{stateName}.pkl`.

To have a readable format of the learned rules, run 
```
  python3 printrule.py 
``` 
after training model, the printed rules will be under `LearnedModel/PrintedRules` with the same format.

Available Command Line Flags:
- `--threshold=t`   Only rules with error less than t will be printed, default 0.1

To run evaluation on the tree model, run:
```
  python3 evaluation.py
```
You would need to have a trained model ready before running the script. The output will be found in `EvalReport`

Available Command Line Flags:
- `--threshold=t`   Only rules with error less than t will be printed, default 0.1
- `--interval=n --offset=m` Data handling parameters, should be the same as given for training.

### TreeNoSTL
To run training on the tree model without learning STLrules, run
```
  python3 ModelsNoSTL/DecisionTree.py
```
and run
```
  python3 ModelsNoSTL/DecisionTreeVisualization.py

```
To visualize the learned rules. The learned rules and visualization can be found under `LearnedModel`
with format `{deviceName}_{stateName}.txt` and `{deviceName}_{stateName}.pkl` correspondingly.

## Runtime checking of Samsung Environment
To run the checker, you would need to first SSH into a server with a public address, and run
```
  python3 runtime.py
```
with specifying your server address and port in the file. You would also need to specify the APIToken
and APIEndpoint of `Smartapp/monitor.groovy` in your runtime.py file.

Available Command Line Flags:
- `--important=True`: Set the monitor to only check important device changes
- `--do=False`: Set the monitor to ignore checking Do rules, so it will not automatically change device to the rule specified state
- `--threshold=t` Only rules with error less than t will be used, default 0.1
- `--interval=i` Number of timestamps per data interval, should be the same as given for training

Finally, you would want to have `Smartapp/runtimeMonitor.groovy` installed in your environment with the
devices you want to monitor. The checker also supports monitoring user defined rules which you can provide in the top of 
`runtime.py`, a detailed decscription can be found in `Documentation.pdf`.
