# STLTree
STLTree for learning IoT security rules

To generate training\evaluation data, run:
```python3 event.py```
The size of data generated is determined by the number of iterations described in function `genEvent`,
and output file is specified in funciton `EventHandle`.

To run training on the tree model, run:
```python3 training.py```
The data is separated into intervals with length sepcified by the function `trainingset` in the file

To run evaluation on the tree model, run:
```python3 evaluation.py```
You would need to have a trained model ready before running the script.
