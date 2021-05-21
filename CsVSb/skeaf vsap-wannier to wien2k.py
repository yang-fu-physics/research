bohr = 5.2917721067 * 10 ** -11
A = 10 ** -10
Atobohr = A / bohr
eVtoRy = 0.073498688455102
RytoeV = 13.605662285137
pi = 3.141592654

print(1/eVtoRy)

def caludelta(a):
    return a - 0.490288


def caluRytoeV(a):
    print(caludelta(a))
    return (a - 0.490288) * RytoeV

def changel(filename, newfile):
    file = open(filename)
    new = open(newfile, "w")
    i = 0
    while 1:
        line = file.readline()
        if i == 1:
            a = line.split()
            b = float(a[2]) * eVtoRy
            # print(b)
            line = line.replace(a[2], "%6f" % b)
            # print(line)
        elif 7 < i < 12:
            a = line.split()
            newdata = ""
            for j in a:
                # print(j)
                j = float(j)
                j = j / (Atobohr * 2 * pi)
                newdata = newdata + "      " + "%.8f" % j
            else:
                newdata = newdata + "\n"
            line = newdata
        elif line == " END_BANDGRID_3D\n":
            line = line
        elif line == " END_BLOCK_BANDGRID_3D\n":
            new.write(line)
            file.close()
            new.close()
            break
        elif 12 < i:
            a = line.split()
            newdata = ""
            for j in a:
                j = float(j)
                # print(j)
                j = j * eVtoRy
                newdata = newdata + " " + "%e" % j
            else:
                newdata = newdata + "\n"
            line = newdata
        new.write(line)
        i = i + 1

# def changeE:
# name = input("输入原始文件名")
# name2 = name + "-r"
# changel(name, name2)
