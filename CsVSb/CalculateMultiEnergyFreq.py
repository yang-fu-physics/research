fermienergy=0.505201
a =fermienergy+0.00735#max fermi
b =fermienergy-0.00735#min fermi
c =0.000350#interval
import os
import numpy as np
import shutil
workdir=os.getcwd()
filenames = [entry.path for entry in os.scandir(workdir) if entry.name.endswith(".bxsf")]
filenames.sort()
subdir=[]
for i in filenames:
    print(i[-8:-5])
    subdir.append(i[-8:-5])#subfolder for results
def rewritefilename(name):
    """rewrite config.in to change the bxsf file in config.in """
    newline = []
    config = open("config.in", "r+")
    i = 0
    filename=name
    while len(filename)<52:
        filename=filename+" "
    while 1:
        line = config.readline()
        if not line:
            break
        if i == 0:
            predata = line[0:52]
            line = line.replace(predata, filename)
        newline.append(line)
        i = i + 1
    config.close()
    file = open("config.in", "w")
    for i in newline:
        file.write(i)
    file.close()

def rewrite(k, m):
    """rewrite config.in. k was the cycle number, m is one-dimensional array of fermi energy """
    newline = []
    config = open("config.in", "r+")
    i = 0
    while 1:
        line = config.readline()
        if not line:
            break
        if i == 1:
            predata = line[4:12]
            line = line.replace(predata, "%.6f"%round(m[k], 6))
            print(str(round(m[k], 6)))
        newline.append(line)
        i = i + 1
    config.close()
    file = open("config.in", "w")
    for i in newline:
        file.write(i)
    file.close()


def run(k, m, n,workdir):
    """Call the skeaf.sh to run the skeaf code and rename output file. k was the cycle number, m is one-dimensional array of fermi energy """
    cmd = "./skeaf.sh"
    # os.system(cmd)
    data = os.popen(cmd)
    print(data.read())
    newname = 'results_short ' + "%.6f"%round(m[k], 6)
    print(newname)
    print(n+newname)
    os.rename('results_short.out', newname)
    try:
        shutil.move(workdir+"/"+newname,n)
    except Exception as m:
        print(m)



d = abs(int((a - b) / c + 1))
m = np.linspace(a, b, d)
print(m.size)
workdir = os.getcwd()
for i in subdir:
    os.makedirs(workdir+"/"+i,exist_ok=True)
l=0
for i in filenames:
    rewritefilename(i)
    k = 0
    n=workdir+"/"+subdir[l]
    while k < d:
        rewrite(k, m)
        run(k, m, n, workdir)
        k = k + 1
    l=l+1

