import os
import numpy as np
import time
workdir = os.getcwd()
pi = 3.141592654
h = 6.62607004 * 10 ** -34
e = 1.60217733 * 10 ** -19
me = 9.10938356 * 10 ** -30
file = [entry.path for entry in os.scandir(workdir) if entry.name.endswith(".dat")]
def rename(newfile):
    i = 2
    last=newfile.strip().split('.')[-1]
    newfile = newfile[:-1*len(last)-1]
    while True:
        try:
            fpw = open(newfile+"."+last, "r")  # 如果不存在会报错
            fpw.close
            if i == 2:
                newfile = newfile + "(%i)" % i
            else:
                newfile = newfile[:-1*len(str(i))-2] + "(%i)" % i
            i = i + 1
        except IOError:
            break
    newfile=newfile+"."+last
    return newfile
def addheadline(headline, oldfile, newfile):
    """在新文件中加入抬头，删除旧文件"""
    with open(oldfile, "r+")as fp:
        tmp_data = fp.read()  # 读取所有文件, 文件太大时不用使用此方法
        fp.seek(0)  # 移动游标
        fpw=open(rename(newfile),"w+")
        fpw.write(headline + tmp_data)#原本headline就有回车
        fpw.close()
    time.sleep(0.1)
    os.remove(oldfile)
def dealdata(name,lie,unit,error,pre):
    """处理数据的主体,lie代表转变点#需要更改第二项选择分隔依据，低四项是分隔标准"""
    a = open(name, "r+")
    headstr=a.readline()
    head=headstr.strip().split('\t')
    data = a.readlines()
    a.close()
    rows = len(data)  # 数据总行
    l = 0
    for line in data:
        line = line.strip().split('\t')  # strip()默认移除字符串首尾空格或换行符
        if line[0] == "--":
            l = l + 1
    rows = rows - l  # 确认非空数据行数
    # print(rows)
    data2 = np.zeros((rows, len(head)))  # 创建数据储存矩阵
    row = 0  # 数据处理的行数
    Tchange = []  # 温度变化点
    for line in data:
        line = line.strip().split('\t')
        if line[0] == "--" or line[0] == "":
            continue
        data2[row, :] = line[:] # 数据转移至data2并处理空格
        # print(data2[row,0])
        if row > 0:
            if abs(data2[row, lie] - data2[row - 1, lie]) > error:  # 判读温度转变点
                Tchange.append(row)
        row += 1
    i = 0  # 数据以温度未根据进行的分组
    print(Tchange)
    while True:
        if i > 0:  # 以温度为依据分段
            dataT = data2[Tchange[i - 1]:Tchange[i], :]  # dataT为每个温度的分离
        else:  # 第一组则取0：。
            if Tchange == []:
                dataT = data2[:, :]
            else:
                dataT = data2[:Tchange[i], :]
            if Tchange == []:
                np.savetxt("tmp.dat", dataT, fmt="%.8e", delimiter="\t")
                addheadline(headstr, "tmp.dat", pre + "%.1f" % dataT[0, lie] + unit + ".dat")
                break
        np.savetxt("tmp.dat", dataT, fmt="%.8e", delimiter="\t")
        addheadline(headstr, "tmp.dat", pre + "%.1f" % dataT[0, lie] + unit + ".dat")
        if i == len(Tchange) - 1:  # 如果是最后一个点，则额外输出一个至最后的数组。并跳出循环
            dataT = data2[Tchange[i]:, :]
            print(Tchange[i])
            np.savetxt("tmp.dat", dataT, fmt="%.8e", delimiter="\t")
            addheadline(headstr, "tmp.dat", pre+"%.0f" %dataT[0,lie] +unit+ ".dat")
            break
        # print(i)
        i = i + 1
    Tchange.insert(0, int(0))
    return data2[Tchange, 0]



file = [entry.path for entry in os.scandir(workdir) if entry.name.endswith(".dat")]
if 0==0:
    if len(file) > 1:
        print("dat文件过多")
    else:
        dealdata(file[0],0,"K",2,"")#需要更改第二项选择分隔依据，低四项是分隔标准
file = [entry.path for entry in os.scandir(workdir) if entry.name.endswith("K.dat")]
"""for i in file:
    dealdata(i,46,"Hz",1,i[:-4]+"-")
    #dealdata(i, 9, "Hz", 0.5, "")"""
