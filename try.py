import numpy as np 

a = np.array([[1, 2], [3, 4]])
a = a[np.newaxis, :, :]
b = np.array([[5,6], [7,8]])
b = b[np.newaxis, :, :]

c = [a, b]
print(np.concatenate(c))

