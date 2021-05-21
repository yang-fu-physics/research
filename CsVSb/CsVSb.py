import math

import numpy as np

pi = 3.141592654
A = 10475.764126557
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
    print(r * r * pi * A)


def runa(a, b):
    """k坐标未乘2pi计算频率大小"""
    a = a * 2 * pi
    # print(a)
    b = b * 2 * pi
    # print(b)
    r = (a - b) / 2
    print(r * r * pi * A)


def runb(a, b, c):
    """k坐标未乘2pi,椭圆计算频率大小"""
    a = a * 2 * pi
    # print(a)
    b = b * 2 * pi
    # print(b)
    c = c * 2 * pi
    print((c - a) * (b - c) * pi * A)


def rund(a, c):
    """k点未乘2pi，圆形，c-a为半径计算频率大小"""
    r = (c - a) * 2 * pi
    print(r * r * pi * A)


def runc(a):
    """反解界面大小，或对应的倒空间长度"""
    b = math.sqrt(a / (A * pi))
    print(a / A)
    print(b / (2 * pi) * 2)


def area(a):
    a = 1 / (a * math.sqrt(3) / 2)  # 倒空间轴长
    """六方的面积，a为是实空间轴长"""
    a = a * 2 * pi
    # print(a)
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


print((0.45 / 0.51 * 0.85440055) ** 2 * pi * A)

