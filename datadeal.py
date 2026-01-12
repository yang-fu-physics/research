import os
import pandas as pd
import numpy
from scipy import interpolate
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import scipy.stats as st
loop=False
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
    #print(newlist)
    return newlist

def relist2(file,x1,x2):
    namelist=[]
    elselist=[]
    for i in file:
        name=i.strip().split('\\')[-1]
        if len(name.strip().split('('))==1:
            namelist.append(name)
        else:
            elselist.append(name)
        #print(name[x1:x2])
    namelist.sort(key=lambda x:float(x[x1:x2]))
    elselist.sort(key=lambda x:float(x[x1:x2-3]))
    newlist=[]
    for i in namelist:
        newlist.append(workdirdata+"\\"+i)
    for i in elselist:
        newlist.append(workdirdata + "\\" + i)
    return newlist

def rename(newfile):
    i = 2
    last = newfile.strip().split('.')[-1]
    newfile = newfile[:-1 * len(last) - 1]
    while True:
        try:
            fpw = open(newfile + "." + last, "r")  # 如果不存在会报错
            fpw.close()
            if i == 2:
                newfile = newfile + "(%i)" % i
            else:
                newfile = newfile[:-1 * len(str(i)) - 2] + "(%i)" % i
            i = i + 1
        except IOError:
            break
    newfile = newfile + "." + last
    return newfile


def fitRH(hallfile, Rfile, temp, low, high):
    """对hall数"""
    datahall = filetonumpy(hallfile)
    try:
        dataR=filetonumpy(Rfile)
    except:
        onlyhall=True
        rho0 = 1
        print("没有发现电阻数据，将不输出迁移率")
    else:
        onlyhall=False
        rho0 = dataR[0, 1]
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
        n = 1 / slope * Ce
        #dof=datahall.shape[0]-2
        #t=st.t.ppf(1-0.05/2, dof)*std_err#本来想计算置信区间也就是参数误差，但是发现不太对，这样对于所有参数之心区间是相同的，就注释掉了。
        miu = slope/rho0
        with open(workdirfit + "fitRH.dat", "a") as fitfile:
            fitstr = temp
            fitstr = fitstr + "," + "%e" % slope
            fitstr = fitstr + "," + "%e" % intercept
            fitstr = fitstr + "," + "%e" % r_value
            fitstr = fitstr + "," + "%e" % n
            #fitstr = fitstr + "," + "%e" % t
            if onlyhall==False:
                fitstr = fitstr + "," + "%e" % miu
            else:
                fitstr = fitstr + ",--"
            fitfile.write(fitstr + "\n")
    plt.close()
    figRH.savefig(rename(workdirfit + "RH-" + temp + "K.png"))
    return slope, intercept, r_value#, std_err


def fitRHprocess():
    fitornot = input("是否进行RH线性拟合（y/n），回车默认不拟合\n")
    if fitornot == "y":
        fitfile = open(workdirfit + "fitRH.dat", "w+")
        fitfile.write("Temp(K),RH(cm^3/C),intercept(ohm cm),Correlation coefficien,Carrier concentration(cm^-3),carrier mobility(cm^2/(s*V))\n")
        fitfile.close()
        fitfiles = relist(
            [entry.path for entry in os.scandir(workdir + "/data") if "K" in entry.name and "hall" in entry.name])
        fitfiles=relist2(fitfiles,5,-5)
        fitfilesR = relist(
            [entry.path for entry in os.scandir(workdir + "/data") if "K" in entry.name and "R" in entry.name])
        fitfilesR = relist2(fitfilesR, 2, -5)
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
                    line = fitfiles[num].strip().split("-")
                    line = line[-1].strip().split('K')
                    if fitfilesR == []:
                        arg[num, 1:] = fitRH(fitfiles[num],"", line[0], low, high)
                    else:
                        arg[num, 1:] = fitRH(fitfiles[num], fitfilesR[num], line[0], low, high)
                    arg[num, 0] = line[0]
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
"""
def functionR(x, ne, nh, miue, miuh):
    result=100 / e * (
            (ne * miue + nh * miuh) + (nh * miue + ne * miuh) * miuh * miue * x ** 2) / (
                     (ne * miue + nh * miuh) ** 2 + (nh - ne) ** 2 * (miue * miuh) ** 2 * x ** 2)
    return result
def functionhall(x, ne, nh, miue, miuh):
    result=100 / e * (
            (ne * miue + nh * miuh) + (nh * miue + ne * miuh) * miuh * miue * x ** 2) / (
                     (ne * miue + nh * miuh) ** 2 + (nh - ne) ** 2 * (miue * miuh) ** 2 * x ** 2)
    return result
def functionnew(x, ne, nh, miue, miuh):
    result=np.concatenate((functionR(x, ne, nh, miue, miuh), functionhall(x, ne, nh, miue, miuh)))
    return result
def fitnew(Rfile, hallfile, temp):
    #对hall数据文件和电阻数据文件拼接，并使用双带模型拟合，并对每一个温度产生一个电阻图和一个hall图
    datahall = filetonumpy(hallfile)
    dataR = filetonumpy(Rfile)
    xdata = np.concatenate((dataR[:,0], datahall[:,0]))
    ydata = np.concatenate((dataR[:,1], datahall[:,1]))
    # data = np.vstack((datahall,dataR[::-1, :]))
    figtwo = plt.figure(figsize=(16, 9))
    plt.subplot(121)
    plt.plot(dataR[:, 0], dataR[:, 1], "rx", label=temp + "K")
    plt.legend()
    plt.subplot(122)
    plt.plot(datahall[:, 0], datahall[:, 1], "rx", label=temp + "K")
    plt.legend()

    def weighted_func(x, ne, nh, miue, miuh):
        weights = np.ones(np.shape(x))
        weights[4] = 1
        return functionnew(x, ne, nh, miue, miuh) * weights
    try:
        p_est, err_est = curve_fit(weighted_func, xdata, ydata)
        #p_est, err_est = curve_fit(function, data[:, 0], data[:, 1])#如果这里跑飞，则是需要添加初值列表，在括号中的最后即可。
    except RuntimeError:
        p_est = np.array([0, 0, 0, 0])
        print(temp + "K拟合失败")
    else:
        plt.subplot(121)
        plt.plot(dataR[:, 0], functionR(dataR[:, 0], *p_est), "k--", label=temp + "K-fit")
        plt.legend()
        plt.subplot(122)
        plt.plot(datahall[:, 0], functionhall(datahall[:, 0], *p_est), "k--", label=temp + "K-fit")
        plt.legend()
        with open(workdirfit + "twobandfit.dat", "a") as fitfile:
            fitstr = temp
            p_est[0]=p_est[0]/1000000
            p_est[1] = p_est[1] / 1000000
            p_est[2] = p_est[2] * 10000
            p_est[3] = p_est[3] * 10000
            for i in p_est:
                fitstr = fitstr + "," + "%e" % i
            fitfile.write(fitstr + "\n")
    plt.close()
    figtwo.savefig(rename(workdirfit + "twoband-" + temp + "K.png"))
    return p_est
    """
def lasthalfarray(originarray):
    num_rows = originarray.shape[0]  # 获取行数
    mid_row = num_rows // 2
    output=originarray[mid_row:,:]
    return output
def fit(Rfile, hallfile, temp):
    """对hall数据文件和电阻数据文件拼接，并使用双带模型拟合，并对每一个温度产生一个电阻图和一个hall图"""
    datahall = lasthalfarray(filetonumpy(hallfile))
    dataR = lasthalfarray(filetonumpy(Rfile))
    #xdata = np.concatenate((dataR[:,0], datahall[:,0]))
    #ydata = np.concatenate((dataR[:,1], datahall[:,1]))
    dataR[:, 0] = -1 * dataR[:, 0]
    data = np.vstack((dataR[::-1, :], datahall))#可能有问题注意后续修改
    # data = np.vstack((datahall,dataR[::-1, :]))
    half = np.shape(dataR)[0]
    figtwo = plt.figure(figsize=(16, 9))
    plt.subplot(121)
    plt.plot(-1 * dataR[:, 0], dataR[:, 1], "rx", label=temp + "K")
    plt.legend()
    plt.subplot(122)
    plt.plot(datahall[:, 0], datahall[:, 1], "rx", label=temp + "K")
    plt.legend()
    #weights = np.ones(data[:, 0])
    #weights[4] = 15
    #def weighted_func(x, ne, nh, miue, miuh):
        #return function(x, ne, nh, miue, miuh) * weights
    try:
        #p_est, err_est = curve_fit(weighted_func, xdata, ydata)
        p_est, err_est = curve_fit(function, data[:, 0], data[:, 1], [1E26,1E26,1,1],maxfev=1500)#如果这里跑飞，则是需要添加初值列表，在括号中的最后即可。
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
        perr = np.sqrt(np.diag(err_est))
        t_value = 2.0  # 使用 95% 的置信度
        ci = t_value * perr
        with open(workdirfit + "twobandfit.dat", "a") as fitfile:
            fitstr = temp
            p_est[0]=p_est[0]/1000000
            p_est[1] = p_est[1] / 1000000
            p_est[2] = p_est[2] * 10000
            p_est[3] = p_est[3] * 10000
            for i in p_est:
                fitstr = fitstr + "," + "%e" % i
            for i in ci:
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
        fitfile.write("Temp(K),ne(cm^-3),nh(cm^-3),miue(cm^2/(s*V)),miuh(cm^2/(s*V)),ne Confidence intervals(cm^-3),nh Confidence intervals(cm^-3),miue Confidence intervals(cm^2/(s*V)),miuh Confidence intervals(cm^2/(s*V))\n")
        fitfile.close()
        Rfitfiles = relist(
            [entry.path for entry in os.scandir(workdir + "\\data") if "K" in entry.name and "R" in entry.name])
        Rfitfiles =relist2(Rfitfiles,2,-5)
        hallfitfiles = relist(
            [entry.path for entry in os.scandir(workdir + "\\data") if "K" in entry.name and "hall" in entry.name])
        hallfitfiles = relist2(hallfitfiles, 5, -5)
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
                    line = Rfitfiles[num].strip().split("-")
                    line = line[-1].strip().split('K')
                    if oneormore == "y" or oneormore == "":
                        arg[num, 1:] = fit(Rfitfiles[num], hallfitfiles[num], line[0])
                    else:
                        arg[num, 1:] = fitonefig(Rfitfiles[num], hallfitfiles[num], line[0])
                    num = num + 1
                    if num == Rnums:
                        break
            except Exception as error:
                print(error)


def halltest(name):
    """通过判断初始数据列数，确认有几行数据，3列返回True"""
    df = pd.read_csv('Sheet1.dat',sep="\t",header=None,na_values='--')
    row_count, column_count = df.shape
    if column_count > 3:
        if column_count > 4:
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


def savesinglefile(headlines, data, type, abc, mrhead):
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
                MR = (data[:, k] - data[data.shape[0]//2, k]) / data[data.shape[0]//2, k] *100
                np.savetxt("tmp.dat", np.c_[data[:, [0, k]], MR.T], fmt="%.8e", delimiter=",")
                MRall[:, k] = MR.T
            if abc == "1,1,1":
                if type == "hall":
                    headline = "Field(T),Ryx(ohm)"
                else:
                    headline = "Field(T),Rxx(ohm)" + ",MR(%)"
            else:
                if type == "hall":
                    headline = "Field(T),rhoyx(ohm cm)"
                else:
                    headline = "Field(T),rhoxx(ohm cm)" + ",MR(%)"
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
        addheadline(mrhead, "tmp.dat", workdirdata + "MRall.dat")


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


def inter(m, type, intervals):
    """根据输入的m数据，intervals列表（包含(limit, step)元组），type类型"""
    a = 1
    if m[1, 1] < 0:  # 取第一行第一列判断是否为负值
        a = -1
    u, indices = np.unique(m[:, 1], return_index=True)
    fx = interpolate.interp1d(m[indices, 1] / 10000, m[indices, 2], kind="linear",
                              fill_value="extrapolate")
    
    x_segments = []
    last_limit = 0.0
    
    for limit, step in intervals:
        range_oe = (limit - last_limit) * 10000
        num = round(range_oe / step)  # 使用round避免浮点精度问题
        
        # Determine current segment points
        # Start from last_limit, go to limit.
        # If it's not the first segment, we skip the first point to avoid duplication
        this_x = np.linspace(a * last_limit, a * limit, num + 1)
        
        if len(x_segments) > 0:
            x_segments.append(this_x[1:])
        else:
            x_segments.append(this_x)
            
        last_limit = limit
        
    x = np.concatenate(x_segments)
    internumber = x.size
    
    intery = np.zeros([x.size, 2])
    intery[:, 0] = a * x
    if type == 3:
        intery[:, 1] = a * fx(x)
    else:
        intery[:, 1] = fx(x)
    return intery, internumber


def interloop(m, type, intervals):
    """根据输入的m数据，intervals列表，type类型"""
    a = 1
    emm=0
    while m[emm+1, 1] - m[emm, 1]==0:
        emm=emm+1
    if m[emm+1, 1] - m[0, 1] < 0:  # 判断升场还是降场
        a = -1
    u, indices = np.unique(m[:, 1], return_index=True)
    fx = interpolate.interp1d(m[indices, 1] / 10000, m[indices, 2], kind="linear",
                              fill_value="extrapolate")
    
    # Generate positive half first (0 to max)
    pos_segments = []
    last_limit = 0.0
    
    for limit, step in intervals:
        range_oe = (limit - last_limit) * 10000
        # For symmetric loop, we want intervals on both sides.
        # Here we just generate 0 -> limit with step
        num = round(range_oe / step)  # 使用round避免浮点精度问题
        
        this_x = np.linspace(last_limit, limit, num + 1)
        
        if len(pos_segments) > 0:
            pos_segments.append(this_x[1:])
        else:
            pos_segments.append(this_x)
            
        last_limit = limit
        
    x_pos = np.concatenate(pos_segments)
    
    # Mirror to get negative half: [-max, ..., 0] -> we want [-max, ..., -step]
    # x_pos is [0, step, ..., max]
    x_neg = -x_pos[1:][::-1] # [-max, ..., -step]
    
    # Concatenate: neg + pos -> [-max, ..., -step, 0, step, ..., max]
    x_total = np.concatenate([x_neg, x_pos])
    
    # Apply direction 'a'
    # If a=1 (normal), we want -max to max. x_total is -max to max. Correct.
    # If a=-1 (descending?), user might expect range -> -range?
    # Current code `spit` passes `range` (positive).
    # interloop in old code:
    # x1 = linspace(-range, -split)
    # x3 = linspace(split, range)
    # If a=-1, it basically flips the x axis.
    
    x = a * x_total
    internumber = x.size

    intery = np.zeros([x.size, 2])
    intery[:, 0] = a * x
    if type == 3:
        intery[:, 1] = a * fx(x)
    else:
        intery[:, 1] = fx(x)
    return intery, internumber


def spit(dataT, type, intervals):
    """将单个温度的数据进行正负场的分离，并使用inter函数，并做平均"""
    global loop
    row = 1
    Fchange = []
    print("当前处理温度%.1fK"%dataT[0,0])
    print(dataT)
    while row < dataT.shape[0]:
        if row > 0:
            dataF = dataT[row, 1] * dataT[row - 1, 1]
            if dataF <= 0:  # 判断磁场转变点，正负转换
                if len(Fchange)!=0:
                    if row!=Fchange[-1]+1:
                       Fchange.append(row)
                    else: Fchange[-1]=row
                else: 
                    Fchange.append(row)
        row = row + 1
    
    # 处理 Fchange 为空的情况（数据没有经过零点，只有正场或只有负场）
    if len(Fchange) == 0:
        print("警告：该温度数据没有经过零点，只有单边磁场数据")
        # 只有单边数据，直接使用 inter 处理整个数据
        [av, internumber] = inter(dataT, type, intervals)
        return av, internumber
    elif len(Fchange) == 2:
        print("存在loop线，或多次经过零点，需要注意是否数据有问题,按照loop线处理")
        loop=True
        row = 3
        Fchange2 = []
        while row < dataT.shape[0]:
            if row > 0:
                if np.argmax(dataT[row - 3:row, 1]) == 1 or np.argmin(dataT[row - 3:row, 1]) == 1:
                    Fchange2.append(row - 1)
            row = row + 1
        emm = 0
        while dataT[emm + 1, 1] - dataT[emm, 1] == 0:
            emm = emm + 1
        if dataT[emm+1, 1] - dataT[emm, 1] > 0:
            Fchange2 = [np.argmax(dataT[:, 1])]
            print("升")
        else:
            Fchange2 = [np.argmin(dataT[:, 1])]
        a1 = dataT[:Fchange2[-1]+1, :]
        a2 = dataT[Fchange2[-1]:, :]
        print(a1)
        [av1,internumber1] = interloop(a1, type, intervals)
        [av2,internumber2]=interloop(a2, type, intervals)
    elif len(Fchange) > 2:
        print("单个温度数据三次及以上经过零点，请检查数据")
        print(1 / 0)
    else:
        j = Fchange[0]
        a1 = dataT[:j + 1, :]
        a2 = dataT[j - 1:, :]
        # print(a1,a2)
        [av1,internumber1]= inter(a1, type, intervals)
        [av2,internumber2]=inter(a2, type, intervals)
    av=(av1+av2)/2
    internumber=internumber2
    return av,internumber


def dealdata(name, lie, interval, plot, type):
    """处理数据的主体,type=2为R，type=3为hall"""
    global loop
    plt.subplot(plot)
    data = pd.read_csv(name,sep="\t",header=None,na_values='--')
    rows, column_count = data.shape
    """a = open(name, "r+")
    data = a.readlines()
    a.close()
    rows = len(data)  # 数据总行
    l = 0
    for line in data:
        line = line.strip().split('\t')  # strip()默认移除字符串首尾空格或换行符
        if line[lie] == "--":
            l = l + 1
    rows = rows - l  # 确认非空数据行数
    # print(rows)"""
    data2 = np.zeros((rows, 3))  # 创建数据储存矩阵
    row = 0  # 数据处理的行数
    Tchange = []  # 温度变化点
    Fchange = []  # 磁场变化点
    for line in data.itertuples():
        if pd.isnull(line[lie+1]):
            continue
        data2[row, 0] = line[1]
        data2[row, 1] = line[2]
        data2[row, 2] = line[lie+1]  # 数据转移至data2并处理空格
        # print(data2[row,0])
        if row > 0:
            if abs(data2[row, 0] - data2[row - 1, 0]) > 10:  # 判读温度转变点
                Tchange.append(row)
        row += 1
    data2=data2[:row,:]
    #print(Tchange)
    """a=0
    for i in Tchange:
        print(i-a)
        a=i
    print(rows-a)"""
    # print(Fchange)
    i = 0  # 数据以温度未根据进行的分组
    first_internumber = None  # 记录第一个温度的 internumber
    dataall = None
    while True:
        if i > 0:  # 以温度为依据分段
            dataT = data2[Tchange[i - 1]:Tchange[i], :]  # dataT为每个温度的分离
            [dataspit,internumber] = spit(dataT, type, interval)
            plt.plot(dataT[:, 1], dataT[:, 2], label="%.1f" % data2[Tchange[i - 1], 0] + "K")
            if type == 3:
                plt.ylabel("Ryx(ohm)")
            else:
                plt.ylabel("R(ohm)")
            plt.xlabel("Field(Oe)")
            
            # 检查 internumber 是否一致
            if internumber != first_internumber:
                print(f"警告：温度 {data2[Tchange[i - 1], 0]:.1f}K 的插值点数 ({internumber}) 与第一个温度 ({first_internumber}) 不一致")
                # 调整数据大小以匹配
                if internumber < first_internumber:
                    # 需要扩展 dataspit
                    new_dataspit = np.zeros((first_internumber, 2))
                    new_dataspit[:internumber, :] = dataspit
                    # 使用最后一个值填充剩余部分
                    new_dataspit[internumber:, 0] = dataspit[-1, 0]
                    new_dataspit[internumber:, 1] = dataspit[-1, 1]
                    dataspit = new_dataspit
                else:
                    # 需要截断 dataspit
                    dataspit = dataspit[:first_internumber, :]
            
            dataall[:, 0] = dataspit[:, 0]
            dataall[:, i + 1] = dataspit[:, 1]
        else:  # 第一组则取0：。
            if Tchange == []:
                dataT = data2[:, :]
            else:
                dataT = data2[:Tchange[i], :]
            [dataspit,internumber]= spit(dataT, type, interval)
            first_internumber = internumber  # 记录第一个温度的 internumber
            if loop:
                dataall = np.zeros([internumber, 40])
            else:
                dataall = np.zeros([internumber, 40])
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
            [dataspit,internumber] = spit(dataT, type, interval)
            
            # 检查 internumber 是否一致
            if internumber != first_internumber:
                print(f"警告：最后一个温度的插值点数 ({internumber}) 与第一个温度 ({first_internumber}) 不一致")
                if internumber < first_internumber:
                    new_dataspit = np.zeros((first_internumber, 2))
                    new_dataspit[:internumber, :] = dataspit
                    new_dataspit[internumber:, 0] = dataspit[-1, 0]
                    new_dataspit[internumber:, 1] = dataspit[-1, 1]
                    dataspit = new_dataspit
                else:
                    dataspit = dataspit[:first_internumber, :]
            
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


def deal(file, interval, abc):
    """处理数据的多个温度文件的储存"""
    if halltest(file):
        fig = plt.figure(figsize=(19.2, 10.8))
        [dataR, headline] = dealdata(file, 2, interval, 221, 2)
        type = "R"
    else:
        type = input("检测到只有三列数据，请输入R或者H(hall)，回车默认R\n")
        if type == "R" or type == "":
            type = "R"
            fig = plt.figure(figsize=(9.6, 10.8))
            [dataR, headline] = dealdata(file, 2, interval, 211, 2)
    if type == "R":
        dataR = dataR.T[~(dataR == 0).all(0)].T  # 去除0列
        dataR = Rtorho(dataR, abc)
        
        # 处理dataR：第一列取反，偶数列不变，然后倒序插入原始数据前
        new_dataR = dataR.copy()
        # 奇数列（第1列）
        new_dataR[:, 0] = -dataR[:, 0]
        if loop==False:
            new_dataR = new_dataR[::-1]  # 倒序
        else:
            new_dataR = new_dataR[::]
        dataR = np.vstack((new_dataR, dataR))  # 拼接
        
        np.savetxt(workdirdata + "dealed-R.dat", dataR, fmt="%.8e", delimiter=",")
        headlinestr = "Field(T)"
        mrhead ="Field(T)"
        for i in headline:
            if abc == "1,1,1":
                headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm)"
            else:
                headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm cm)"
        
            mrhead=mrhead+"," + "%.1f" % i + "K(%)"
        addheadline(headlinestr, workdirdata + "dealed-R.dat", workdirdata + "dealed-R-" + abc + ".dat")
        savesinglefile(headlinestr, dataR, "R", abc,mrhead)
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
        mrhead = ""
        if type == "H":
            fig = plt.figure(figsize=(9.6, 10.8))
            [datahall, headline] = dealdata(file, 2, interval, 211, 3)
        else:
            [datahall, headline] = dealdata(file, 3, interval, 222, 3)
        datahall = datahall.T[~(datahall == 0).all(0)].T  # 去除0列
        datahall = Ryxtorhoyx(datahall, abc)
        
        # 处理datahall：所有列取反，然后倒序插入原始数据前
        new_datahall = -datahall.copy()  # 所有列取反
        if loop==False:
            new_datahall = new_datahall[::-1]  # 倒序
        else:
            new_datahall = new_datahall[::]  # loop倒序
        datahall = np.vstack((new_datahall, datahall))  # 拼接
        
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
        savesinglefile(headlinestr, datahall, "hall", abc, mrhead)
    plt.tight_layout()
    plt.show()
    fig.savefig("alldata.png")


# ============== GUI Wrapper Functions ==============

def deal_with_params(file, intervals, abc, data_type=None, show_plot=True):
    """
    GUI版本的deal函数，接受参数而不是input()
    data_type: None=自动检测, "R"=电阻, "H"=霍尔
    返回: (success, message, needs_type_input)
    """
    global loop
    
    if halltest(file):
        fig = plt.figure(figsize=(19.2, 10.8))
        [dataR, headline] = dealdata(file, 2, intervals, 221, 2)
        type_val = "R"
    else:
        if data_type is None:
            return (False, "检测到只有三列数据，请选择数据类型", True)
        type_val = data_type if data_type in ["R", "H"] else "R"
        if type_val == "R":
            fig = plt.figure(figsize=(9.6, 10.8))
            [dataR, headline] = dealdata(file, 2, intervals, 211, 2)
    
    if type_val == "R":
        dataR = dataR.T[~(dataR == 0).all(0)].T
        dataR = Rtorho(dataR, abc)
        
        new_dataR = dataR.copy()
        new_dataR[:, 0] = -dataR[:, 0]
        if loop == False:
            new_dataR = new_dataR[::-1]
        else:
            new_dataR = new_dataR[::]
        dataR = np.vstack((new_dataR, dataR))
        
        np.savetxt(workdirdata + "dealed-R.dat", dataR, fmt="%.8e", delimiter=",")
        headlinestr = "Field(T)"
        mrhead = "Field(T)"
        for i in headline:
            if abc == "1,1,1":
                headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm)"
            else:
                headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm cm)"
            mrhead = mrhead + "," + "%.1f" % i + "K(%)"
        addheadline(headlinestr, workdirdata + "dealed-R.dat", workdirdata + "dealed-R-" + abc + ".dat")
        savesinglefile(headlinestr, dataR, "R", abc, mrhead)
        if halltest(file):
            plt.subplot(223)
        else:
            plt.subplot(212)
        if abc == "1,1,1":
            plot(headline, dataR, "R(ohm)")
        else:
            plot(headline, dataR, "rho(ohm cm)")
    
    if halltest(file) or type_val == "H":
        mrhead = ""
        if type_val == "H":
            fig = plt.figure(figsize=(9.6, 10.8))
            [datahall, headline] = dealdata(file, 2, intervals, 211, 3)
        else:
            [datahall, headline] = dealdata(file, 3, intervals, 222, 3)
        datahall = datahall.T[~(datahall == 0).all(0)].T
        datahall = Ryxtorhoyx(datahall, abc)
        
        new_datahall = -datahall.copy()
        if loop == False:
            new_datahall = new_datahall[::-1]
        else:
            new_datahall = new_datahall[::]
        datahall = np.vstack((new_datahall, datahall))
        
        headlinestr = "Field(T)"
        for i in headline:
            if abc == "1,1,1":
                headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm)"
            else:
                headlinestr = headlinestr + "," + "%.1f" % i + "K(ohm cm)"
        np.savetxt(workdirdata + "dealed-hall.dat", datahall, fmt="%.8e", delimiter=",")
        addheadline(headlinestr, workdirdata + "dealed-hall.dat", workdirdata + "dealed-hall-" + abc + ".dat")
        if type_val == "H":
            plt.subplot(212)
        else:
            plt.subplot(224)
        if abc == "1,1,1":
            plot(headline, datahall, "Ryx(ohm)")
        else:
            plot(headline, datahall, "rhoyx(ohm cm)")
        savesinglefile(headlinestr, datahall, "hall", abc, mrhead)
    
    plt.tight_layout()
    fig.savefig(workdir + "/alldata.png")
    if show_plot:
        plt.show()
    plt.close(fig)
    
    return (True, "数据处理完成", False)


def fitprocess_with_params(run_fit=False):
    """GUI版本的fitprocess，接受参数控制是否拟合"""
    if not run_fit:
        return (True, "跳过双带拟合", [])
    
    fitfiles = [entry.path for entry in os.scandir(workdirdata) if "1,1,1" in entry.name]
    warning_msg = ""
    if fitfiles != []:
        warning_msg = "警告：由于dealed-hall-1,1,1.dat存在，认为没有进行ohm至ohm cm的计算，不推荐进行拟合计算"
    
    fitfile = open(workdirfit + "twobandfit.dat", "w+")
    fitfile.write("Temp(K),ne(cm^-3),nh(cm^-3),miue(cm^2/(s*V)),miuh(cm^2/(s*V)),ne Confidence intervals(cm^-3),nh Confidence intervals(cm^-3),miue Confidence intervals(cm^2/(s*V)),miuh Confidence intervals(cm^2/(s*V))\n")
    fitfile.close()
    
    Rfitfiles = relist([entry.path for entry in os.scandir(workdir + "\\data") if "K" in entry.name and "R" in entry.name])
    Rfitfiles = relist2(Rfitfiles, 2, -5)
    hallfitfiles = relist([entry.path for entry in os.scandir(workdir + "\\data") if "K" in entry.name and "hall" in entry.name])
    hallfitfiles = relist2(hallfitfiles, 5, -5)
    
    Rnums = len(Rfitfiles)
    hallnums = len(hallfitfiles)
    
    if Rnums != hallnums or Rnums == 0 or hallnums == 0:
        return (False, "data文件夹数据文件不正确，一般是由于只有R或者只有hall", [])
    
    num = 0
    arg = np.zeros([Rnums, 5])
    generated_files = []
    
    try:
        while True:
            line = Rfitfiles[num].strip().split("-")
            line = line[-1].strip().split('K')
            arg[num, 1:] = fit(Rfitfiles[num], hallfitfiles[num], line[0])
            generated_files.append(workdirfit + "twoband-" + line[0] + "K.png")
            num = num + 1
            if num == Rnums:
                break
    except Exception as error:
        return (False, f"拟合过程出错: {error}", generated_files)
    
    return (True, warning_msg if warning_msg else "双带拟合完成", generated_files)


def fitRHprocess_with_params(run_fit=False, fit_range=(0, 14)):
    """GUI版本的fitRHprocess，接受参数控制是否拟合和拟合范围"""
    if not run_fit:
        return (True, "跳过RH拟合", [])
    
    low, high = fit_range
    
    fitfile = open(workdirfit + "fitRH.dat", "w+")
    fitfile.write("Temp(K),RH(cm^3/C),intercept(ohm cm),Correlation coefficien,Carrier concentration(cm^-3),carrier mobility(cm^2/(s*V))\n")
    fitfile.close()
    
    fitfiles = relist([entry.path for entry in os.scandir(workdir + "/data") if "K" in entry.name and "hall" in entry.name])
    fitfiles = relist2(fitfiles, 5, -5)
    fitfilesR = relist([entry.path for entry in os.scandir(workdir + "/data") if "K" in entry.name and "R" in entry.name])
    fitfilesR = relist2(fitfilesR, 2, -5)
    
    if fitfiles == []:
        return (False, "没有hall文件", [])
    
    nums = len(fitfiles)
    if nums == 0:
        return (False, "没有需要的hall文件", [])
    
    num = 0
    arg = np.zeros([nums, 4])
    generated_files = []
    
    while True:
        line = fitfiles[num].strip().split("-")
        line = line[-1].strip().split('K')
        if fitfilesR == []:
            arg[num, 1:] = fitRH(fitfiles[num], "", line[0], low, high)
        else:
            arg[num, 1:] = fitRH(fitfiles[num], fitfilesR[num], line[0], low, high)
        generated_files.append(workdirfit + "RH-" + line[0] + "K.png")
        arg[num, 0] = line[0]
        num = num + 1
        if num == nums:
            break
    
    return (True, "RH拟合完成", generated_files)


def get_data_files():
    """获取工作目录下的dat文件列表"""
    return [entry.path for entry in os.scandir(workdir) if entry.name.endswith(".dat")]


def check_data_folder():
    """检查data文件夹状态"""
    if os.path.exists(workdirdata) and os.listdir(workdirdata):
        return True
    return False


def check_fit_folder():
    """检查fit文件夹状态"""
    if os.path.exists(workdirfit):
        datafile = [entry.path for entry in os.scandir(workdirfit) if entry.name.endswith(".dat")]
        if datafile != []:
            return True
    return False


def ensure_folders():
    """确保必要的文件夹存在"""
    try:
        os.makedirs(workdir + "/data", 777)
    except:
        pass
    try:
        os.makedirs(workdir + "/fit", 777)
    except:
        pass


def parse_intervals(interval_input):
    """解析内插分段输入"""
    if interval_input == "":
        interval_input = "14:20"
    
    intervals = []
    try:
        segments = interval_input.replace("，", ",").strip().split(',')
        for seg in segments:
            limit, step = seg.strip().split(':')
            intervals.append((float(limit), float(step)))
        intervals.sort(key=lambda x: x[0])
    except:
        intervals = [(14.0, 20.0)]
    
    return intervals


# ============== Main Execution ==============

if __name__ == "__main__":
    if os.path.exists(workdirdata) and os.listdir(workdirdata):
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
            interval_input = input("输入内插分段，格式为'范围:间隔'，多个分段用逗号隔开 (示例: 4:20, 14:100)，回车默认14:20\n")
            
            if interval_input == "":
                interval_input = "14:20"
                
            intervals = []
            try:
                segments = interval_input.replace("，", ",").strip().split(',')
                for seg in segments:
                    limit, step = seg.strip().split(':')
                    intervals.append((float(limit), float(step)))
                intervals.sort(key=lambda x: x[0])
                print("内插分段为:", intervals)
            except Exception as e:
                print("输入格式错误，使用默认14:20")
                intervals = [(14.0, 20.0)]

            abc = input("输入长宽高，逗号隔开，单位为cm，回车则皆为1，即输出为电阻\n")
            if abc == "":
                abc = "1,1,1"
            print("长宽高分别为" + abc)
            input("确认参数")
            abc = abc.replace("，", ",")
            deal(datafile[0], intervals, abc)

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
            if loop:
                print("对于有loop的数据不建议使用双带拟合")
            fitprocess()
            fitRHprocess()
        except Exception as error:
            print(error)
    try:
        os.removedirs(workdirfit)
    except Exception as error:
        pass
    input("by fuyang ヽ(°∀°)ﾉ  \n 按任意键结束")

