import numpy as np
import matplotlib.pyplot as plt
"""读取多个文件，并提取相应列数至同一文件"""
filelist=["-newRH-1.8k-r-90-10mA-ch3sr554.dat","RH-3k-90-10mA-ch3sr554.dat","RH-4k-90deg-10mA-ch3sr554.dat","RH-5k-90-10mA-ch3sr554.dat","RH-6k-90deg-10mA-ch3sr554.dat","RH-7k-90-10mA-ch3sr554.dat","RH-8k-90deg-10mA-ch3sr554.dat","RH-9k-90-10mA-ch3sr554.dat","RH-10k-90deg-10mA-ch3sr554.dat","RH-11k-90-10mA-ch3sr554.dat","RH-15k-90-10mA-ch3sr554.dat","RH-20k-90-10mA-ch3sr554.dat","RH-25k-90-10mA-ch3sr554.dat","RH-30k-90-10mA-ch3sr554.dat","RH-35k-90-10mA-ch3sr554.dat"]
header="Filed,1.8K,Filed,3K,Filed,4K,Filed,5K,Filed,6K,Filed,7K,Filed,8K,Filed,9K,Filed,10K,Filed,11K,Filed,15K,Filed,20K,Filed,25K,Filed,30K,Filed,35K"
#filelist = ["RH-1.8k-r-90-10mA-ch3sr554.dat","RH-1.8K-85deg-10ma-ch3sr554.dat","RH-1.8K-80deg-10ma-ch3sr554.dat","RH-1.8K-75deg-10ma-ch3sr554.dat","RH-1.8K-70deg-10ma-ch3sr554.dat","RH-1.8K-60deg-10ma-ch3sr554.dat","RH-1.8K-50deg-10ma-ch3sr554.dat","RH-1.8K-40deg-10ma-ch3sr554.dat","RH-1.8K-30deg-10ma-ch3sr554.dat","RH-1.8K-20deg-10ma-ch3sr554.dat","RH-1.8K-10deg-10ma-ch3sr554.dat"]
#header="Filed,0,Filed,5,Filed,10,Filed,15,Filed,20,Filed,30,Filed,40,Filed,50,Filed,60,Filed,70,Filed,80"
datadeg = np.zeros([2000, 40])
k = 0
ch = 3
fi = 0
for i in filelist:
    a = open(i)
    data = a.readlines()[1:]
    j = 0
    buer = True
    for line in data:
        line = line.strip().split('\t')
        if float(line[fi]) > 0 and buer:
            datadeg[j, 2 * k + 1] = line[ch]
            datadeg[j, 2 * k + 1] =datadeg[j, 2 * k + 1] /0.044336 * 0.1122 *0.00685
            datadeg[j, 2 * k] = line[fi]
            j = j + 1
        if float(line[fi]) > 32:
            buer = False
    a.close()
    k = k + 1
datadegcut0 = datadeg[~(datadeg == 0).all(1)]#去除0行
datadegcut00=datadegcut0.T[~(datadegcut0==0).all(0)].T#去除0列
#print(datadeg.shape)
#print(datadegcut0.shape)
#print(datadegcut00.shape)
np.savetxt("dealed.dat", datadegcut00, fmt="%.8e", delimiter=",")
with open("dealed.dat", "r+")as fp:
    tmp_data = fp.read()  # 读取所有文件, 文件太大时不用使用此方法
    fp.seek(0)  # 移动游标
    fp.write(header + "\n" + tmp_data)
with open("dealed.dat","r+")as fp:
    b=open("dealed-0.dat","w+")
    for line in fp:
        line = line.replace("0.00000000e+00", "")
        b.write(line)
    b.close()

k=plt.plot(datadegcut0[:, 0], datadegcut0[:, 1])
plt.show()