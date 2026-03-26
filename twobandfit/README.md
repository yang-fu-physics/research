# Two-Band Model Fitting Suite / 双带模型拟合工具包

*[English version below]*

本工作目录包含用于磁输运数据的双带模型（电子-空穴或双载流子）拟合分析的 Python 程序套件。

## 程序说明

### `twobandfit.py`
**单次拟合**（交互式，含 GUI 文件选择对话框）。

- **输入**：
  - 霍尔电阻率数据文件（B (T)、$\rho_{xy}$ (ohm cm)）
  - （可选）手动输入零场纵向电阻率 $\rho_{xx}(0)$ 作为物理约束
  - （可选）额外的 $\rho_{xx}(B)$ 数据文件用于对比验证
- **特性**：
  - 当零场约束未手动提供但加载了 $\rho_{xx}$ 数据时，自动从数据中提取零场约束值
  - 双阶段优化：`differential_evolution` 全局搜索 + `L-BFGS-B` 局部精化
  - 通过数值 Hessian 矩阵估算参数误差（标准差）
- **输出**：拟合参数 ($n_1, \mu_1, n_2, \mu_2$) 及误差，R²，导出 `.dat` 文件，以及单图或双子图（有无 $\rho_{xx}$ 对比）

### `twobandfit_batch.py`
**批量拟合**（命令行，无需交互）。

- **输入**：自动扫描指定文件夹中配对的 `R-{T}K.dat`（纵向）与 `hall-{T}K.dat`（霍尔）文件
- **特性**：
  - 自动从 $\rho_{xx}$ 数据中提取零场约束（B 最近零场点处的电阻率）
  - 对每个温度独立执行与 `twobandfit.py` 相同的优化流程
  - 输出每个温度的结果文件和图 + 汇总表和汇总图
- **用法**：
  ```bash
  python twobandfit_batch.py                    # 默认扫描 rawdata/ 文件夹
  python twobandfit_batch.py path/to/data_dir   # 指定文件夹
  ```
- **输出**：`results/` 子目录，包含各温度的 `{T}_fit_result.dat`、`{T}_fit_plot.png`，以及 `batch_summary.dat` 和 `batch_summary_plot.png`

### `twobandfit_sigma.py`
**电导率域单次拟合**（交互式，含 GUI 文件选择对话框）。

- **输入**：$\rho_{xx}(B)$ 和 $\rho_{yx}(B)$ 数据文件（ohm cm）
- **特性**：
  - 将电阻率张量反演为电导率张量：$\sigma_{xx}$, $\sigma_{xy}$
  - 拟合 $\sigma_{xy}(B)$，以 $\sigma_{xx}(0)$ 作为软约束
  - 自动从 $\rho_{xx}$ 数据中提取零场约束值
  - 动态均匀重采样（基于最小相邻点间距），统一双数据集的 B 网格
- **输出**：拟合参数及误差，$\sigma_{xy}$ 拟合图 + $\sigma_{xx}$ 对比图

### `twobandfit_sigma_joint.py`
**电导率域联合拟合**（同时拟合 $\sigma_{xx}(B)$ 和 $\sigma_{xy}(B)$）。

- **输入**：与 `twobandfit_sigma.py` 相同
- **特性**：
  - 同时最小化 $\sigma_{xx}$ 和 $\sigma_{xy}$ 的残差，使用方差倒数权重平衡两个数据集
  - 无需额外的 $\sigma_{xx}(0)$ 软约束（因 $\sigma_{xx}$ 本身已被拟合）
- **输出**：$\sigma_{xx}$ 和 $\sigma_{xy}$ 双子图，分别标注 R²

### `twobandfit_sigma_range.py`
**电导率域限定磁场范围拟合**（$\sigma_{xy}$ 拟合 + $\sigma_{xx}(0)$ 约束）。

- 从 `twobandfit_sigma.py` 导入核心逻辑
- 将拟合范围限制在用户指定的 $|B|$ 区间（默认 2.5–9.0 T），避免低场异常
- 同时显示全范围外推的 R² 作为参考

### `twobandfit_sigma_joint_range.py`
**电导率域限定范围联合拟合**（同时拟合 $\sigma_{xx}$ 和 $\sigma_{xy}$）。

- 从 `twobandfit_sigma_joint.py` 导入核心逻辑
- 将联合拟合范围限制在用户指定的 $|B|$ 区间（默认 2.5–9.0 T）
- 同时显示全范围外推的 R²

### `twobandfit_sigma_batch.py`
**电导率域批量拟合**（命令行，无需交互）。

- **输入**：自动扫描指定文件夹中配对的 `R-{T}K.dat` 与 `hall-{T}K.dat` 文件
- **特性**：
  - 将 $\rho_{xx}$/$\rho_{yx}$ 转换为 $\sigma_{xx}$/$\sigma_{xy}$，然后同时拟合两者（联合模式）
  - 对每个温度独立执行优化并导出结果
- **用法**：
  ```bash
  python twobandfit_sigma_batch.py                    # 默认扫描 rawdata/ 文件夹
  python twobandfit_sigma_batch.py path/to/data_dir   # 指定文件夹
  ```
- **输出**：`results_sigma/` 子目录，包含各温度结果及 `batch_sigma_summary.dat` 和 `batch_sigma_summary_plot.png`

## 算法概述

### 电阻率域（`twobandfit.py` / `twobandfit_batch.py`）

共用 `twobandfit.py` 中的 `fit_two_band()` 核心函数：

1. **初始猜值**：从数据线性斜率估算载流子浓度初始值
2. **全局搜索**：`scipy.optimize.differential_evolution`，支持正负载流子（电子/空穴任意组合）
3. **局部精化**：`scipy.optimize.minimize`（L-BFGS-B），精确收敛至最优点
4. **约束方式**：$\rho_{xx}(0)$ 以动态加权软惩罚项形式加入目标函数
5. **误差估算**：对目标函数在最优点处计算数值 Hessian，取逆乘以残差方差得到协方差矩阵，对角元开方即为参数标准误差

### 电导率域（`twobandfit_sigma*.py` 系列）

在电导率空间进行拟合。核心流程与电阻率域一致，额外步骤为：

1. **张量反演**：$\sigma_{xx} = \rho_{xx}/(\rho_{xx}^2+\rho_{yx}^2)$，$\sigma_{xy} = \rho_{yx}/(\rho_{xx}^2+\rho_{yx}^2)$
2. **均匀重采样**：将两组不同 B 网格的数据统一到公共均匀网格（基于最小相邻点间距）
3. **拟合模式**：
   - `sigma` 模式：仅拟合 $\sigma_{xy}(B)$，$\sigma_{xx}(0)$ 作软约束
   - `joint` 模式：同时拟合 $\sigma_{xx}(B)$ 和 $\sigma_{xy}(B)$，方差倒数权重平衡
   - `range` 变体：限定 $|B|$ 范围拟合，避免低场异常

## 数据文件格式

输入数据文件需为制表符分隔的文本（`.dat`），第一列为磁场 B (T)，第二列为电阻率 (ohm cm)，首行为标题行：

```
B(T)	rho(ohm cm)
-9.0	-0.00312
...
```

---

# (English Version) Two-Band Model Fitting Suite

This folder contains Python programs for fitting longitudinal and Hall resistivity data to the two-carrier (two-band) transport model.

## Programs

### `twobandfit.py`
**Interactive single-run fitting** (GUI file dialogs).

- **Input**:
  - Hall resistivity file (B in T, $\rho_{xy}$ in ohm cm)
  - (Optional) Manual entry of zero-field $\rho_{xx}(0)$ constraint
  - (Optional) Longitudinal resistivity file for visual comparison
- **Features**:
  - Auto-extracts $\rho_{xx}(0)$ constraint from loaded $\rho_{xx}$ data if not entered manually
  - Two-stage optimization: global `differential_evolution` + local `L-BFGS-B` refinement
  - Parameter uncertainties estimated via numerical Hessian inversion
- **Output**: Fitted parameters ($n_1, \mu_1, n_2, \mu_2$) with errors, R², exported `.dat`, and fit plot (single or dual-panel)

### `twobandfit_batch.py`
**Automated batch fitting** (command-line, no interaction required).

- **Input**: Automatically discovers paired `R-{T}K.dat` and `hall-{T}K.dat` files in the data folder
- **Features**:
  - Auto-extracts zero-field $\rho_{xx}(0)$ constraint from the $\rho_{xx}$ data
  - Runs the same optimization pipeline as `twobandfit.py` for each temperature
- **Usage**:
  ```bash
  python twobandfit_batch.py                    # scan default rawdata/ folder
  python twobandfit_batch.py path/to/data_dir   # specify folder
  ```
- **Output**: A `results/` subdirectory containing per-temperature `{T}_fit_result.dat`, `{T}_fit_plot.png`, and a combined `batch_summary.dat` and `batch_summary_plot.png`

### `twobandfit_sigma.py`
**Single-run conductivity-domain fitting** (interactive GUI).

- **Input**: $\rho_{xx}(B)$ and $\rho_{yx}(B)$ data files (ohm cm)
- **Features**:
  - Inverts the resistivity tensor to conductivity: $\sigma_{xx}$, $\sigma_{xy}$
  - Fits $\sigma_{xy}(B)$ with $\sigma_{xx}(0)$ as a soft constraint
  - Auto-extracts zero-field constraint from $\rho_{xx}$ data
  - Dynamic uniform resampling (based on minimum adjacent-point spacing) to unify B grids
- **Output**: Fitted parameters with errors, $\sigma_{xy}$ fit plot + $\sigma_{xx}$ comparison plot

### `twobandfit_sigma_joint.py`
**Joint conductivity-domain fitting** (fits both $\sigma_{xx}(B)$ and $\sigma_{xy}(B)$ simultaneously).

- **Input**: Same as `twobandfit_sigma.py`
- **Features**:
  - Jointly minimizes residuals for both $\sigma_{xx}$ and $\sigma_{xy}$, balanced by inverse-variance weights
  - No separate $\sigma_{xx}(0)$ soft constraint needed (since $\sigma_{xx}$ is directly fitted)
- **Output**: Dual-panel plot with R² for both $\sigma_{xx}$ and $\sigma_{xy}$

### `twobandfit_sigma_range.py`
**Range-restricted conductivity fitting** ($\sigma_{xy}$ fit + $\sigma_{xx}(0)$ constraint).

- Imports core logic from `twobandfit_sigma.py`
- Restricts the fitting range to a user-specified $|B|$ window (default 2.5–9.0 T) to avoid low-field anomalies
- Reports full-range extrapolated R² for reference

### `twobandfit_sigma_joint_range.py`
**Range-restricted joint conductivity fitting** (fits both $\sigma_{xx}$ and $\sigma_{xy}$).

- Imports core logic from `twobandfit_sigma_joint.py`
- Restricts the joint fitting range to a user-specified $|B|$ window (default 2.5–9.0 T)
- Reports full-range extrapolated R² for reference

### `twobandfit_sigma_batch.py`
**Batch conductivity-domain fitting** (command-line, no interaction).

- **Input**: Automatically discovers paired `R-{T}K.dat` and `hall-{T}K.dat` files
- **Features**:
  - Converts $\rho_{xx}$/$\rho_{yx}$ to $\sigma_{xx}$/$\sigma_{xy}$, then fits both simultaneously (joint mode)
  - Runs independent optimization for each temperature
- **Usage**:
  ```bash
  python twobandfit_sigma_batch.py                    # scan default rawdata/ folder
  python twobandfit_sigma_batch.py path/to/data_dir   # specify folder
  ```
- **Output**: A `results_sigma/` subdirectory containing per-temperature results and `batch_sigma_summary.dat` + `batch_sigma_summary_plot.png`

## Algorithm

### Resistivity Domain (`twobandfit.py` / `twobandfit_batch.py`)

Both programs share the `fit_two_band()` core in `twobandfit.py`:

1. **Initial guess**: Carrier density estimated from the Hall slope in the low-field region
2. **Global search**: `scipy.optimize.differential_evolution`, supports any electron/hole combination
3. **Local refinement**: `scipy.optimize.minimize` (L-BFGS-B) for precise convergence
4. **Constraint**: $\rho_{xx}(0)$ enforced as a dynamically-weighted soft penalty term
5. **Error estimation**: Numerical Hessian of the objective at the optimum is inverted and scaled by the residual variance to yield the parameter covariance matrix; standard errors are $\sqrt{\text{diag}(C)}$

### Conductivity Domain (`twobandfit_sigma*.py` family)

Fitting is performed in conductivity space. The core pipeline is the same, with additional steps:

1. **Tensor inversion**: $\sigma_{xx} = \rho_{xx}/(\rho_{xx}^2+\rho_{yx}^2)$, $\sigma_{xy} = \rho_{yx}/(\rho_{xx}^2+\rho_{yx}^2)$
2. **Uniform resampling**: Merges two datasets with different B grids onto a common uniform grid (based on minimum adjacent-point spacing)
3. **Fitting modes**:
   - `sigma` mode: Fits $\sigma_{xy}(B)$ only, with $\sigma_{xx}(0)$ as a soft constraint
   - `joint` mode: Fits both $\sigma_{xx}(B)$ and $\sigma_{xy}(B)$ simultaneously, balanced by inverse-variance weights
   - `range` variants: Restricts $|B|$ range to avoid low-field anomalies

## Data File Format

Tab-separated text (`.dat`) with a header row; column 0 = B (T), column 1 = resistivity (ohm cm):

```
B(T)	rho(ohm cm)
-9.0	-0.00312
...
```
