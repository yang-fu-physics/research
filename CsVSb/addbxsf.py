import os
workdir=os.getcwd()
def main():
    m=0
    datafile = [entry.path for entry in os.scandir(workdir) if
                entry.name.endswith(".bxsf")]
    l=len(datafile)
    datafile.sort()
    allfile = open("all.bxsf", "w")
    for i in datafile:
        j = 0
        data=open(i)
        while True:
            line=data.readline()
            if line==" END_BANDGRID_3D\n":
                break
            if line==" 1\n":
                line=" %i\n"%l
            if j<12 and m!=0:
                pass
            else:
                allfile.write(line)
            j=j+1
        m=m+1
        data.close()
    allfile.write(" END_BANDGRID_3D\n END_BLOCK_BANDGRID_3D")
    allfile.close()
main()