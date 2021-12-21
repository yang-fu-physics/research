subdir=["577","578","579","580","581","582","583","584","585","586","587","588","589","590","591","592","593","594","595","596","597","598","599","600","601","602"]#subfolder for results
import os
import numpy as np
workdir = os.getcwd()
RytoeV = 13.605662285137
def replace0(a):
    """Delete the 0 in the file"""
    m = a.strip().split(",")
    newstr=""
    for i in m:
        if i=="0.0000":
            i = ""
        newstr=newstr+i+","
    newstr=newstr[:-1]+"\n"
    return newstr
def relist(file):
    """Reorder the file so that file with a serial number follows file without serial number"""
    list=[]
    for i in file:
        i = i
        list.append(i)
    list.sort()
    newlist=list
    return newlist
def rename(newfile):
    #if file exited, then rename newfile which is old file name add serial number.
    i = 2
    last=newfile.strip().split('.')[-1]
    newfile = newfile[:-1*len(last)-1]
    while True:
        try:
            fpw = open(newfile+"."+last, "r")
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
    """Add a header to the new file and delete the old file"""
    with open(oldfile, "r+")as fp:
        tmp_data = fp.read()
        fp.seek(0)  # Move the cursor
        newfile=rename(newfile)
        fpw=open(newfile,"w+")
        fpw.write(headline + "\n" + tmp_data)
        fpw.close()
    os.remove(oldfile)
    return(newfile)

m=0
headline=""
data=np.zeros([50000,1000])
for n in subdir:
    subworkdir=workdir+"/"+n
    num=400
    print(m)
    files = relist([entry.path for entry in os.scandir(subworkdir) if entry.name.startswith("results")])
    k = 0
    for filename in files:
        name = filename[-8:]
        a = open(filename)
        contect = a.readlines()
        j = 0
        for i in contect:
            if i[1:5] == "Freq":
                data[k * num + j, 8 * m + 2] = i[9:17]  # Frequency, mass, electron or hole
                data[k * num + j, 8 * m + 3] = i[38:46]
                data[k * num + j, 8 * m + 4] = i[125:127]
            if i[1:5] == "Orbi":
                data[k * num + j, 8 * m + 5] = i[47:53]  # coordinate
                data[k * num + j, 8 * m + 6] = i[67:73]
                data[k * num + j, 8 * m + 7] = i[87:93]
                j = j + 1
            if i[1:5] == "Ferm":
                data[k * num + j, 8 * m + 0] = float(i[19:27])  #fermi energy
                data[k * num + j, 8 * m + 1] = float(i[19:27]) * RytoeV
                j = j + 1
            if i[1:5] == "XCry":
                name = i[23:].strip().split()[0]

        a.close()
        if j > num:
            print("error")
        k = k + 1
    m=m+1
    headline = headline+n+"Fermi(Ry),Fermi(eV),Freq(kT),m*(me),e/h,x-coord,y-coord,z-coord,"
data = data[~(data == 0).all(1)]  #Get rid of all 0 rows
data = data.T[~(data == 0).all(0)].T  # Get rid of all 0 columns
np.savetxt("tmp.dat", data, fmt="%.4f", delimiter=",")
newfile = addheadline(headline, "tmp.dat", "result.dat")
with open(newfile, "r+")as fp:
    b = open("tmp.dat", "w+")
    for line in fp:
        line = replace0(line)
        b.write(line)
    b.close()
with open("tmp.dat", "r+") as fp:
    c = open(newfile, "w+")
    for line in fp:
        c.write(line)
    c.close()
os.remove("tmp.dat")