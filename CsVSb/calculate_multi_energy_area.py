import os
import numpy as np


def rewrite(k, m):
    """rewrite config.in. k was the cycle number, m is one-dimensional array of fermi energy """
    newline = []
    config = open("../config.in", "r+")
    i = 0
    while 1:
        line = config.readline()
        if not line:
            break
        if i == 1:
            predata = line[4:12]
            line = line.replace(predata, str(round(m[k], 6)))
            print(str(round(m[k], 6)))
        newline.append(line)
        i = i + 1
    config.close()
    file = open("../config.in", "w")
    for i in newline:
        file.write(i)
    file.close()


def run(k, m):
    """Call the skeaf.sh to run the skeaf code and rename output file. k was the cycle number, m is one-dimensional array of fermi energy """
    cmd = "./skeaf.sh"
    # os.system(cmd)
    data = os.popen(cmd)
    print(data.read())
    newname = 'results_short ' + str(round(m[k], 6))
    os.rename('results_short.out', newname)


a = input("input max energy\n")
b = input("input min energy\n")
c = input("input interval\n")
d = int((a - b) / c + 1)
m = np.linspace(a, b, d)
print(m.size)
k = 0
while k < d:
    rewrite(k, m)
    run(k, m)
    k = k + 1
