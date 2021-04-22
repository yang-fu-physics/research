import os
import math
from scipy import interpolate
import numpy as np
import matplotlib.pyplot as plt

workdir = os.getcwd()


def plot(headline, data, rhoorhall):
    j = 0
    for i in headline:
        plt.plot(data[:, 0] / 10000, data[:, j + 1], label="%.1f" % i + "K")
        j = j + 1
    plt.legend()
    plt.ylabel(rhoorhall)
    plt.xlabel("Filed")
    plt.show()


def addheadline(headline, oldfile, newfile):
    with open(oldfile, "r+")as fp:
        tmp_data = fp.read()  # 读取所有文件, 文件太大时不用使用此方法
        fp.seek(0)  # 移动游标
        fpw = open(newfile, "w+")
        fpw.write(headline + "\n" + tmp_data)
        fpw.close
    os.remove(oldfile)


def Rtorho(data, abc):
    abc = abc.strip().split(',')
    abcdeal = []
    for i in abc:
        i = float(i)
        abcdeal.append(i)
    shape = data.shape
    i = 1
    while True:
        data[:, i] = data[:, i] * abcdeal[1] * abcdeal[2] / abcdeal[0]
        if i == shape[1] - 1:
            break
        i = i + 1
    return data


def Ryxtorhoyx(data, abc):
    abc = abc.strip().split(',')
    abcdeal = []
    for i in abc:
        i = float(i)
        abcdeal.append(i)
    shape = data.shape
    i = 1
    while True:
        data[:, i] = data[:, i] * abcdeal[2]
        if i == shape[1] - 1:
            break
        i = i + 1
    return data


def inter(m, range, lie, interval):
    a = 1
    if m[0, 1] < 0:
        a = -1
    fx = interpolate.interp1d(m[:, 1], m[:, 2], kind="linear",
                              fill_value="extrapolate")  # 'linear','zero', 'slinear', 'quadratic', 'cubic'
    internumber = int(range * 10000 / interval+ 1)
    x = np.linspace(0, a * range * 10000, internumber)
    intery = np.zeros([x.size, 2])
    intery[:, 0] = a * x
    if lie == 3:
        intery[:, 1] = a * fx(x)
    else:
        intery[:, 1] = fx(x)
    # plt.plot(m[:,1],m[:,2],intery[:,0],intery[:,1])
    # plt.show()
    # print(intery)
    return intery


def spit(dataT, j, range, lie, interval):
    a1 = dataT[:j, :]
    a2 = dataT[j:, :]
    av = (inter(a1, range,lie,interval) + inter(a2, range, lie, interval)) / 2
    return av


def dealdata(name, range, lie, interval):
    dataall = np.zeros([int(range*10000/interval+1), 40])
    a = open(name, "r+")
    data = a.readlines()
    rows = len(data)  # 数据总行
    l = 0
    for line in data:
        line = line.strip().split(',')  # strip()默认移除字符串首尾空格或换行符
        if line[lie] == "--":
            l = l + 1
    rows = rows - l  # 确认非空数据行数
    # print(rows)
    data2 = np.zeros((rows, 3))  # 创建数据储存矩阵
    row = 0  # 数据处理的行数
    Tchange = []  # 温度变化点
    Fchange = []  # 磁场变化点
    for line in data:
        line = line.strip().split(',')
        if line[lie] == "--":
            continue
        data2[row, 0] = line[0]
        data2[row, 1] = line[1]
        data2[row, 2] = line[lie]  # 数据转移至data2并处理空格
        # print(data2[row,0])
        if row > 0:
            if abs(data2[row, 0] - data2[row - 1, 0]) > 0.3:  # 判读温度转变点
                Tchange.append(row)
            dataF = data2[row, 1] * data2[row - 1, 1]
            if dataF < 0:  # 判断磁场转变点，正负转换
                Fchange.append(row)
        row += 1
    i = 0  # 数据以温度未根据进行的分组
    # print(Tchange)
    # print(Fchange)
    while True:
        if i > 0:  # 以温度为依据分段
            dataT = data2[Tchange[i - 1]:Tchange[i], :]  # dataT为每个温度的分离
            j = Fchange[i] - Tchange[i]
            dataspit = spit(dataT, j, range, lie, interval)
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f"% data2[Tchange[i - 1], 0] + "K")
        elif i == 0:  # 第一组则取0：。
            dataT = data2[:Tchange[i], :]
            dataspit = spit(dataT, Fchange[0], range, lie, interval)
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f"%data2[0, 0] + "K")
        # print(i)
        dataall[:, 0] = dataspit[:, 0]
        dataall[:, i + 1] = dataspit[:, 1]
        if i == len(Tchange) - 1:  # 如果是最后一个点，则额外输出一个至最后的数组。并跳出循环
            dataT = data2[Tchange[i]:, :]
            dataspit = spit(dataT, Fchange[i + 1] - Tchange[i], range, lie, interval)
            dataall[:, 0] = dataspit[:, 0]
            dataall[:, i + 2] = dataspit[:, 1]
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f"%data2[Tchange[i], 0] + "K")
            break
        i = i + 1
    plt.legend()
    plt.show()
    Tchange.insert(0, int(0))
    return dataall, data2[Tchange, 0]


file = [entry.path for entry in os.scandir(workdir) if entry.name.endswith(".dat")]
if len(file) > 1:
    print("dat文件过多")
else:
    print("文件名是" + file[0])
    range = input("输入内插范围（整数）,最大值即可,回车则默认为14\n")
    if range == "":
        range = 14
    else:
        range = float(range)
    print("插值范围为0-%.0d"%range)
    interval = input("输入内插间隔，回车则默认20 Oe\n")
    if interval == "":
        interval = 20
    else:
        interval = float(interval)
    print("内插间隔为%.0d"%interval)
    abc = input("输入长宽高，英文逗号隔开，单位为cm，回车则皆为1，即输出为电阻\n")
    if abc == "":
        abc = "1,1,1"
    print("长宽高分别为"+abc)
    input("确认参数")
    [dataR, headline] = dealdata(file[0], range, 2, interval)
    dataR = dataR.T[~(dataR == 0).all(0)].T  # 去除0列
    dataR = Rtorho(dataR, abc)
    np.savetxt("dealed-R.dat", dataR, fmt="%.8e", delimiter=",")
    headlinestr = "Filed"
    for i in headline:
        headlinestr = headlinestr + "," + "%.1f"%i + "K"
    addheadline(headlinestr, "dealed-R.dat", "dealed-R-" + abc + ".dat")
    [datahall, headline] = dealdata(file[0], range, 3, interval)
    datahall = datahall.T[~(datahall == 0).all(0)].T  # 去除0列
    datahall = Ryxtorhoyx(datahall, abc)
    np.savetxt("dealed-hall.dat", datahall, fmt="%.8e", delimiter=",")
    addheadline(headlinestr, "dealed-hall.dat", "dealed-hall-" + abc + ".dat")
    plot(headline, dataR, "R")
    plot(headline, datahall, "hall")
input("by fuyang ヽ(°∀°)ﾉ  \n 按任意键结束")
