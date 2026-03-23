"""
twobandfit_constrained_withRxx.py

基于 twobandfit.py：
  - 使用零场电阻率 rho_xx(0) 作为约束条件拟合霍尔电阻率 rho_xy(B)
  - 同时加载纵向电阻率数据 rho_xx(B)，将拟合参数计算出的 rho_xx(B) 与实测对比
  - 最终生成双子图：
      左子图  : rho_xx(B)  实测数据 vs 拟合计算值
      右子图  : rho_xy(B)  原始数据 vs 拟合曲线
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, differential_evolution
from tkinter import Tk, filedialog
import os

# ===== 物理常数 =====
e_charge = 1.602176634e-19          # C

# ===== 双带模型 =====

def two_band_conductivity(B, n1, mu1, n2, mu2):
    mu1, mu2 = abs(mu1), abs(mu2)
    s_xx = (e_charge * abs(n1) * mu1 / (1 + (mu1 * B)**2)
            + e_charge * abs(n2) * mu2 / (1 + (mu2 * B)**2))
    s_xy = (e_charge * n1 * mu1**2 * B / (1 + (mu1 * B)**2)
            + e_charge * n2 * mu2**2 * B / (1 + (mu2 * B)**2))
    return s_xx, s_xy

def two_band_rho_xy(B, n1, mu1, n2, mu2):
    s_xx, s_xy = two_band_conductivity(B, n1, mu1, n2, mu2)
    return s_xy / (s_xx**2 + s_xy**2)

def two_band_rho_xx(B, n1, mu1, n2, mu2):
    s_xx, s_xy = two_band_conductivity(B, n1, mu1, n2, mu2)
    return s_xx / (s_xx**2 + s_xy**2)

def model_rho_xy(B, n1s, mu1, n2s, mu2):
    """n_scale 单位: 1e20 m^-3"""
    return two_band_rho_xy(B, n1s * 1e20, mu1, n2s * 1e20, mu2)

def model_rho_xx(B, n1s, mu1, n2s, mu2):
    return two_band_rho_xx(B, n1s * 1e20, mu1, n2s * 1e20, mu2)

# ===== 数据加载辅助函数 =====

def load_dat(filepath, col_B=0, col_rho=1):
    data = pd.read_csv(filepath, sep='\t', header=0,
                       usecols=[col_B, col_rho]).dropna()
    data = data.drop_duplicates(subset=data.columns[0])
    B   = data.iloc[:, 0].values.astype(float)
    rho = data.iloc[:, 1].values.astype(float)
    return B, rho

# ===== 主程序 =====

def main():
    root = Tk(); root.withdraw()

    print("=" * 52)
    print("  Constrained Hall Fit + rho_xx(B) Comparison  ")
    print("=" * 52)

    # --- 零场电阻率约束 ---
    rho_xx_0_input = input(
        "Enter zero-field resistivity rho_xx(0) in ohm cm "
        "(or press Enter to skip): "
    ).strip()
    if rho_xx_0_input:
        try:
            rho_xx_0_cm = float(rho_xx_0_input)
            sigma_xx_0  = 1.0 / (rho_xx_0_cm * 1e-2)
            print(f"Constraint: rho_xx(0) = {rho_xx_0_cm:.6e} ohm cm")
        except ValueError:
            print("Invalid input. Constraint disabled.")
            sigma_xx_0 = None; rho_xx_0_cm = None
    else:
        sigma_xx_0 = None; rho_xx_0_cm = None

    # --- 加载霍尔电阻率数据 (rho_xy) ---
    print("\nSelect file containing B (T) and rho_xy (ohm cm)...")
    fp_xy = filedialog.askopenfilename(
        title="Select Hall (rho_xy) data file",
        filetypes=(("Data files", "*.dat *.txt *.csv"), ("All files", "*.*"))
    )
    if not fp_xy:
        print("No file selected. Exiting."); return
    B_xy, rho_xy_cm = load_dat(fp_xy, 0, 1)
    rho_xy_m = rho_xy_cm * 1e-2
    print(f"Loaded rho_xy: {len(B_xy)} points from {fp_xy}")

    # --- 加载纵向电阻率数据 (rho_xx) 用于对比 ---
    print("Select file containing B (T) and rho_xx (ohm cm)...")
    fp_xx = filedialog.askopenfilename(
        title="Select rho_xx data file",
        filetypes=(("Data files", "*.dat *.txt *.csv"), ("All files", "*.*"))
    )
    if not fp_xx:
        print("No file selected. Exiting."); return
    B_xx, rho_xx_cm = load_dat(fp_xx, 0, 1)
    rho_xx_m = rho_xx_cm * 1e-2
    print(f"Loaded rho_xx: {len(B_xx)} points from {fp_xx}")

    # ===== 拟合 rho_xy，以 rho_xx(0) 为约束 =====

    B_data   = B_xy
    rho_data = rho_xy_m

    # --- 自动估算 p0 ---
    mask = (np.abs(B_data) > 0.3) & (np.abs(B_data) < 1.5)
    if mask.sum() > 4:
        slope = np.polyfit(B_data[mask], rho_data[mask], 1)[0]
    else:
        slope = (rho_data[-1] - rho_data[0]) / (B_data[-1] - B_data[0])
    n_guess = 1.0 / (e_charge * abs(slope))
    n_sign  = -1.0 if slope < 0 else 1.0
    n_scale = n_sign * n_guess / 1e20
    n_abs   = abs(n_scale)
    mu_guess = 0.5
    p0 = [n_sign * n_abs, mu_guess, n_sign * n_abs * 0.8, mu_guess * 0.3]
    print(f"\nAuto p0: n1_s={p0[0]:.2e}, mu1={p0[1]:.3f}, "
          f"n2_s={p0[2]:.2e}, mu2={p0[3]:.3f}")

    # --- differential_evolution 全局搜索 ---
    n_hi = max(n_abs * 1000, 1000.0)
    bounds_de = [(-n_hi, n_hi), (1e-5, 1e3),
                 (-n_hi, n_hi), (1e-5, 1e3)]

    def residual_de(params):
        try:
            n1s, mu1, n2s, mu2 = params
            pred = model_rho_xy(B_data, *params)
            err  = np.sum((pred - rho_data)**2)
            if sigma_xx_0 is not None:
                s_pred = e_charge * abs(n1s * 1e20) * mu1 + e_charge * abs(n2s * 1e20) * mu2
                w      = 100 * np.sum((rho_data - rho_data.mean())**2) / sigma_xx_0**2
                err   += w * (s_pred - sigma_xx_0)**2
            return err
        except Exception:
            return 1e30

    print("\nRunning global optimisation (differential_evolution)...")
    de_res = differential_evolution(
        residual_de, bounds_de, seed=42, maxiter=2000, tol=1e-14,
        mutation=(0.5, 1.5), recombination=0.9, popsize=15, workers=1
    )
    print(f"Global optimum found  (fun={de_res.fun:.3e})")

    # --- curve_fit 精化 ---
    print("Refining with curve_fit...")
    bounds_cf = ([-np.inf, 1e-5, -np.inf, 1e-5], [np.inf, 1e3, np.inf, 1e3])

    if sigma_xx_0 is not None:
        B_fit = np.append(B_data, 0.0)
        y_fit = np.append(rho_data, 1.0 / sigma_xx_0)

        def combined_model(Ba, n1s, mu1, n2s, mu2):
            rxy = model_rho_xy(Ba[:-1], n1s, mu1, n2s, mu2)
            sxx = e_charge * abs(n1s * 1e20) * mu1 + e_charge * abs(n2s * 1e20) * mu2
            return np.append(rxy, 1.0 / sxx)

        sigma = np.ones(len(B_fit)); sigma[-1] = 1e-8
        popt, pcov = curve_fit(
            combined_model, B_fit, y_fit,
            p0=de_res.x, bounds=bounds_cf, sigma=sigma,
            maxfev=200000, ftol=1e-14, xtol=1e-14, gtol=1e-14
        )
    else:
        popt, pcov = curve_fit(
            model_rho_xy, B_data, rho_data,
            p0=de_res.x, bounds=bounds_cf,
            maxfev=200000, ftol=1e-14, xtol=1e-14, gtol=1e-14
        )

    perr = np.sqrt(np.diag(pcov))

    # 提取参数
    n1  = popt[0] * 1e20; mu1 = popt[1]
    n2  = popt[2] * 1e20; mu2 = popt[3]
    n1_err  = perr[0] * 1e20; mu1_err = perr[1]
    n2_err  = perr[2] * 1e20; mu2_err = perr[3]

    # 计算 rho_xx(0) fitted
    sxx0 = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2
    rho_xx_0_fit_cm = 1.0 / sxx0 * 100

    # R² of Hall fit
    res_xy = rho_data - model_rho_xy(B_data, *popt)
    r2_xy  = 1 - np.sum(res_xy**2) / np.sum((rho_data - rho_data.mean())**2)

    print("\n=== Fit Results (SI Units) ===")
    print(f"Carrier 1 (n1): {n1:.4e} \u00b1 {n1_err:.4e} m^-3 "
          f"({'Hole' if n1 > 0 else 'Electron'})")
    print(f"Mobility 1 (mu1): {mu1:.4e} \u00b1 {mu1_err:.4e} m^2/(V\u00b7s)")
    print(f"Carrier 2 (n2): {n2:.4e} \u00b1 {n2_err:.4e} m^-3 "
          f"({'Hole' if n2 > 0 else 'Electron'})")
    print(f"Mobility 2 (mu2): {mu2:.4e} \u00b1 {mu2_err:.4e} m^2/(V\u00b7s)")
    if rho_xx_0_cm is not None:
        print(f"--- Constraint Check ---")
        print(f"Target  rho_xx(0) : {rho_xx_0_cm:.6e} ohm cm")
    print(f"Fitted  rho_xx(0) : {rho_xx_0_fit_cm:.6e} ohm cm")
    print(f"R\u00b2 (rho_xy fit)  : {r2_xy:.4f}\n")

    # ===== 绘图 =====
    B_smooth = np.linspace(min(B_data.min(), B_xx.min()),
                           max(B_data.max(), B_xx.max()), 600)

    # 从拟合参数计算 rho_xx(B) 曲线
    rho_xx_calc_cm = model_rho_xx(B_smooth, *popt) * 100
    # R² of rho_xx comparison
    rho_xx_calc_at_data = model_rho_xx(B_xx, *popt) * 100
    res_xx = rho_xx_cm - rho_xx_calc_at_data
    r2_xx  = 1 - np.sum(res_xx**2) / np.sum((rho_xx_cm - rho_xx_cm.mean())**2)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Two-Band Constrained Fit: Hall + Resistivity", fontsize=15, fontweight='bold')

    # --- 左子图: rho_xx ---
    ax = axes[0]
    ax.scatter(B_xx, rho_xx_cm, color='black', marker='o',
               facecolors='none', s=12, label='Measured $\\rho_{xx}$')
    ax.plot(B_smooth, rho_xx_calc_cm, 'b-', lw=2,
            label='Calc. from fit params')
    ax.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax.set_ylabel('$\\rho_{xx}$ ($\\Omega\\cdot$cm)', fontsize=13)
    ax.tick_params(labelsize=11)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, ls='--', alpha=0.5)
    ax.annotate(f'$R^2$ = {r2_xx:.4f}', xy=(0.05, 0.94),
                xycoords='axes fraction', fontsize=11,
                color='blue', va='top')

    # --- 右子图: rho_xy ---
    rho_xy_fit_smooth = model_rho_xy(B_smooth, *popt) * 100
    ax = axes[1]
    ax.scatter(B_data, rho_xy_cm, color='black', marker='o',
               facecolors='none', s=12, label='Raw $\\rho_{xy}$')
    ax.plot(B_smooth, rho_xy_fit_smooth, 'r-', lw=2, label='Two-band Fit')
    ax.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax.set_ylabel('$\\rho_{xy}$ ($\\Omega\\cdot$cm)', fontsize=13)
    ax.tick_params(labelsize=11)
    ax.legend(fontsize=11, loc='best')
    ax.grid(True, ls='--', alpha=0.5)
    ax.annotate(f'$R^2$ = {r2_xy:.4f}', xy=(0.05, 0.94),
                xycoords='axes fraction', fontsize=11,
                color='blue', va='top')

    # 参数标注 (右图)
    t1 = 'h' if n1 > 0 else 'e'
    t2 = 'h' if n2 > 0 else 'e'
    info = (
        f"Carrier 1 ({t1}): $n_1$=({n1:.2e}$\\pm${n1_err:.1e}) m$^{{-3}}$\n"
        f"  $\\mu_1$=({mu1:.3e}$\\pm${mu1_err:.1e}) m$^2$/Vs\n"
        f"Carrier 2 ({t2}): $n_2$=({n2:.2e}$\\pm${n2_err:.1e}) m$^{{-3}}$\n"
        f"  $\\mu_2$=({mu2:.3e}$\\pm${mu2_err:.1e}) m$^2$/Vs\n"
        f"Fitted $\\rho_{{xx}}(0)$={rho_xx_0_fit_cm:.4e} $\\Omega\\cdot$cm"
    )
    if rho_xx_0_cm is not None:
        info += f"\nTarget  $\\rho_{{xx}}(0)$={rho_xx_0_cm:.4e} $\\Omega\\cdot$cm"
    axes[1].annotate(info, xy=(0.03, 0.04), xycoords='axes fraction',
                     fontsize=9, color='blue', va='bottom',
                     bbox=dict(boxstyle='round,pad=0.3', fc='white',
                               ec='gray', alpha=0.8))

    plt.tight_layout()

    # ===== 导出 =====
    base_name = os.path.splitext(fp_xy)[0]
    out_dat = base_name + '_constrained_fit_result.dat'
    out_png = base_name + '_constrained_fit_plot.png'

    try:
        fit_xy_at_raw = model_rho_xy(B_data, *popt) * 100
        # rho_xx: align to rho_xx data grid
        rho_xx_calc_at_xx = model_rho_xx(B_xx, *popt) * 100
        with open(out_dat, 'w') as f:
            f.write("# Two-Band Constrained Fit (Hall) + rho_xx Comparison\n")
            f.write(f"# rho_xy file: {fp_xy}\n")
            f.write(f"# rho_xx file: {fp_xx}\n")
            if rho_xx_0_cm is not None:
                f.write(f"# Constraint rho_xx(0) = {rho_xx_0_cm:.8e} ohm cm\n")
            f.write(f"# Fitted  rho_xx(0) = {rho_xx_0_fit_cm:.8e} ohm cm\n")
            f.write(f"# R2(rho_xy fit)={r2_xy:.6f}  R2(rho_xx compare)={r2_xx:.6f}\n")
            f.write("# --- Parameters ---\n")
            f.write(f"# n1 (m^-3) = {n1:.6e} +/- {n1_err:.6e} "
                    f"({'Hole' if n1 > 0 else 'Electron'})\n")
            f.write(f"# mu1 (m^2/Vs) = {mu1:.6e} +/- {mu1_err:.6e}\n")
            f.write(f"# n2 (m^-3) = {n2:.6e} +/- {n2_err:.6e} "
                    f"({'Hole' if n2 > 0 else 'Electron'})\n")
            f.write(f"# mu2 (m^2/Vs) = {mu2:.6e} +/- {mu2_err:.6e}\n")
            f.write("# ------------------\n")
            f.write("# [Hall data @ Hall B grid]\n")
            f.write("# B(T)\trho_xy_raw(ohm_cm)\trho_xy_fit(ohm_cm)\n")
            for i in range(len(B_data)):
                f.write(f"{B_data[i]:.6f}\t{rho_xy_cm[i]:.6e}\t{fit_xy_at_raw[i]:.6e}\n")
            f.write("# [rho_xx data @ rho_xx B grid]\n")
            f.write("# B(T)\trho_xx_raw(ohm_cm)\trho_xx_calc(ohm_cm)\n")
            for i in range(len(B_xx)):
                f.write(f"{B_xx[i]:.6f}\t{rho_xx_cm[i]:.6e}\t{rho_xx_calc_at_xx[i]:.6e}\n")
        print(f"=> Fit data exported: {out_dat}")
    except Exception as e:
        print(f"Warning: export failed. ({e})")

    try:
        plt.savefig(out_png, dpi=300, bbox_inches='tight')
        print(f"=> Plot saved: {out_png}")
    except Exception as e:
        print(f"Warning: plot save failed. ({e})")

    plt.show()


if __name__ == "__main__":
    main()
