import os
import numpy as np
workdir = os.getcwd()
RytoeV = 13.605662285137
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
files=relist([entry.path for entry in os.scandir(workdir) if entry.name.startswith("results")])
data = []
headline = ["",""]
data=np.zeros([1000,6])
j=0
for filename in files:
    name=filename[-8:]
    a=open(filename)
    contect=a.readlines()
    for i in contect:
        if i[1:5]=="Freq":
            data[j, 0]=i[11:17]#频率，质量，电子还是空穴
            data[j, 1]=i[40:46]
            data[j, 2]=i[125:127]
        if i[1:5]=="Orbi":
            data[j,3] = i[47:53]#坐标
            data[j,4]=i[67:73]
            data[j,5]=i[87:93]
            j=j+1
        if i[1:5]=="Ferm":
            data[j,0]=float(i[19:27])
            data[j, 1] = float(i[19:27]) * RytoeV
            j=j+1
        if i[1:5]=="XCry":
            name=i[23:].strip().split()[0]
    a.close()
headline="Freq(kT),m*(me),e/h,x-coord,y-coord,z-coord"
data = data[~(data == 0).all(1)]
data = data.T[~(data == 0).all(0)].T  # 去除0列
np.savetxt("tmp.dat", data, fmt="%.4f", delimiter=",")
newfile=addheadline(headline,"tmp.dat",name+".dat")
with open(newfile, "r+")as fp:
    b = open("tmp.dat", "w+")
    for line in fp:
        line = line.replace("0.0000,0.0000,0.0000,0.0000,0.0000,0.0000", ",,,,,")
        line = line.replace("0.0000,0.0000,0.0000,0.0000", ",,,")
        b.write(line)
    b.close()
with open("tmp.dat", "r+") as fp:
    c = open(newfile, "w+")
    for line in fp:
        c.write(line)
    c.close()
os.remove("tmp.dat")
"""
数据结构：
第一行是数据的名称
对于只有两列的数据行则是能量，第一行是Ry，第二行是eV
"""