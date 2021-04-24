import os
import numpy as np


def rewrite(k, m):
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
    cmd = "./skeaf.sh"
    # os.system(cmd)
    data = os.popen(cmd)
    print(data.read())
    newname = 'results_short ' + str(round(m[k], 6))
    os.rename('results_short.out', newname)


a = 6.630901
b = 6.630900
c = 0.000001
d = int((a - b) / c + 1)
m = np.linspace(a, b, d)
print(m.size)
k = 0
while k < d:
    rewrite(k, m)
    run(k, m)
    k = k + 1
