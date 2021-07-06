import os
import numpy as np
workdir = os.getcwd()
RytoeV = 13.605662285137
def replace0(a):
    m = a.strip().split(",")
    newstr=""
    for i in m:
        if i=="0.0000":
            i = ""
        newstr=newstr+i+","
    newstr=newstr[:-1]+"\n"
    return newstr
def relist(file):
    """对文件重新排序，使得（2）在无（2）后面"""
    list=[]
    for i in file:
        i = i
        list.append(i)
    list.sort()
    newlist=list
    return newlist
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
        newfile=rename(newfile)
        fpw=open(newfile,"w+")
        fpw.write(headline + "\n" + tmp_data)
        fpw.close()
    os.remove(oldfile)
    return(newfile)
m=0
headline=""
data=np.zeros([10000,200])
files = relist([entry.path for entry in os.scandir(workdir) if entry.name.endswith(".out")])
for filename in files:
    a = open(filename)
    contect = a.readlines()
    name = filename[-8:]
    k = -1
    j = 0
    for i in contect:
        if i[1:5] == "Freq":
            data[k * 40 + j, 8 * m + 2] = i[9:17]  # 频率，质量，电子还是空穴
            data[k * 40 + j, 8 * m + 3] = i[38:46]
            data[k * 40 + j, 8 * m + 4] = i[125:127]
        if i[1:5] == "Orbi":
            data[k * 40 + j, 8 * m + 5] = i[47:53]  # 坐标
            data[k * 40 + j, 8 * m + 6] = i[67:73]
            data[k * 40 + j, 8 * m + 7] = i[87:93]
            j = j + 1
        if i[1:5] == "ANGL":
            k=k+1
            j=0
            data[k * 40 + j, 8 * m + 0] = float(i[30:41])
            data[k * 40 + j, 8 * m + 1] = float(i[48:59])
            j = j + 1
        if i[1:5] == "XCry":
            name = i[42:45].strip().split()[0]
    a.close()
    k = k + 1
    m=m+1
    headline = headline+name+"theta,phi,Freq(kT),m*(me),e/h,x-coord,y-coord,z-coord,"
data = data[~(data == 0).all(1)]
data = data.T[~(data == 0).all(0)].T  # 去除0列
np.savetxt("tmp.dat", data, fmt="%.4f", delimiter=",")
newfile = addheadline(headline, "tmp.dat", files[0][-14:-8] + ".dat")#需注意命名方式
print(newfile)
with open(newfile, "r+")as fp:
    b = open("tmp.dat", "w+")
    for line in fp:
        #line = line.replace("0.0000,0.0000,0.0000,0.0000,0.0000,0.0000", ",,,,,")
        line = replace0(line)
        b.write(line)
    b.close()
with open("tmp.dat", "r+") as fp:
    c = open(newfile, "w+")
    for line in fp:
        c.write(line)
    c.close()
os.remove("tmp.dat")