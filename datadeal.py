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

def filetonumpy(file):
    """将带有抬头的文件处理为数据矩阵"""
    with open(file) as filedata:
        datastr = filedata.readlines()
    rows = len(datastr) - 1
    data = numpy.zeros([rows, 2])
    for line in datastr:
        row = datastr.index(line)
        line = line.strip().split(',')
        if line[0] != "Field(T)":
            data[row - 1, 0] = line[0]
            data[row - 1, 1] = line[1]
    return data
def function(x, ne, nh, miue, miuh):
    """双带拟合的函数"""
    result = 0.5 * (1 - np.sign(x)) * 100 / e * (
            (ne * miue + nh * miuh) + (nh * miue + ne * miuh) * miuh * miue * x ** 2) / (
                     (ne * miue + nh * miuh) ** 2 + (nh - ne) ** 2 * (miue * miuh) ** 2 * x ** 2) + 0.5 * (
                     1 + np.sign(x)) * 100 * x / e * (
                     (nh * miuh ** 2 - ne * miue ** 2) + (nh - ne) * (miue * miuh) ** 2 * x ** 2) / (
                     (nh * miuh + ne * miue) ** 2 + (nh - ne) ** 2 * (miue * miuh) ** 2 * x ** 2)
    return result
def fit(Rfile, hallfile, temp):
    """对hall数据文件和电阻数据文件拼接，并使用双带模型拟合，并对每一个温度产生一个电阻图和一个hall图"""
    datahall = filetonumpy(hallfile)
    dataR = filetonumpy(Rfile)
    dataR[:, 0] = -1 * dataR[:, 0]
    data = np.vstack((dataR[::-1, :], datahall))
    # data = np.vstack((datahall,dataR[::-1, :]))
    half = np.shape(dataR)[0]
    plt.figure(figsize=(16, 9))
    plt.subplot(121)
    plt.plot(-1 * dataR[:, 0], dataR[:, 1], "rx", label=temp + "K")
    plt.subplot(122)
    plt.plot(datahall[:, 0], datahall[:, 1], "rx", label=temp + "K")
    try:
        p_est, err_est = curve_fit(function, data[:, 0], data[:, 1])
    except RuntimeError:
        p_est = np.array([0, 0, 0, 0])
        print(temp + "K拟合失败")
    else:
        plt.subplot(121)
        plt.plot(-1 * data[:half - 1, 0], function(data[:half - 1, 0], *p_est), "k--", label=temp + "K-fit")
        plt.legend()
        plt.subplot(122)
        plt.plot(data[half + 1:, 0], function(data[half + 1:, 0], *p_est), "k--", label=temp + "K-fit")
        plt.legend()
        with open("fit.dat", "a") as fitfile:
            fitstr = temp
            for i in p_est:
                fitstr = fitstr + "," + "%e" % i
            fitfile.write(fitstr + "\n")
    plt.show()
    return p_est
def fitonefig(Rfile, hallfile, temp):
    """对hall数据文件和电阻数据文件拼接，并使用双带模型拟合，并对产生一个电阻图和一个hall图"""
    datahall = filetonumpy(hallfile)
    dataR = filetonumpy(Rfile)
    dataR[:, 0] = -1 * dataR[:, 0]
    data = np.vstack((dataR[::-1, :], datahall))
    # data = np.vstack((datahall,dataR[::-1, :]))
    half = np.shape(dataR)[0]
    plt.subplot(121)
    plt.plot(-1 * dataR[:, 0], dataR[:, 1], "x", label=temp + "K")
    plt.legend()
    plt.subplot(122)
    plt.plot(datahall[:, 0], datahall[:, 1], "x", label=temp + "K")
    plt.legend()
    try:
        p_est, err_est = curve_fit(function, data[:, 0], data[:, 1])
    except RuntimeError:
        p_est = np.array([0, 0, 0, 0])
        print(temp + "K拟合失败")
    else:
        plt.subplot(121)
        plt.plot(-1 * data[:half, 0], function(data[:half, 0], *p_est), "r--")
        plt.subplot(122)
        plt.plot(data[half + 1:, 0], function(data[half + 1:, 0], *p_est), "r--")
        with open("fit.dat", "a") as fitfile:
            fitstr = temp
            for i in p_est:
                fitstr = fitstr + "," + "%e" % i
            fitfile.write(fitstr + "\n")
    return p_est
def fitprocess():
    """拟合主流程"""
    fitornot = input("是否进行拟合（y/n），回车默认拟合")
    if fitornot == "y" or fitornot == "":
        fitfile = open("fit.dat", "w+")
        fitfile.write("Temp(K),ne,nh,miue,miuh\n")
        fitfile.close()
        fitfiles = [entry.path for entry in os.scandir(workdir) if entry.name.endswith("K.dat")]
        nums = int(len(fitfiles) / 2)
        num = 0
        arg = np.zeros([nums, 5])
        plt.figure(figsize=(16, 9))
        oneormore = input("一个温度一个拟合图/所有温度合到一个图（y/n),回车默认为y")
        while True:
            line = fitfiles[num].strip().split('K')
            line = line[0].strip().split("-")
            if oneormore == "y" or oneormore == "":
                arg[num, 1:] = fit(fitfiles[num + nums], fitfiles[num], line[1])
            else:
                arg[num, 1:] = fitonefig(fitfiles[num + nums], fitfiles[num], line[1])

            arg[num, 0] = line[1]
            num = num + 1
            if num == nums:
                break
        plt.tight_layout()
        plt.show()

def halltest(name):
    """通过判断初始数据列数，确认是否有hall数据，如果3行则无hall数据"""
    a = open(name, "r+")
    data = a.readlines()
    a.close()
    line = data[0].strip().split(',')  # strip()默认移除字符串首尾空格或换行符
    if len(line) > 3:
        return True
    else:
        return False
def plot(headline, data, rhoorhall):
    """针对处理后的数据画图"""
    j = 0
    for i in headline:
        plt.plot(data[:, 0], data[:, j + 1], label="%.1f" % i + "K")
        j = j + 1
    plt.legend()
    plt.ylabel(rhoorhall)
    plt.xlabel("Field(T)")
def addheadline(headline, oldfile, newfile):
    """在新文件中加入抬头，删除旧文件"""
    with open(oldfile, "r+")as fp:
        tmp_data = fp.read()  # 读取所有文件, 文件太大时不用使用此方法
        fp.seek(0)  # 移动游标
        fpw = open(newfile, "w+")
        fpw.write(headline + "\n" + tmp_data)
        fpw.close()
    os.remove(oldfile)
def savesinglefile(headlines, data, type, abc):
    """将处理后的每个温度的数据储存在单个文件"""
    headlines = headlines.strip().split(',')
    for i in headlines:
        # print(i)
        if i != "Field(T)":
            name = i.strip().split('(')
            np.savetxt("tmp.dat", data[:, [0, headlines.index(i)]], fmt="%.8e", delimiter=",")
            if abc == "1,1,1":
                headline = "Field(T),Rxx(ohm)"
            else:
                headline = ["Field(T),rhoxx(ohm cm)"]
            addheadline(headline, "tmp.dat", type + "-" + name[0] + ".dat")
def Rtorho(data, abc):
    """电阻到电阻率"""
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
    """hall电阻到霍尔电阻率"""
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
    """根据输入的m数据，range范围，lie霍尔或者电阻的列数用于判读是内插的y的正负，interval内插间隔"""
    a = 1
    if m[0, 1] < 0:
        a = -1
    fx = interpolate.interp1d(m[:, 1] / 10000, m[:, 2], kind="linear",
                              fill_value="extrapolate")  # 'linear','zero', 'slinear', 'quadratic', 'cubic'
    internumber = int(range * 10000 / interval + 1)
    x = np.linspace(0, a * range, internumber)
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
def spit(dataT, range, lie, interval):
    """将单个温度的数据进行正负场的分离，并使用inter函数，并做平均"""
    row = 0
    while True:
        if row > 0:
            dataF = dataT[row, 1] * dataT[row - 1, 1]
            if dataF < 0:  # 判断磁场转变点，正负转换
                Fchange = row
                break
        row = row + 1
    j = Fchange

    a1 = dataT[:j, :]
    a2 = dataT[j:, :]
    # print(a1,a2)
    av = (inter(a1, range, lie, interval) + inter(a2, range, lie, interval)) / 2
    return av
def dealdata(name, range, lie, interval, plot):
    """处理数据的主体"""
    dataall = np.zeros([int(range * 10000 / interval + 1), 40])
    plt.subplot(plot)
    a = open(name, "r+")
    data = a.readlines()
    a.close()
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
        row += 1
    # print(Tchange)
    """a=0
    for i in Tchange:
        print(i-a)
        a=i
    print(rows-a)"""
    # print(Fchange)
    i = 0  # 数据以温度未根据进行的分组
    while True:
        if i > 0:  # 以温度为依据分段
            dataT = data2[Tchange[i - 1]:Tchange[i], :]  # dataT为每个温度的分离
            dataspit = spit(dataT, range, lie, interval)
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f" % data2[Tchange[i - 1], 0] + "K")
            if lie == 3:
                plt.ylabel("Ryx(ohm)")
            else:
                plt.ylabel("R(ohm)")
            plt.xlabel("Field(Oe)")
            dataall[:, 0] = dataspit[:, 0]
            dataall[:, i + 1] = dataspit[:, 1]
        else:  # 第一组则取0：。
            if Tchange == []:
                dataT = data2[:, :]
            else:
                dataT = data2[:Tchange[i], :]
            dataspit = spit(dataT, range, lie, interval)
            dataall[:, 0] = dataspit[:, 0]
            dataall[:, i + 1] = dataspit[:, 1]
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f" % data2[0, 0] + "K")
            if lie == 3:
                plt.ylabel("Ryx(ohm)")
            else:
                plt.ylabel("R(ohm)")
            plt.xlabel("Field(Oe)")
            if Tchange == []:
                break
        if i == len(Tchange) - 1:  # 如果是最后一个点，则额外输出一个至最后的数组。并跳出循环
            dataT = data2[Tchange[i]:, :]
            dataspit = spit(dataT, range, lie, interval)
            dataall[:, 0] = dataspit[:, 0]
            dataall[:, i + 2] = dataspit[:, 1]
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f" % data2[Tchange[i], 0] + "K")
            if lie == 3:
                plt.ylabel("Ryx(ohm)")
            else:
                plt.ylabel("R(ohm)")
            plt.xlabel("Field(Oe)")
            break
        # print(i)

        i = i + 1
    plt.legend()
    Tchange.insert(0, int(0))
    return dataall, data2[Tchange, 0]
def deal(file, range, interval, abc):
    """处理数据的多个温度文件的储存"""
    if halltest(file):
        plt.figure(figsize=(16, 9))
        [dataR, headline] = dealdata(file, range, 2, interval, 221)
    else:
        plt.figure(figsize=(8, 9))
        [dataR, headline] = dealdata(file, range, 2, interval, 211)
    dataR = dataR.T[~(dataR == 0).all(0)].T  # 去除0列
    dataR = Rtorho(dataR, abc)
    np.savetxt("dealed-R.dat", dataR, fmt="%.8e", delimiter=",")
    headlinestr = "Field(T)"
    for i in headline:
        if abc == "1,1,1":
            headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm)"
        else:
            headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm cm)"
    addheadline(headlinestr, "dealed-R.dat", "dealed-R-" + abc + ".dat")
    savesinglefile(headlinestr, dataR, "R", abc)
    if halltest(file):
        plt.subplot(223)
    else:
        plt.subplot(212)
    if abc == "1,1,1":
        plot(headline, dataR, "R(ohm)")
    else:
        plot(headline, dataR, "rho(ohm cm)")
    # hall处理
    if halltest(file):
        [datahall, headline] = dealdata(file, range, 3, interval, 222)
        datahall = datahall.T[~(datahall == 0).all(0)].T  # 去除0列
        datahall = Ryxtorhoyx(datahall, abc)
        np.savetxt("dealed-hall.dat", datahall, fmt="%.8e", delimiter=",")
        addheadline(headlinestr, "dealed-hall.dat", "dealed-hall-" + abc + ".dat")
        plt.subplot(224)
        if abc == "1,1,1":
            plot(headline, datahall, "Ryx(ohm)")
        else:
            plot(headline, datahall, "rhoyx(ohm cm)")
        savesinglefile(headlinestr, datahall, "hall", abc)
    plt.tight_layout()
    plt.show()

file = [entry.path for entry in os.scandir(workdir) if entry.name.endswith(".dat")]
if 0==0:
    if len(file) > 1:
        print("dat文件过多")
    else:
        print("文件名是" + file[0])
        range = input("输入内插范围（整数）,最大值即可,回车则默认为14\n")
        if range == "":
            range = 14
        else:
            range = float(range)
        print("插值范围为0-%.1f" % range)
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
        abc = abc.replace("，", ",")
        deal(file[0], range, interval, abc)
fitprocess()
input("by fuyang ヽ(°∀°)ﾉ  \n 按任意键结束")
