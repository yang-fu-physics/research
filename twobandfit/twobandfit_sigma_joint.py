"""
twobandfit_sigma_joint.py

Two-band joint conductivity fitting program.
- Input : measured rho_xx (ohm cm) and rho_xy (ohm cm) vs B
- Converts inputs to conductivity: sigma_xx(B) and sigma_xy(B)
- Fits BOTH sigma_xx(B) and sigma_xy(B) simultaneously
  (analogous to twobandfit_joint.py which fits rho_xx + rho_xy jointly)
- Output : fitted carrier concentrations & mobilities, both conductivity fit plots

The two-band conductivity model:
    sigma_xx(B) = e|n1|mu1/(1+(mu1 B)^2) + e|n2|mu2/(1+(mu2 B)^2)
    sigma_xy(B) = e n1 mu1^2 B/(1+(mu1 B)^2) + e n2 mu2^2 B/(1+(mu2 B)^2)

Inversion from measured resistivity:
    sigma_xx =  rho_xx / (rho_xx^2 + rho_xy^2)
    sigma_xy = -rho_xy / (rho_xx^2 + rho_xy^2)

Usage:
    python twobandfit_sigma_joint.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution, minimize, approx_fprime
from tkinter import Tk, filedialog
import os

# ===== Physical Constants =====
e_charge = 1.602176634e-19  # Elementary charge in C

# ===== Two-Band Model =====

def two_band_sigma(B, n1, mu1, n2, mu2):
    mu1, mu2 = abs(mu1), abs(mu2)
    s_xx = (e_charge * abs(n1) * mu1 / (1 + (mu1 * B)**2)
            + e_charge * abs(n2) * mu2 / (1 + (mu2 * B)**2))
    s_xy = (e_charge * n1 * mu1**2 * B / (1 + (mu1 * B)**2)
            + e_charge * n2 * mu2**2 * B / (1 + (mu2 * B)**2))
    return s_xx, s_xy

def model_sigma_xx(B, n1s, mu1, n2s, mu2):
    """n in units of 1e20 m^-3"""
    s_xx, _ = two_band_sigma(B, n1s * 1e20, mu1, n2s * 1e20, mu2)
    return s_xx

def model_sigma_xy(B, n1s, mu1, n2s, mu2):
    """n in units of 1e20 m^-3"""
    _, s_xy = two_band_sigma(B, n1s * 1e20, mu1, n2s * 1e20, mu2)
    return s_xy

# ===== Resistivity -> Conductivity =====

def rho_to_sigma(rho_xx, rho_xy):
    """Convert resistivity tensor to conductivity tensor (SI ohm m -> S/m)."""
    denom = rho_xx**2 + rho_xy**2
    return rho_xx / denom, rho_xy / denom

# ===== Data Loading =====

def load_dat(filepath, col_B=0, col_rho=1):
    data = pd.read_csv(filepath, sep='\t', header=0,
                       usecols=[col_B, col_rho]).dropna()
    data = data.drop_duplicates(subset=data.columns[0])
    B   = data.iloc[:, 0].values.astype(float)
    rho = data.iloc[:, 1].values.astype(float)
    return B, rho

# ===== Uniform Resampling =====

def resample_uniform(*arrays_B_and_data):
    """
    Resample one or more (B, data) pairs onto a common uniform B grid.

    The number of grid points is determined dynamically:
        n_pts = round((B_max - B_min) / min_avg_spacing)
    where min_avg_spacing is the finest average spacing among all B arrays
    (clipped to the common B range). This preserves the resolution of the
    densest dataset without over- or under-sampling.
    """
    pairs = [(arrays_B_and_data[i], arrays_B_and_data[i + 1])
             for i in range(0, len(arrays_B_and_data), 2)]

    B_min = max(B.min() for B, _ in pairs)
    B_max = min(B.max() for B, _ in pairs)

    # Minimum adjacent-point spacing of each dataset within the common range
    def min_spacing_in(B):
        mask = (B >= B_min) & (B <= B_max)
        B_in = np.sort(B[mask])
        if len(B_in) < 2:
            return B_max - B_min
        return np.min(np.diff(B_in))  # smallest gap between any two adjacent points

    finest_spacing = min(min_spacing_in(B) for B, _ in pairs)
    n_pts = max(10, round((B_max - B_min) / finest_spacing) + 1)

    B_uniform = np.linspace(B_min, B_max, n_pts)
    resampled = []
    for B, data in pairs:
        sort_idx = np.argsort(B)
        resampled.append(np.interp(B_uniform, B[sort_idx], data[sort_idx]))
    return (B_uniform, *resampled)

# ===== Core Joint Fitting =====

def fit_two_band_sigma_joint(B_data, sigma_xx_data, sigma_xy_data):
    """
    Simultaneously fit sigma_xx(B) and sigma_xy(B).

    Parameters
    ----------
    B_data        : common B field array (T)
    sigma_xx_data : sigma_xx values (S/m)
    sigma_xy_data : sigma_xy values (S/m)

    Returns
    -------
    popt  : [n1s, mu1, n2s, mu2]  (n in 1e20 m^-3)
    perr  : 1-sigma errors
    r2_xx : R^2 for sigma_xx fit
    r2_xy : R^2 for sigma_xy fit
    """
    # ---- Initial guess ----
    mask = (np.abs(B_data) > 0.3) & (np.abs(B_data) < 1.5)
    if mask.sum() > 4:
        slope = np.polyfit(B_data[mask], sigma_xy_data[mask], 1)[0]
    else:
        slope = (sigma_xy_data[-1] - sigma_xy_data[0]) / (B_data[-1] - B_data[0] + 1e-30)

    n_sign  = -1.0 if slope < 0 else 1.0
    sigma0  = np.max(np.abs(sigma_xx_data))
    mu_guess = abs(slope) / (sigma0 + 1e-30)
    mu_guess = np.clip(mu_guess, 1e-4, 100.0)
    n_guess  = sigma0 / (e_charge * mu_guess)
    n_scale  = n_sign * n_guess / 1e20
    n_abs    = max(abs(n_scale), 1e-3)

    # Normalisation weights (inverse variance) for balanced joint residual
    var_xx = np.var(sigma_xx_data)
    var_xy = np.var(sigma_xy_data)
    w_xx = 1.0 / var_xx if var_xx > 0 else 1.0
    w_xy = 1.0 / var_xy if var_xy > 0 else 1.0

    def residual(params):
        try:
            sx_pred = model_sigma_xx(B_data, *params)
            sy_pred = model_sigma_xy(B_data, *params)
            return (w_xx * np.sum((sx_pred - sigma_xx_data)**2) +
                    w_xy * np.sum((sy_pred - sigma_xy_data)**2))
        except Exception:
            return 1e30

    n_hi = max(n_abs * 1000, 1000.0)
    bounds_de = [(-n_hi, n_hi), (1e-5, 1e3), (-n_hi, n_hi), (1e-5, 1e3)]

    # ---- Global search ----
    print("Running global optimisation (differential_evolution)...")
    de_res = differential_evolution(
        residual, bounds_de, seed=42, maxiter=3000, tol=1e-14,
        mutation=(0.5, 1.5), recombination=0.9, popsize=15, workers=1
    )
    print(f"Global optimum found  (fun={de_res.fun:.3e})")

    # ---- Local refinement ----
    bounds_min = [(None, None), (1e-5, 1e3), (None, None), (1e-5, 1e3)]
    opt_res = minimize(residual, x0=de_res.x, method='L-BFGS-B',
                       bounds=bounds_min, options={'maxiter': 200000, 'ftol': 1e-15})
    popt = opt_res.x

    # ---- Hessian-based error estimation ----
    eps = 1e-8
    n_params = len(popt)
    hessian = np.zeros((n_params, n_params))
    for i in range(n_params):
        def grad_i(x, _i=i):
            return approx_fprime(x, residual, eps * np.ones(n_params))[_i]
        hessian[i] = approx_fprime(popt, grad_i, eps * np.ones(n_params))
    hessian = 0.5 * (hessian + hessian.T)
    n_pts   = len(B_data)
    res_var = residual(popt) / (2 * n_pts - n_params)
    try:
        pcov = np.linalg.inv(hessian) * res_var * 2.0
        perr = np.sqrt(np.abs(np.diag(pcov)))
    except np.linalg.LinAlgError:
        perr = np.full(n_params, np.nan)

    r2_xx = 1 - np.sum((model_sigma_xx(B_data, *popt) - sigma_xx_data)**2) / \
                np.sum((sigma_xx_data - sigma_xx_data.mean())**2)
    r2_xy = 1 - np.sum((model_sigma_xy(B_data, *popt) - sigma_xy_data)**2) / \
                np.sum((sigma_xy_data - sigma_xy_data.mean())**2)

    return popt, perr, r2_xx, r2_xy

# ===== Main =====

def main():
    root = Tk(); root.withdraw()

    print("=" * 58)
    print("  Two-Band Joint Conductivity Fit (sigma_xx + sigma_xy)")
    print("=" * 58)

    # --- Load rho_xx ---
    print("\nSelect longitudinal resistivity file (rho_xx vs B)...")
    fp_xx = filedialog.askopenfilename(
        title="1/2: Select rho_xx data file (B in T, rho in ohm cm)",
        filetypes=(("Data files", "*.dat *.txt *.csv"), ("All files", "*.*"))
    )
    if not fp_xx:
        print("No file selected. Exiting."); return
    B_xx, rho_xx_cm = load_dat(fp_xx, 0, 1)
    rho_xx_m = rho_xx_cm * 1e-2
    print(f"-> Loaded rho_xx: {len(B_xx)} points from '{os.path.basename(fp_xx)}'")

    # --- Load rho_xy ---
    print("\nSelect Hall resistivity file (rho_xy vs B)...")
    fp_xy = filedialog.askopenfilename(
        title="2/2: Select Hall (rho_xy) data file (B in T, rho in ohm cm)",
        filetypes=(("Data files", "*.dat *.txt *.csv"), ("All files", "*.*"))
    )
    if not fp_xy:
        print("No file selected. Exiting."); return
    B_xy, rho_xy_cm = load_dat(fp_xy, 0, 1)
    rho_xy_m = rho_xy_cm * 1e-2
    print(f"-> Loaded rho_xy: {len(B_xy)} points from '{os.path.basename(fp_xy)}'")

    # --- Resample to common uniform B grid and convert to conductivity ---
    B_fit, rxx_fit_m, rxy_fit_m = resample_uniform(
        B_xx, rho_xx_m, B_xy, rho_xy_m
    )
    sigma_xx_data, sigma_xy_data = rho_to_sigma(rxx_fit_m, rxy_fit_m)

    print(f"\n-> Uniform B grid: {len(B_fit)} points  "
          f"[{B_fit.min():.3f} T, {B_fit.max():.3f} T]")
    print(f"-> sigma_xx range: {sigma_xx_data.min():.3e} to {sigma_xx_data.max():.3e} S/m")
    print(f"-> sigma_xy range: {sigma_xy_data.min():.3e} to {sigma_xy_data.max():.3e} S/m")

    # Reference sigma_xx(0) from data
    idx_zero = np.argmin(np.abs(B_xx))
    sigma_xx_0_data = 1.0 / (rho_xx_cm[idx_zero] * 1e-2)
    rho_xx_0_data_cm = rho_xx_cm[idx_zero]

    # --- Fit ---
    popt, perr, r2_xx, r2_xy = fit_two_band_sigma_joint(B_fit, sigma_xx_data, sigma_xy_data)

    # --- Extract parameters ---
    n1  = popt[0] * 1e20; mu1 = popt[1]
    n2  = popt[2] * 1e20; mu2 = popt[3]
    n1_err  = perr[0] * 1e20; mu1_err = perr[1]
    n2_err  = perr[2] * 1e20; mu2_err = perr[3]

    sigma_xx_0_fit  = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2
    rho_xx_0_fit_cm = 1.0 / sigma_xx_0_fit * 100

    print("\n=== Fit Results (SI Units) ===")
    print(f"Carrier 1 (n1): {n1:.4e} +/- {n1_err:.4e} m^-3 ({'Hole' if n1 > 0 else 'Electron'})")
    print(f"Mobility 1 (mu1): {mu1:.4e} +/- {mu1_err:.4e} m^2/(Vs)")
    print(f"Carrier 2 (n2): {n2:.4e} +/- {n2_err:.4e} m^-3 ({'Hole' if n2 > 0 else 'Electron'})")
    print(f"Mobility 2 (mu2): {mu2:.4e} +/- {mu2_err:.4e} m^2/(Vs)")
    print(f"--- Conductivity Check ---")
    print(f"sigma_xx(0) from data : {sigma_xx_0_data:.6e} S/m  [rho_xx(0) = {rho_xx_0_data_cm:.6e} ohm cm]")
    print(f"sigma_xx(0) from fit  : {sigma_xx_0_fit:.6e} S/m  [rho_xx(0) = {rho_xx_0_fit_cm:.6e} ohm cm]")
    print(f"R^2 (sigma_xx fit)    : {r2_xx:.4f}")
    print(f"R^2 (sigma_xy fit)    : {r2_xy:.4f}\n")

    # ===== Visualization =====
    B_smooth = np.linspace(B_fit.min(), B_fit.max(), 600)
    sxx_smooth = model_sigma_xx(B_smooth, *popt)
    sxy_smooth = model_sigma_xy(B_smooth, *popt)

    t1 = 'h' if n1 > 0 else 'e'
    t2 = 'h' if n2 > 0 else 'e'
    info = (
        f"Carrier 1 ({t1}): $n_1$=({n1:.2e}$\\pm${n1_err:.1e}) m$^{{-3}}$\n"
        f"  $\\mu_1$=({mu1:.3e}$\\pm${mu1_err:.1e}) m$^2$/Vs\n"
        f"Carrier 2 ({t2}): $n_2$=({n2:.2e}$\\pm${n2_err:.1e}) m$^{{-3}}$\n"
        f"  $\\mu_2$=({mu2:.3e}$\\pm${mu2_err:.1e}) m$^2$/Vs\n"
        f"$\\sigma_{{xx}}(0)$ fit  = {sigma_xx_0_fit:.3e} S/m\n"
        f"$\\sigma_{{xx}}(0)$ data = {sigma_xx_0_data:.3e} S/m"
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("Two-Band Joint Conductivity Fit", fontsize=15, fontweight='bold')

    # Left: sigma_xx (jointly fitted)
    ax_xx = axes[0]
    ax_xx.scatter(B_fit, sigma_xx_data, color='black', marker='o', facecolors='none',
                  s=12, label='From data ($\\sigma_{xx}$)')
    ax_xx.plot(B_smooth, sxx_smooth, 'b-', lw=2, label='Two-band Joint Fit')
    ax_xx.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax_xx.set_ylabel('$\\sigma_{xx}$ (S/m)', fontsize=13)
    ax_xx.legend(fontsize=11, loc='best')
    ax_xx.annotate(f'$R^2$ = {r2_xx:.4f}', xy=(0.05, 0.94), xycoords='axes fraction',
                   fontsize=11, color='blue', va='top')
    ax_xx.grid(True, ls='--', alpha=0.5)

    # Right: sigma_xy (jointly fitted)
    ax_xy = axes[1]
    ax_xy.scatter(B_fit, sigma_xy_data, color='black', marker='o', facecolors='none',
                  s=12, label='From data ($\\sigma_{xy}$)')
    ax_xy.plot(B_smooth, sxy_smooth, 'r-', lw=2, label='Two-band Joint Fit')
    ax_xy.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax_xy.set_ylabel('$\\sigma_{xy}$ (S/m)', fontsize=13)
    ax_xy.legend(fontsize=11, loc='best')
    ax_xy.annotate(f'$R^2$ = {r2_xy:.4f}', xy=(0.05, 0.94), xycoords='axes fraction',
                   fontsize=11, color='blue', va='top')
    ax_xy.annotate(info, xy=(0.03, 0.04), xycoords='axes fraction', fontsize=9,
                   color='blue', va='bottom',
                   bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='gray', alpha=0.8))
    ax_xy.grid(True, ls='--', alpha=0.5)

    plt.tight_layout()

    # ===== Export =====
    base_name = os.path.splitext(fp_xx)[0]
    out_png = base_name + '_sigma_joint_fit_plot.png'
    out_dat = base_name + '_sigma_joint_fit_result.dat'

    try:
        plt.savefig(out_png, dpi=300, bbox_inches='tight')
        print(f"=> Plot saved: {out_png}")
    except Exception as e:
        print(f"Warning: plot save failed. ({e})")

    try:
        sxx_at_data = model_sigma_xx(B_fit, *popt)
        sxy_at_data = model_sigma_xy(B_fit, *popt)
        with open(out_dat, 'w') as f:
            f.write("# Two-Band Joint Conductivity Fit Results\n")
            f.write(f"# Fit targets: sigma_xx(B) + sigma_xy(B) jointly\n")
            f.write(f"# R2(sigma_xx)={r2_xx:.6f}  R2(sigma_xy)={r2_xy:.6f}\n")
            f.write(f"# sigma_xx(0) from data = {sigma_xx_0_data:.6e} S/m\n")
            f.write(f"# sigma_xx(0) from fit  = {sigma_xx_0_fit:.6e} S/m\n")
            f.write(f"# rho_xx(0) from data   = {rho_xx_0_data_cm:.6e} ohm cm\n")
            f.write(f"# rho_xx(0) from fit    = {rho_xx_0_fit_cm:.6e} ohm cm\n")
            f.write("# --- Parameters ---\n")
            f.write(f"# n1 (m^-3) = {n1:.6e} +/- {n1_err:.6e} ({'Hole' if n1 > 0 else 'Electron'})\n")
            f.write(f"# mu1 (m^2/Vs) = {mu1:.6e} +/- {mu1_err:.6e}\n")
            f.write(f"# n2 (m^-3) = {n2:.6e} +/- {n2_err:.6e} ({'Hole' if n2 > 0 else 'Electron'})\n")
            f.write(f"# mu2 (m^2/Vs) = {mu2:.6e} +/- {mu2_err:.6e}\n")
            f.write("# ------------------\n")
            f.write("# B(T)\tsigma_xx_data(S/m)\tsigma_xx_fit(S/m)\tsigma_xy_data(S/m)\tsigma_xy_fit(S/m)\n")
            for i in range(len(B_fit)):
                f.write(f"{B_fit[i]:.6f}\t{sigma_xx_data[i]:.6e}\t{sxx_at_data[i]:.6e}\t"
                        f"{sigma_xy_data[i]:.6e}\t{sxy_at_data[i]:.6e}\n")
        print(f"=> Fit data exported: {out_dat}")
    except Exception as e:
        print(f"Warning: data export failed. ({e})")

    plt.show()


if __name__ == "__main__":
    main()
