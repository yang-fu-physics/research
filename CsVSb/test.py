import os
import math
e = 1.60217733 * 10 ** -19
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
#print(a[~(a==0).all(1)])#去除0行
#b=a[~(a==0).all(1)]
#print(~(b==0).all(0))

def Rtorho(data, abc):
    abc = abc.strip().split(',')
    abcdeal=[]
    for i in abc:
        i = float(i)
        abcdeal.append(i)
    print(abcdeal)
#Rtorho("1,2,3","1,2,3")
print(a**2)
#def function(x, ne, nh, miue, miuh):
    #"""a function of x with four parameters"""
    #result = 0.5*(1-np.sign(x-0.00001))*100/e*((ne*miue+nh*miuh)+(nh*miue+ne*miuh)*miuh*miue*x**2)/((ne*miue+nh*miuh)**2+(nh-ne)**2*(miue*miuh)**2*x**2)+0.5*(1+np.sign(x-0.00001))*100*x/e*((nh*miuh**2-ne*miue**2)+(nh-ne)*(miue*miuh)**2*x**2)/((nh*miuh+ne*miue)**2+(nh-ne)**2*(miue*miuh)**2*x**2)
    #return result
#x=np.linspace(-4,4,100)
#plt.plot(x,function(x,0.5,1,0.3,2))
#plt.show()
#print(a[:, 1:4])