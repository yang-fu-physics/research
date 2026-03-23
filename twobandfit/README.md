# Two-Band Model Fitting Suite / 双带模型拟合工具包

*[English version below]*

本工作目录包含一组用于半导体双带模型（电子-空穴 或 双电子/双空穴）传输属性拟合分析的 Python 程序。

## 包含的程序功能说明

### 1. `twobandfit.py`
基础版双带拟合增强程序：带纵向电阻率（$\rho_{xx}$）辅助验证。
- **输入**：包含磁场 $B$ (T) 和霍尔电阻率 $\rho_{xy}$ (ohm cm) 的测量数据。并可选输入额外的 $\rho_{xx}$ 实验数据用于对比。
- **特性**：可选输入零场电阻率 $\rho_{xx}(0)$ 作为物理约束；当提供了额外的 $\rho_{xx}$ 数据文件时，会在拟合得出双带参数后反向映射预测 $\rho_{xx}(B)$ 曲线。
- **输出**：四参数解 ($n_1, \mu_1, n_2, \mu_2$)，若仅载入霍尔数据则生成单图，若含有对比数据则生成对比双子图。结果支持文本文件导出。

### 3. `twobandfit_joint.py`
终极免约束的**双通道联合自适应全局拟合**程序。
- **输入**：同时分别调入 $\rho_{xx}(B)$ 与 $\rho_{xy}(B)$ 两套实验数据。程序在底层会自动插值配准两者非结构化或长度不一的磁场。
- **特性**：无需用户手动输入计算后的零场电阻数值作为锚点。程序直接通过对两大张量信号流使用“差分进化”全局探测算法（Differential Evolution），一次性找出同时匹配纵向磁阻弯曲形态与霍尔反常交叉的公域最优组合解。
- **输出**：最完整的分析报表（整合版五列结果文件）和包含各通道独立关联度 $R^2$ 的并拢拟合双子图。

## 测试与校验数据集
目录内的 `test_data.dat` 是一套携带人为高斯环境白噪声的纯合成标准参照集单元，用于确保分析程序内核能够在含错扰动下自持验证推导；而您可以将真实的实验数据仅用作本地化科研使用。

## 算法简述
三款拟合器均底层驱动了双阶梯调优架构：先用 SciPy `differential_evolution` 基于广域物理特征点粗定位进行抗局域驻点的全局空间嗅探，再交由 `curve_fit` 沿阻抗雅可比矩阵降维收敛到极值，进而支持电子与空穴任何组合参量的无人值守发掘。

---

# (English Version) Two-Band Model Fitting Suite

This folder contains a suite of Python programs designed for analyzing longitudinal and Hall resistivity data using a two-band (electron-hole or electron-electron) semiconductor transport model.

## Programs Included

### 1. `twobandfit.py`
The base program for fitting Hall resistivity ($\rho_{xy}$ vs *B*) to the two-band model.
- **Input**: A data file containing at least Magnetic Field (T) and Hall resistivity $\rho_{xy}$ (ohm cm).
- **Features**: Asks for an optional zero-field longitudinal resistivity Constraint ($\rho_{xx}(0)$) to regularize the fit.
- **Output**: Fitted subset of parameters ($n_1, \mu_1, n_2, \mu_2$), an R-squared value, an exported coordinate file, and a fitted comparison plot.

### 2. `twobandfit_constrained_withRxx.py`
An extended version of the base program that also processes longitudinal resistivity.
- **Input**: User selects sequentially the Hall resistivity $\rho_{xy}$ (e.g., `hall-2.0K.dat`) AND the longitudinal resistivity $\rho_{xx}$ (e.g., `R-2.0K.dat`).
- **Features**: Fits the Hall data under a $\rho_{xx}(0)$ constraint, and visually uses these fitted parameters to calculate the expected $\rho_{xx}(B)$ dependency.
- **Output**: A dual-panel figure allowing the user to compare the raw measurements against the model's simulated expectations for both $\rho_{xy}$ and $\rho_{xx}$.

### 3. `twobandfit_joint.py`
The ultimate joint-fitting tool that considers both data modes simultaneously.
- **Input**: Loads $\rho_{xx}(B)$ and $\rho_{xy}(B)$ files and dynamically interpolates their field scales for alignment. 
- **Features**: Performs a global joint optimization (differential evolution) matching the dual-channel signals. It does *not* demand a manual $\rho_{xx}(0)$ constraint anymore.
- **Output**: Best-fit globally unified parameter set, dual correlation profiles $R^2$, paired dataset file, and a dual-panel fit plot overlay.

## Algorithm Notice
All three tools apply a two-step refinement architecture comprising SciPy's `differential_evolution` algorithms mapped over to `curve_fit`, allowing fully unsupervised bounding (spanning both unipolar + bipolar electron-hole architectures).
