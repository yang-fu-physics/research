import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

# 创建一个带有噪声的线性数据集
x = np.linspace(0, 10, 100)
y = 2.0 * x + 1.0 + 2.0 * np.random.randn(len(x))

# 定义拟合函数
def linear_func(x, a, b):
    return a * x + b

# 使用 curve_fit 进行拟合
popt, pcov = curve_fit(linear_func, x, y)

# 计算置信区间
perr = np.sqrt(np.diag(pcov))
t_value = 2.0 # 使用 95% 的置信度
ci = t_value * perr

# 打印拟合参数和置信区间
print('a:', popt[0], '+/-', ci[0])
print('b:', popt[1], '+/-', ci[1])
for i in popt:
    print(i)
# 绘制数据集和拟合函数
plt.scatter(x, y)
plt.plot(x, linear_func(x, *popt), 'r-', label='fit')
plt.legend()
plt.show()