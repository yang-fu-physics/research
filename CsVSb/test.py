import os
import math
from scipy import interpolate
import numpy as np
import matplotlib.pyplot as plt
x=np.linspace(0,10,11)
y=x*x
fx = interpolate.interp1d(x, y, kind="cubic",fill_value="extrapolate")
x1=np.linspace(0,11,100)
y1=fx(x1)*2
k=plt.plot(x,y,x1,y1)
plt.show()

a = np.array([[4, 1, 1, 2, 0, 0],[3, 4, 3, 1, 4, 0],[1, 4, 3, 1, 0, 0],[0, 4, 4, 0, 4, 0],[0, 0, 0, 0, 0, 0]])
print(a[~(a==0).all(1)])#去除0行
b=a[~(a==0).all(1)]
print(~(b==0).all(0))

def Rtorho(data, abc):
    abc = abc.strip().split(',')
    abcdeal=[]
    for i in abc:
        i = float(i)
        abcdeal.append(i)
    print(abcdeal)
Rtorho("1,2,3","1,2,3")