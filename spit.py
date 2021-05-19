import os
import math

import numpy
from scipy import interpolate
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import leastsq
from scipy.optimize import curve_fit
import math

pi = 3.141592654
h = 6.62607004 * 10 ** -34
e = 1.60217733 * 10 ** -19
me = 9.10938356 * 10 ** -30

workdir = os.getcwd()
def dealdata(name, lie):
    """处理数据的主体"""
    a = open(name, "r+")
    data = a.readlines()
    a.close()
    rows = len(data)  # 数据总行
    l = 0
    for line in data:
        line = line.strip().split('\t')  # strip()默认移除字符串首尾空格或换行符
        if line[lie] == "--":
            l = l + 1
    rows = rows - l  # 确认非空数据行数
    # print(rows)
    data2 = np.zeros((rows, 3))  # 创建数据储存矩阵
    row = 0  # 数据处理的行数
    Tchange = []  # 温度变化点
    for line in data:
        line = line.strip().split('\t')
        if line[lie] == "--" or line[lie] == "":
            continue
        data2[row, 0] = line[0]
        data2[row, 1] = line[1]
        data2[row, 2] = line[lie]  # 数据转移至data2并处理空格
        # print(data2[row,0])
        row += 1
    return data2
def deal(file):
    a = open(file, "r+")
    data = a.readlines()
    a.close()
    line = data[0].strip().split('\t')
    i=2
    while True:
        dataR = dealdata(file, i)
        dataR = dataR.T[~(dataR == 0).all(0)].T  # 去除0列
        dataR = dataR[~(dataR == 0).all(1)]
        np.savetxt("data%.0f.dat"%(i-1), dataR, fmt="%.8e", delimiter=",")
        i=i+1
        if i==len(line):
            break
file = [entry.path for entry in os.scandir(workdir) if entry.name.endswith(".dat")]
if 0==0:
    if len(file) > 1:
        print("dat文件过多")
    else:
        deal(file[0])
