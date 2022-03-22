import os

import numpy
from scipy import interpolate
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import scipy.stats as st

pi = 3.141592654
h = 6.62607004 * 10 ** -34
e = 1.60217733 * 10 ** -19
me = 9.10938356 * 10 ** -30
Ce = 6.24150974 * 10 ** 18  # 库伦到电子数
workdir = os.getcwd()
workdirdata = workdir + "/data/"
workdirfit = workdir + "/fit/"
workdiroriginal = workdir + "/original/"


def relist(file):
    """对文件重新排序，使得（2）在无（2）后面"""
    list = []
    for i in file:
        i = i[:-4]
        list.append(i)
    list.sort()
    newlist = []
    for i in list:
        i = i + ".dat"
        newlist.append(i)
    print(newlist)
    return newlist


def rename(newfile):
    i = 2
    last = newfile.strip().split('.')[-1]
    newfile = newfile[:-1 * len(last) - 1]
    while True:
        try:
            fpw = open(newfile + "." + last, "r")  # 如果不存在会报错
            fpw.close
            if i == 2:
                newfile = newfile + "(%i)" % i
            else:
                newfile = newfile[:-1 * len(str(i)) - 2] + "(%i)" % i
            i = i + 1
        except IOError:
            break
    newfile = newfile + "." + last
    return newfile


def fitRH(hallfile, temp, low, high):
    """对hall数"""
    datahall = filetonumpy(hallfile)
    # data = np.vstack((datahall,dataR[::-1, :]))
    figRH = plt.figure(figsize=(16, 9))
    plt.plot(datahall[:, 0], datahall[:, 1], "rx", label=temp + "K")
    delet = []
    i = 0
    while True:
        if datahall[i, 0] < low or datahall[i, 0] > high:
            delet = delet + [i]
        i = i + 1
        if i == datahall[:, 0].shape[0]:
            break
    x = np.delete(datahall, delet, axis=0)
    try:
        slope, intercept, r_value, p_value, std_err = st.linregress(x[:, 0], x[:, 1])
    except RuntimeError:
        print(temp + "K拟合失败")
    else:
        plt.plot(datahall[:, 0], slope * datahall[:, 0] + intercept, "k--", label=temp + "K-fit")
        plt.legend()
        slope = slope * 10000  # 单位转换
        ne = 1 / slope * Ce
        with open(workdirfit + "fitRH.dat", "a") as fitfile:
            fitstr = temp
            fitstr = fitstr + "," + "%e" % slope
            fitstr = fitstr + "," + "%e" % intercept
            fitstr = fitstr + "," + "%e" % r_value
            fitstr = fitstr + "," + "%e" % ne
            fitfile.write(fitstr + "\n")
    plt.close()
    figRH.savefig(rename(workdirfit + "RH-" + temp + "K.png"))
    return slope, intercept, r_value


def fitRHprocess():
    fitornot = input("是否进行RH线性拟合（y/n），回车默认不拟合\n")
    if fitornot == "y":
        fitfile = open(workdirfit + "fitRH.dat", "w+")
        fitfile.write("Temp(K),RH(cm^3/C),intercept(ohm cm),Correlation coefficien,Carrier concentration(cm-3)\n")
        fitfile.close()
        fitfiles = relist(
            [entry.path for entry in os.scandir(workdir + "/data") if "K" in entry.name and "hall" in entry.name])
        if fitfiles == []:
            print('没有hall文件')
        else:
            nums = len(fitfiles)
            num = 0
            arg = np.zeros([nums, 4])
            range = input("请输入RH线性拟合范围，示例：4-9，回车默认0-14\n")
            if nums == 0:
                print('没有需要的hall文件')
            else:
                if range == "":
                    low = 0
                    high = 14
                else:
                    range = range.strip().split('-')
                    low = float(range[0])
                    high = float(range[1])
                while True:
                    line = fitfiles[num].strip().split('K')
                    line = line[0].strip().split("-")
                    arg[num, 1:] = fitRH(fitfiles[num], line[1], low, high)
                    arg[num, 0] = line[1]
                    num = num + 1
                    if num == nums:
                        break


def filetonumpy(file):
    """将带有抬头的文件处理为数据矩阵"""
    with open(file) as filedata:
        datastr = filedata.readlines()
    rows = len(datastr) - 1
    data = numpy.zeros([rows, 2])
    k = 0
    while True:
        line = datastr[k].strip().split(',')
        if line[0] != "Field(T)":
            data[k - 1, 0] = line[0]
            data[k - 1, 1] = line[1]
        if k == rows:
            break
        k = k + 1
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
    figtwo = plt.figure(figsize=(16, 9))
    plt.subplot(121)
    plt.plot(-1 * dataR[:, 0], dataR[:, 1], "rx", label=temp + "K")
    plt.legend()
    plt.subplot(122)
    plt.plot(datahall[:, 0], datahall[:, 1], "rx", label=temp + "K")
    plt.legend()
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
        with open(workdirfit + "twobandfit.dat", "a") as fitfile:
            fitstr = temp
            for i in p_est:
                fitstr = fitstr + "," + "%e" % i
            fitfile.write(fitstr + "\n")
    plt.close()
    figtwo.savefig(rename(workdirfit + "twoband-" + temp + "K.png"))
    return p_est


def fitonefig(Rfile, hallfile, temp):
    """对hall数据文件和电阻数据文件拼接，并使用双带模型拟合，并对产生一个电阻图和一个hall图"""
    datahall = filetonumpy(hallfile)
    dataR = filetonumpy(Rfile)
    dataR[:, 0] = -1 * dataR[:, 0]
    data = np.vstack((dataR[::-1, :], datahall))
    # data = np.vstack((datahall,dataR[::-1, :]))
    half = np.shape(dataR)[0]
    plt.figure(figsize=(16, 9))
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
        with open(workdirfit + "twobandfit.dat", "a") as fitfile:
            fitstr = temp
            for i in p_est:
                fitstr = fitstr + "," + "%e" % i
            fitfile.write(fitstr + "\n")
    return p_est


def fitprocess():
    """拟合主流程"""
    fitfiles = [entry.path for entry in os.scandir(workdirdata) if "1,1,1" in entry.name]
    if fitfiles != []:
        print("\n警告：由于dealed-hall-1,1,1.dat存在，认为没有进行ohm至ohm cm的计算，不推荐进行拟合计算\n")
    fitornot = input("是否进行双带线性拟合（y/n），回车默认不拟合，拟合会产生每个温度的拟合图像\n")
    if fitornot == "y":
        fitfile = open(workdirfit + "twobandfit.dat", "w+")
        fitfile.write("Temp(K),ne,nh,miue,miuh\n")
        fitfile.close()
        Rfitfiles = relist(
            [entry.path for entry in os.scandir(workdir + "\data") if "K" in entry.name and "R" in entry.name])
        hallfitfiles = relist(
            [entry.path for entry in os.scandir(workdir + "\data") if "K" in entry.name and "hall" in entry.name])
        Rnums = len(Rfitfiles)
        hallnums = len(hallfitfiles)
        if Rnums != hallnums or Rnums == 0 or hallnums == 0:
            print("data文件见数据文件不正确，一般是由于只有R或者只有hall")
        else:
            num = 0
            arg = np.zeros([Rnums, 5])
            oneormore = ""  # input("一个温度一个拟合图/所有温度合到一个图（y/n),回车默认为y\n")
            try:
                while True:
                    line = Rfitfiles[num].strip().split('K')
                    line = line[0].strip().split("-")
                    if oneormore == "y" or oneormore == "":
                        arg[num, 1:] = fit(Rfitfiles[num], hallfitfiles[num], line[1])
                    else:
                        arg[num, 1:] = fitonefig(Rfitfiles[num], hallfitfiles[num], line[1])
                    num = num + 1
                    if num == Rnums:
                        break
            except Exception as error:
                print(error)


def halltest(name):
    """通过判断初始数据列数，确认有几行数据，3列返回True"""
    a = open(name, "r+")
    data = a.readlines()
    a.close()
    line = data[0].strip().split('\t')  # strip()默认移除字符串首尾空格或换行符
    if len(line) > 3:
        if len(line) > 4:
            print("报警：数据列数不标准")
            input("输入任意键继续或直接关闭窗口退出")
        return True
    else:
        return False


def plot(headline, data, rhoorhall):
    """针对处理后的数据画图"""
    j = 0
    for i in headline:
        plt.plot(data[:, 0], data[:, j + 1], label="%.1f" % i + "K")
        j = j + 1
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize='small')
    plt.ylabel(rhoorhall)
    plt.xlabel("Field(T)")


def addheadline(headline, oldfile, newfile):
    """在新文件中加入抬头，删除旧文件"""
    with open(oldfile, "r+") as fp:
        tmp_data = fp.read()  # 读取所有文件, 文件太大时不用使用此方法
        fp.seek(0)  # 移动游标
        fpw = open(rename(newfile), "w+")
        fpw.write(headline + "\n" + tmp_data)
        fpw.close()
    os.remove(oldfile)


def savesinglefile(headlines, data, type, abc):
    """将处理后的每个温度的数据储存在单个文件"""
    headlinestr = headlines
    headlines = headlines.strip().split(',')
    k = 0
    if type == "R":
        MRall = np.zeros([data.shape[0], len(headlines)])
    while True:
        if headlines[k] != "Field(T)":
            name = headlines[k].strip().split('(')
            if type == "hall":
                np.savetxt("tmp.dat", data[:, [0, k]], fmt="%.8e", delimiter=",")
            else:
                MR = (data[:, k] - data[0, k]) / data[0, k]
                np.savetxt("tmp.dat", np.c_[data[:, [0, k]], MR.T], fmt="%.8e", delimiter=",")
                MRall[:, k] = MR.T
            if abc == "1,1,1":
                if type == "hall":
                    headline = "Field(T),Ryx(ohm)"
                else:
                    headline = "Field(T),Rxx(ohm)" + ",MR"
            else:
                if type == "hall":
                    headline = "Field(T),rhoyx(ohm cm)"
                else:
                    headline = "Field(T),rhoxx(ohm cm)" + ",MR"
            addheadline(headline, "tmp.dat", workdirdata + type + "-" + name[0] + ".dat")
        else:
            if type == "hall":
                pass
            else:
                MRall[:, 0] = data[:, 0]
        if k == len(headlines) - 1:
            break
        k = k + 1
    if type == "R":
        np.savetxt("tmp.dat", MRall, fmt="%.8e", delimiter=",")
        addheadline(headlinestr, "tmp.dat", workdirdata + "MRall.dat")


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


def inter(m, range, type, interval):
    """根据输入的m数据，range范围，lie霍尔或者电阻的列数用于判读是内插的y的正负，interval内插间隔"""
    a = 1
    if m[1, 1] < 0:  # 取第一行第一列判断是否为负值，因为为了0T的内插相同，多取了一行。
        a = -1
    u, indices = np.unique(m[:, 1], return_index=True)
    fx = interpolate.interp1d(m[indices, 1] / 10000, m[indices, 2], kind="linear",
                              fill_value="extrapolate")  # 'linear','zero', 'slinear', 'quadratic', 'cubic'
    internumber = int(range * 10000 / interval + 1)
    x = np.linspace(0, a * range, internumber)
    intery = np.zeros([x.size, 2])
    intery[:, 0] = a * x
    if type == 3:
        intery[:, 1] = a * fx(x)
    else:
        intery[:, 1] = fx(x)
    # plt.plot(m[:,1],m[:,2],intery[:,0],intery[:,1])
    # plt.show()
    # print(intery)
    return intery


def interloop(m, range, type, interval):
    """根据输入的m数据，range范围，lie霍尔或者电阻的列数用于判读是内插的y的正负，interval内插间隔"""
    a = 1
    if m[2, 1] - m[1, 1] < 0:  # 判断升场还是降场
        a = -1
    u, indices = np.unique(m[:, 1], return_index=True)
    fx = interpolate.interp1d(m[indices, 1] / 10000, m[indices, 2], kind="linear",
                              fill_value="extrapolate")  # 'linear','zero', 'slinear', 'quadratic', 'cubic'
    internumber = int(range * 2 * 10000 / interval + 1)
    x = np.linspace(-a * range, a * range, internumber)
    intery = np.zeros([x.size, 2])
    intery[:, 0] = a * x
    if type == 3:
        intery[:, 1] = a * fx(x)
    else:
        intery[:, 1] = fx(x)
    # plt.plot(m[:,1],m[:,2],intery[:,0],intery[:,1])
    # plt.show()
    # print(intery)
    return intery


def spit(dataT, range, type, interval):
    """将单个温度的数据进行正负场的分离，并使用inter函数，并做平均"""
    row = 1
    Fchange = []
    print(dataT)
    while row < dataT.shape[0]:
        if row > 0:
            dataF = dataT[row, 1] * dataT[row - 1, 1]
            if dataF < 0:  # 判断磁场转变点，正负转换
                Fchange.append(row)
        row = row + 1
    if len(Fchange) == 2:
        print("存在loop线，需要注意是否数据有问题,按照loop线处理")
        row = 3
        Fchange2 = []
        while row < dataT.shape[0]:
            if row > 0:
                if np.argmax(dataT[row - 3:row, 1]) == 1 or np.argmax(dataT[row - 3:row, 1]) == 1:
                    Fchange2.append(row - 1)
            row = row + 1
        a1 = dataT[Fchange2[-2]:Fchange[-1] + 1, :]
        a2 = dataT[Fchange2[-1]:, :]
        av = (interloop(a1, range, type, interval) + interloop(a2, range, type, interval)) / 2
    elif len(Fchange) > 2:
        print("单个温度数据三次及以上经过零点，请检查数据")
        print(1 / 0)
    else:
        j = Fchange[0]
        a1 = dataT[:j + 1, :]
        a2 = dataT[j - 1:, :]
        # print(a1,a2)
        av = (inter(a1, range, type, interval) + inter(a2, range, type, interval)) / 2
    return av


def dealdata(name, range, lie, interval, plot, type):
    """处理数据的主体,type=2为R，type=3为hall"""
    dataall = np.zeros([int(range * 10000 / interval + 1), 40])
    plt.subplot(plot)
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
    Fchange = []  # 磁场变化点
    for line in data:
        line = line.strip().split('\t')
        if line[lie] == "--" or line[lie] == "":
            continue
        data2[row, 0] = line[0]
        data2[row, 1] = line[1]
        data2[row, 2] = line[lie]  # 数据转移至data2并处理空格
        # print(data2[row,0])
        if row > 0:
            if abs(data2[row, 0] - data2[row - 1, 0]) > 0.3:  # 判读温度转变点
                Tchange.append(row)
        row += 1
    print(Tchange)
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
            dataspit = spit(dataT, range, type, interval)
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f" % data2[Tchange[i - 1], 0] + "K")
            if type == 3:
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
            dataspit = spit(dataT, range, type, interval)
            dataall[:, 0] = dataspit[:, 0]
            dataall[:, i + 1] = dataspit[:, 1]
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f" % data2[0, 0] + "K")
            if type == 3:
                plt.ylabel("Ryx(ohm)")
            else:
                plt.ylabel("R(ohm)")
            plt.xlabel("Field(Oe)")
            if Tchange == []:
                break
        if i == len(Tchange) - 1:  # 如果是最后一个点，则额外输出一个至最后的数组。并跳出循环
            dataT = data2[Tchange[i]:, :]
            dataspit = spit(dataT, range, type, interval)
            dataall[:, 0] = dataspit[:, 0]
            dataall[:, i + 2] = dataspit[:, 1]
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f" % data2[Tchange[i], 0] + "K")
            if type == 3:
                plt.ylabel("Ryx(ohm)")
            else:
                plt.ylabel("R(ohm)")
            plt.xlabel("Field(Oe)")
            break
        # print(i)

        i = i + 1
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize='small')
    Tchange.insert(0, int(0))
    return dataall, data2[Tchange, 0]


def deal(file, range, interval, abc):
    """处理数据的多个温度文件的储存"""
    if halltest(file):
        fig = plt.figure(figsize=(19.2, 10.8))
        [dataR, headline] = dealdata(file, range, 2, interval, 221, 2)
        type = "R"
    else:
        type = input("检测到只有三列数据，请输入R或者H(hall)，回车默认R\n")
        if type == "R" or type == "":
            type = "R"
            fig = plt.figure(figsize=(9.6, 10.8))
            [dataR, headline] = dealdata(file, range, 2, interval, 211, 2)
    if type == "R":
        dataR = dataR.T[~(dataR == 0).all(0)].T  # 去除0列
        dataR = Rtorho(dataR, abc)
        np.savetxt(workdirdata + "dealed-R.dat", dataR, fmt="%.8e", delimiter=",")
        headlinestr = "Field(T)"
        for i in headline:
            if abc == "1,1,1":
                headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm)"
            else:
                headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm cm)"
        addheadline(headlinestr, workdirdata + "dealed-R.dat", workdirdata + "dealed-R-" + abc + ".dat")
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
    if halltest(file) or type == "H":
        if type == "H":
            fig = plt.figure(figsize=(9.6, 10.8))
            [datahall, headline] = dealdata(file, range, 2, interval, 211, 3)
        else:
            [datahall, headline] = dealdata(file, range, 3, interval, 222, 3)
        datahall = datahall.T[~(datahall == 0).all(0)].T  # 去除0列
        datahall = Ryxtorhoyx(datahall, abc)
        headlinestr = "Field(T)"
        for i in headline:
            if abc == "1,1,1":
                headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm)"
            else:
                headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm cm)"
        np.savetxt(workdirdata + "dealed-hall.dat", datahall, fmt="%.8e", delimiter=",")
        addheadline(headlinestr, workdirdata + "dealed-hall.dat", workdirdata + "dealed-hall-" + abc + ".dat")
        if type == "H":
            plt.subplot(212)
        else:
            plt.subplot(224)
        if abc == "1,1,1":
            plot(headline, datahall, "Ryx(ohm)")
        else:
            plot(headline, datahall, "rhoyx(ohm cm)")
        savesinglefile(headlinestr, datahall, "hall", abc)
    plt.tight_layout()
    plt.show()
    fig.savefig("alldata.png")


if os.path.exists(workdirdata):
    input("已有data文件夹，如需处理原始数据请删除该文件夹重新运行程序。如需进行拟合则任意键继续")
    run = 0
else:
    run = 1
    try:
        os.makedirs(workdir + "/data", 777)
    except Exception as result:
        pass
if run == 1:
    datafile = [entry.path for entry in os.scandir(workdir) if entry.name.endswith(".dat")]
    if len(datafile) > 1:
        print("dat文件过多")
    else:
        print("文件名是" + datafile[0])
        range = input("输入内插范围（一位小数）,最大值即可,回车则默认为14\n")
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
        # deal(datafile[0], range, interval, abc)
        deal(datafile[0], range, interval, abc)

if os.path.exists(workdirfit):
    datafile = [entry.path for entry in os.scandir(workdirfit) if entry.name.endswith(".dat")]
    if datafile != []:
        input("fit文件夹已有数据，如需分析请删除fit文件夹重新运行程序。")
        run = 0
    else:
        run = 1
else:
    os.makedirs(workdir + "/fit", 777)
    run = 1
if run == 1:
    try:
        fitprocess()
        fitRHprocess()
    except Exception as error:
        print(error)
try:
    os.removedirs(workdirfit)
except Exception as error:
    pass
input("by fuyang ヽ(°∀°)ﾉ  \n 按任意键结束")
