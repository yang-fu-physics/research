import os
import math
from scipy import interpolate
import numpy as np
import matplotlib.pyplot as plt

"""
使用origin删除掉废弃数据，最后留下四列（温度，磁场，电阻，霍尔）或者三列（温度，磁场，电阻）。保证每个温度，磁场都会从负值正值，或者正值到负值。
使用origin导出ASCII，使用“，”作为分隔符。不要抬头，即输出文件只有数据。(如图)
将程序和数据文件放入同一文件夹。注意需要只有一个dat文件。

运行程序，初始化大概需要几秒。
输入参数，若直接回车则是使用默认值。
最后会生成一张图，分别为原始的R，Ryx。以及处理后的rho，rhoyx。若输入为三列数据，则只有R。可以按需要保存。若输入的样品尺寸为1，1，1，则rho会自动改为R。
会生成R数据和hall数据。文件名并附有样品尺寸的信息，尺寸的逗号中英文皆可。
生成的数据文件可直接拖入origin中。

有时候会报警，因为内插时遇到了相同的x，和不同的y。python会只保留一个点。对最终结果没有影响。

文件夹中的Sheet1.dat为示例文件。
"""
workdir = os.getcwd()


def halltest(name):
    a = open(name, "r+")
    data = a.readlines()
    line = data[0].strip().split(',')  # strip()默认移除字符串首尾空格或换行符
    if len(line) > 3:
        return True
    else:
        return False


def plot(headline, data, rhoorhall):
    j = 0
    for i in headline:
        plt.plot(data[:, 0] / 10000, data[:, j + 1], label="%.1f" % i + "K")
        j = j + 1
    plt.legend()
    plt.ylabel(rhoorhall)
    plt.xlabel("Filed(T)")


def addheadline(headline, oldfile, newfile):
    with open(oldfile, "r+")as fp:
        tmp_data = fp.read()  # 读取所有文件, 文件太大时不用使用此方法
        fp.seek(0)  # 移动游标
        fpw = open(newfile, "w+")
        fpw.write(headline + "\n" + tmp_data)
        fpw.close
    os.remove(oldfile)


def Rtorho(data, abc):
    abc = abc.replace("，", ",")
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
    abc = abc.replace("，", ",")
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
    internumber = int(range * 10000 / interval + 1)
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
    av = (inter(a1, range, lie, interval) + inter(a2, range, lie, interval)) / 2
    return av


def dealdata(name, range, lie, interval, plot):
    dataall = np.zeros([int(range * 10000 / interval + 1), 40])
    plt.subplot(plot)
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
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f" % data2[Tchange[i - 1], 0] + "K")
            if lie == 3:
                plt.ylabel("Ryx(ohm)")
            else:
                plt.ylabel("R(ohm)")
            plt.xlabel("Filed(T)")
            dataall[:, 0] = dataspit[:, 0]
            dataall[:, i + 1] = dataspit[:, 1]
        else:  # 第一组则取0：。
            if Tchange == []:
                dataT = data2[:, :]
            else:
                dataT = data2[:Tchange[i], :]
            dataspit = spit(dataT, Fchange[0], range, lie, interval)
            dataall[:, 0] = dataspit[:, 0]
            dataall[:, i + 1] = dataspit[:, 1]
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f" % data2[0, 0] + "K")
            if lie == 3:
                plt.ylabel("Ryx(ohm)")
            else:
                plt.ylabel("R(ohm)")
            plt.xlabel("Filed(T)")
            if Tchange == []:
                break
        if i == len(Tchange) - 1:  # 如果是最后一个点，则额外输出一个至最后的数组。并跳出循环
            dataT = data2[Tchange[i]:, :]
            dataspit = spit(dataT, Fchange[i + 1] - Tchange[i], range, lie, interval)
            dataall[:, 0] = dataspit[:, 0]
            dataall[:, i + 2] = dataspit[:, 1]
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f" % data2[Tchange[i], 0] + "K")
            if lie == 3:
                plt.ylabel("Ryx(ohm)")
            else:
                plt.ylabel("R(ohm)")
            plt.xlabel("Filed(T)")
            break
        # print(i)

        i = i + 1
    plt.legend()
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
    print("插值范围为0-%.0d" % range)
    interval = input("输入内插间隔，回车则默认20 Oe\n")
    if interval == "":
        interval = 20
    else:
        interval = float(interval)
    print("内插间隔为%.0d" % interval)
    abc = input("输入长宽高，逗号隔开，单位为cm，回车则皆为1，即输出为电阻\n")
    if abc == "":
        abc = "1,1,1"
    print("长宽高分别为" + abc)
    input("确认参数")

    # R处理
    if halltest(file[0]):
        plt.figure(figsize=(16, 9))
        [dataR, headline] = dealdata(file[0], range, 2, interval, 221)
    else:
        plt.figure(figsize=(8, 9))
        [dataR, headline] = dealdata(file[0], range, 2, interval, 211)
    dataR = dataR.T[~(dataR == 0).all(0)].T  # 去除0列
    dataR = Rtorho(dataR, abc)
    np.savetxt("dealed-R.dat", dataR, fmt="%.8e", delimiter=",")
    headlinestr = "Filed(T)"
    for i in headline:
        if abc.replace("，", ",") == "1,1,1":
            headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm)"
        else:
            headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm cm)"
    addheadline(headlinestr, "dealed-R.dat", "dealed-R-" + abc + ".dat")
    if halltest(file[0]):
        plt.subplot(223)
    else:
        plt.subplot(212)
    if abc.replace("，", ",") == "1,1,1":
        plot(headline, dataR, "R(ohm)")
    else:
        plot(headline, dataR, "rho(ohm cm)")
    # hall处理
    if halltest(file[0]):
        [datahall, headline] = dealdata(file[0], range, 3, interval, 222)
        datahall = datahall.T[~(datahall == 0).all(0)].T  # 去除0列
        datahall = Ryxtorhoyx(datahall, abc)
        np.savetxt("dealed-hall.dat", datahall, fmt="%.8e", delimiter=",")
        addheadline(headlinestr, "dealed-hall.dat", "dealed-hall-" + abc + ".dat")
        plt.subplot(224)
        if abc.replace("，", ",") == "1,1,1":
            plot(headline, datahall, "Ryx(ohm)")
        else:
            plot(headline, datahall, "rhoyx(ohm cm)")

    plt.tight_layout()
    plt.show()
input("by fuyang ヽ(°∀°)ﾉ  \n 按任意键结束")
