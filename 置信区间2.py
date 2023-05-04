from scipy.stats import linregress
import statsmodels.api as sm
import numpy as np

# 生成一些随机数据
x = np.arange(10)
y = 2*x + 1 + np.random.normal(size=10)

# 使用linregress进行线性回归拟合
slope, intercept, r_value, p_value, std_error = linregress(x, y)

# 使用OLS类对象的conf_int()方法获得置信区间
model = sm.OLS(y, sm.add_constant(x))
result = model.fit()
conf_int = result.conf_int()

print("Slope: {:.4f}".format(slope))
print("Intercept: {:.4f}".format(intercept))
print("95% Confidence Interval for slope: {:.4f} - {:.4f}".format(conf_int[1][0], conf_int[1][1]))
print("95% Confidence Interval for intercept: {:.4f} - {:.4f}".format(conf_int[0][0], conf_int[0][1]))