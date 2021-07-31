bohr = 5.2917721067 * 10 ** -11
A = 10 ** -10
Atobohr = A / bohr
eVtoRy = 0.073498688455102
RytoeV = 13.605662285137
pi = 3.141592654
import os
def changel(filename, newfile):
    file = open(filename)
    new = open(newfile, "w")
    i = 0
    while 1:
        line = file.readline()
        if i == 1:#Calculate the Fermi energy levels in Ry
            a = line.split()
            b = float(a[2]) * eVtoRy
            # print(b)
            line = line.replace(a[2], "%6f" % b)
            # print(line)
        elif 7 < i < 12:#The the reciprocal lattice base vector unit is converted to Bohr and divided by 2pi.
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
workdir = os.getcwd()
datafile = [entry.path for entry in os.scandir(workdir) if not entry.name.endswith("skeaf_wannier90_to_standard_BXSF.py") and not entry.name.endswith(".py.bxsf")]
print(datafile)
datafile.sort()
print(datafile)
for i in datafile:
    name2 = i[-3:]+".bxsf"
    changel(i, name2)
