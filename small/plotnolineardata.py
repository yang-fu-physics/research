import os
import numpy
from scipy import interpolate
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import scipy.stats as st
tuli=0#调整是否在下方二三行的图中给出图例，1不给图例，0给图例，2是全部不给图例
workdir=os.getcwd()
def relist2(file,suffixnum):
    namelist=[]
    for i in file:
        name=i.strip().split('\\')[-1]
        namelist.append(name)
    namelist.sort(key=lambda x:float(x[:suffixnum]))
    newlist=[]
    for i in namelist:
        newlist.append(workdir+"\\"+i)
    return newlist
fileall = [entry.path for entry in os.scandir(workdir) if entry.name.endswith(".dat")]
try:
    fileall=relist2(fileall,-6)#!!!!!!!!!注意这里，容易报错
except Exception as error:
    pass
parameters = {'xtick.labelsize': 15,
              "ytick.labelsize":15,
              "legend.fontsize": 11}
plt.rcParams.update(parameters)

labels={"x":"Source Current","y11":"R1(V)","y12":"R2(V)","y13":"R3(V)","y14":"R4(V)","y21":"R1(Ohm)","y22":"R2(Ohm)","y23":"R3(Ohm)","y24":"R4(Ohm)","y31":"Theta1(degree)","y32":"Theta2(degree)","y33":"Theta3","y34":"Theta4"}
#labels={"x":"Field(Oe)","y11":"R1(V)","y12":"R2(V)","y13":"R3(V)","y14":"R4(V)","y21":"R1(Ohm)","y22":"R2(Ohm)","y23":"R3(Ohm)","y24":"R4(Ohm)","y31":"Theta1","y32":"Theta2","y33":"Theta3","y34":"Theta4"}
#labels={"x":"Temp(K)","y11":"R1(V)","y12":"R2(V)","y13":"R3(V)","y14":"R4(V)","y21":"R1(Ohm)","y22":"R2(Ohm)","y23":"R3(Ohm)","y24":"R4(Ohm)","y31":"Theta1","y32":"Theta2","y33":"Theta3","y34":"Theta4"}

"""
x="Field(Oe)"
y11="R1(V)"
y12="R2(V)"
y13="R3(V)"
y14="R4(V)"
"""

fig=plt.figure(figsize=(19.2, 10.8))
def main(file):
    a = open(file, "r+")
    head = a.readline().strip().split('\t')
    datastr=a.readlines()[0:]
    k=0
    delelt=[]
    for i in datastr:
        if i.strip().split('\t')[0]=="-":
            delelt.append(k)
        k=k+1
    k=0
    while k<len(delelt):
        del datastr[delelt[k]-k]
        k=k+1
    rows = len(datastr)
    data = np.zeros([rows,len(head)])
    row=0
    while row<rows:
        line = datastr[row].strip().split('\t')
        m=0
        while m<len(line):
            data[row, m] = line[m]
            m=m+1
        row=row+1
    k=0
    for i in head:
        m=i.find(labels["x"])
        if m!=-1:
            x=k
        k=k+1
    j=1
    while j<=12:
        #print((24*10+j+1))
        plt.subplot(3, 4, j)
        label=labels["y"+str(((j-1)//4+1)*10+(j-1)%4+1)]
        #print(label)
        try:
            datalie=head.index(label)
        except:
            pass
        else:
            if tuli==1:#调整是否在下方二三行的图中给出图例，1不给图例，0给图例，2是全部不给图例
                if (j-1)//4!=0:
                    plt.plot(data[:, x]*1000, data[:, datalie])
                else:
                    plt.plot(data[:,x]*1000, data[:,datalie], label=file.strip().split('\\')[-1][:-4])
                    plt.legend()
                plt.xlabel(labels["x"]+"(mA)",fontsize=20)
                plt.ylabel(label,fontsize=20)
            elif tuli==0:
                plt.plot(data[:, x]*1000, data[:, datalie], label=file.strip().split('\\')[-1][:-4])
                plt.xlabel(labels["x"]+"(mA)", fontsize=20)
                plt.ylabel(label, fontsize=20)
                plt.legend()
            else:
                plt.plot(data[:, x]*1000, data[:, datalie])
                plt.xlabel(labels["x"]+"(mA)", fontsize=20)
                plt.ylabel(label, fontsize=20)
        j=j+1


for i in fileall:
    main(i)
plt.tight_layout()
plt.show()
fig.savefig(fileall[0] + ".png")