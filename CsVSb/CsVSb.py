import math
import numpy as np
eVtoRy = 0.073498688455102
RytoeV = 13.605662285137
pi = 3.141592654
Af = 10475.764126557
h = 6.62607004 * 10 ** -34
e = 1.60217733 * 10 ** -19
me = 9.10938356 * 10 ** -30
def caltan(r,num):
    r=r*2*pi*2
    print(r)
    c=1/9.315*2*pi
    tan = np.zeros(num)
    num=np.linspace(1,num,num)
    for i in num:
        nc=i*c
        tan[int(i-1)]=math.atan(nc/r)/pi*180
    return tan


def run(a, b):
    """k坐标乘过2pi计算频率大小"""
    r = (a - b) / 2
    print(r * r * pi * Af)


def runa(a, b):
    """k坐标未乘2pi计算频率大小"""
    a = a * 2 * pi
    # print(a)
    b = b * 2 * pi
    # print(b)
    r = (a - b) / 2
    print(r * r * pi * Af)


def runb(a, b, c):
    """k坐标未乘2pi,椭圆计算频率大小"""
    a = a * 2 * pi
    # print(a)
    b = b * 2 * pi
    # print(b)
    c = c * 2 * pi
    print((c - a) * (b - c) * pi * Af)


def rund(a, c):
    """k点未乘2pi，圆形，c-a为半径计算频率大小"""
    r = (c - a) * 2 * pi
    print(r * r * pi * Af)


def runc(a):
    """反解界面大小，或对应的倒空间长度"""
    b = math.sqrt(a / (Af * pi))
    print(a / Af)
    print(b)#半径乘过2pi
    print(b / (2 * pi) * 2)#直径未乘2pi


def area(a):
    a = 1 / (a * math.sqrt(3) / 2)  # 倒空间轴长
    """六方的面积，a为是实空间轴长"""
    a = a * 2 * pi
    #print(a)
    s = a ** 2 * math.sqrt(3) / 2
    # print(V)
    return s


def calpre(a):
    """计算面积占比"""
    return a / area(5.50552)


def vf(Af, m):
    """计算费米速度"""
    vf = h / (2 * pi) * math.sqrt(Af / pi) * (10 ** 10) / (me * m)
    return vf



print(vf(0.00258, 0.13003), vf(0.00697, 0.12829), vf(0.06940, 0.54010), vf(0.07503, 0.60574))


print((0.45 / 0.51 * 0.85440055) ** 2 * pi * Af)
print("------")
print(runc(13000))
print(0.0038*RytoeV)
print(0.2*eVtoRy)
print(0.0147*RytoeV)
print(0.1884 * 0.1884 * pi * Af)
print(area(5.50552)/6939*306*Af)
print(area(5.50552)/6939*463*Af)
print(area(5.50552)/6939*44*Af)
print(area(5.50552)/109232*533*Af)
print(area(5.50552)/((0.5/133)**2*6939))
print((0.5/133)**2*6728*Af)
axing=(1/(5.5052*math.sqrt(3)/2))*2*pi
print(area(5.50552))
print(axing**2/2*math.sqrt(3))
print(axing)
sperp=(0.5/133)**2
print(sperp*533*Af)
print(sperp*4330*Af)
print(sperp*6737*Af)
print(sperp*4878*Af)
print(sperp*5000*Af)
print(sperp*7339*Af)
print(sperp*647*Af)
print(sperp*512*Af)
print(sperp*4831*Af)
print(sperp*6875*Af)
print(sperp*155*Af)
print(sperp*489*Af)
print(sperp*5708*Af)

print(sperp*465*Af)

print(sperp*4384*Af)
print(sperp*5085*Af)
print(sperp*3806*Af)
print(sperp*533*Af)
print(sperp*212*Af)
print(sperp*236*Af)
print(sperp*489*Af)
print(sperp*533*Af)
print(sperp*780*Af)
print(sperp*824*Af)
print(sperp*6480*Af)
print(sperp*6638*Af)
print(sperp*5565*Af)
print(sperp*5718*Af)
print(sperp*7751*Af)
print(sperp*7939*Af)
print(-0.0333/RytoeV)
print(sperp*2078*3*Af)
print(sperp*4352*Af)
print(sperp*4234*Af)
print(sperp*3514*Af)
print(sperp*3637*Af)
print(sperp*5044*Af)
print(sperp*5205*Af)
print(sperp*200*Af)
print(sperp*339*Af)

