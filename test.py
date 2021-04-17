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