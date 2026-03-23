from uncertainties import ufloat
from uncertainties.umath import *
eVtoRy = 0.073498688455102#能量单位eV到Ry
RytoeV = 13.605662285137#能量单位Ry到eV
pi = 3.141592654
Af = 10475.764126557#计算频率到费米面大小
h = 6.62607004 * 10 ** -34#普朗克长度
e = 1.60217733 * 10 ** -19#电子电荷
me = 9.10938356 * 10 ** -30#电子质量
R=8.31446261815324 #气体常数
L0=2.44*10**-8#热导洛伦兹数
bohr = 5.2917721067 * 10 ** -11 #波尔长度
Kb_ev_unit=ufloat(8.617343*10**-5,0.000015*10**-5)
Kb_j_unit=1.380649*10**-23
Kb_erg_unit=1.380649*10**-16 #玻尔滋曼常数 erg/K
NA=6.02214076*10**23
miuB=9.2740100783*10**-24 #玻尔磁子 J/K
miuB_erg_unit=9.2740100783*10**-21 #玻尔磁子 erg/G

#从beta计算德拜温度
def debai_ca(beta,N):
    return (12*pi**4*N*R/5/beta)**(1/3)
n=5
beta=ufloat(0.002426,0.000014)
print(debai_ca(beta,n))
#debai/50才能观察到较好的三次型
#MR的rho
#普通激活能
xielv=ufloat(2331.77067,0.76175)
print(xielv*Kb_ev_unit)
#极小激活能
xielv2=ufloat(2517.09216,2.45494)
print(xielv2*Kb_ev_unit)
#单独的rho
#普通激活能
xielv3=ufloat(2676.33654,2.05336)
print(xielv3*Kb_ev_unit)
xielv4=ufloat(2888.24904,1.31496)
print(xielv4*Kb_ev_unit)
def lamuda_e_ph(debai, Tc):
    miu=0.13
    lamuda = (1.04 + (miu * log(debai / (1.45 * Tc)))) / ((1 - 0.62 * miu) * log(debai / (1.45 * Tc)) - 1.04)
    print("\n")
    print(debai)
    print(Tc)
    return lamuda

def CWfit(solp,cut):
    C=1/solp
    xita=-cut/solp
    print("cwfit")
    print(C)
    print(xita)
    miueff=(3*Kb_erg_unit*C/(NA*(miuB_erg_unit)**2))**0.5
    return miueff, xita
cut=ufloat(-19.21776,0.058)#c-1(emu-1 mol Oe)
solp=ufloat(0.73047,3.11718*10**-4)#c-1(emu-1 mol Oe)/K
print(CWfit(solp,cut))
