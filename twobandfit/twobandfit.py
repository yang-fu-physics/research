"""
twobandfit.py

The base program for fitting Hall resistivity (rho_xy vs B) to the two-band model.
- Uses optional zero-field longitudinal resistivity (rho_xx(0)) as a constraint
- Optionally loads measured longitudinal resistivity (rho_xx(B)) to visually 
  compare the calculation derived from the fit parameters.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, differential_evolution, minimize, approx_fprime
from tkinter import Tk, filedialog
import os

# ===== Physical Constants =====
e_charge = 1.602176634e-19          # Elementary charge in C

# ===== Two-Band Model =====

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
    """n_scale in 1e20 m^-3"""
    return two_band_rho_xy(B, n1s * 1e20, mu1, n2s * 1e20, mu2)

def model_rho_xx(B, n1s, mu1, n2s, mu2):
    """n_scale in 1e20 m^-3"""
    return two_band_rho_xx(B, n1s * 1e20, mu1, n2s * 1e20, mu2)

# ===== Data Loading ======

def load_dat(filepath, col_B=0, col_rho=1):
    data = pd.read_csv(filepath, sep='\t', header=0,
                       usecols=[col_B, col_rho]).dropna()
    data = data.drop_duplicates(subset=data.columns[0])
    B   = data.iloc[:, 0].values.astype(float)
    rho = data.iloc[:, 1].values.astype(float)
    return B, rho

# ===== Main Fitting Procedure =====

def fit_two_band(B_data, rho_data, sigma_xx_0=None):
    """
    Core fitting logic extracted to be callable by batch scripts.
    Returns: popt, perr, r2_xy, n1, n1_err, mu1, mu1_err, n2, n2_err, mu2, mu2_err
    """
    # Estimate p0
    mask = (np.abs(B_data) > 0.3) & (np.abs(B_data) < 1.5)
    if mask.sum() > 4:
        slope = np.polyfit(B_data[mask], rho_data[mask], 1)[0]
    else:
        slope = (rho_data[-1] - rho_data[0]) / (B_data[-1] - B_data[0])

    n_guess = 1.0 / (e_charge * abs(slope)) if slope != 0 else 1e26
    n_sign  = -1.0 if slope < 0 else 1.0
    n_scale = n_sign * n_guess / 1e20
    n_abs   = abs(n_scale)
    mu_guess = 0.5
    
    p0 = [n_sign * n_abs, mu_guess, n_sign * n_abs * 0.8, mu_guess * 0.3]

    # Differential_evolution Global Search (Support Both Holes and Electrons)
    n_hi = max(n_abs * 1000, 1000.0)
    bounds_de = [(-n_hi, n_hi), (1e-5, 1e3), (-n_hi, n_hi), (1e-5, 1e3)]

    def residual_de(params):
        try:
            n1s, mu1, n2s, mu2 = params
            pred = model_rho_xy(B_data, *params)
            err  = np.sum((pred - rho_data)**2)
            
            # Application of the rho_xx(0) soft constraint dynamically weighted by variance
            if sigma_xx_0 is not None:
                s_pred = e_charge * abs(n1s * 1e20) * mu1 + e_charge * abs(n2s * 1e20) * mu2
                w = 100 * np.sum((rho_data - rho_data.mean())**2) / sigma_xx_0**2
                err += w * (s_pred - sigma_xx_0)**2
            return err
        except Exception:
            return 1e30

    de_res = differential_evolution(
        residual_de, bounds_de, seed=42, maxiter=2000, tol=1e-14,
        mutation=(0.5, 1.5), recombination=0.9, popsize=15, workers=1
    )

    # Local Refinement (scipy.optimize.minimize with soft penalty)
    bounds_min = [(None, None), (1e-5, 1e3), (None, None), (1e-5, 1e3)]

    def objective_local(params):
        pred = model_rho_xy(B_data, *params)
        chi2 = np.sum((pred - rho_data)**2)
        if sigma_xx_0 is not None:
            n1s, mu1, n2s, mu2 = params
            s_pred = e_charge * abs(n1s * 1e20) * mu1 + e_charge * abs(n2s * 1e20) * mu2
            w = 100 * np.sum((rho_data - rho_data.mean())**2) / sigma_xx_0**2
            chi2 += w * (s_pred - sigma_xx_0)**2
        return chi2

    opt_res = minimize(objective_local, x0=de_res.x, method='L-BFGS-B',
                       bounds=bounds_min, options={'maxiter': 200000, 'ftol': 1e-15})
    popt = opt_res.x

    # Estimate parameter covariance from numerical Hessian
    eps = 1e-8
    n_params = len(popt)
    hessian = np.zeros((n_params, n_params))
        
    for i in range(n_params):
        def grad_i(x):
            return approx_fprime(x, objective_local, eps * np.ones(n_params))[i]
        hessian[i] = approx_fprime(popt, grad_i, eps * np.ones(n_params))
    hessian = 0.5 * (hessian + hessian.T)  # ensure symmetry
    
    # Scale residual variance like curve_fit does (reduced chi-squared)
    res_var = np.sum((model_rho_xy(B_data, *popt) - rho_data)**2) / (len(B_data) - n_params)
    
    try:
        pcov = np.linalg.inv(hessian) * res_var * 2.0  # *2.0 because Hessian is 2nd derivative of sum of squares
        perr = np.sqrt(np.abs(np.diag(pcov)))
    except np.linalg.LinAlgError:
        perr = np.full(n_params, np.nan)

    res_xy = rho_data - model_rho_xy(B_data, *popt)
    r2_xy  = 1 - np.sum(res_xy**2) / np.sum((rho_data - rho_data.mean())**2)

    return popt, perr, r2_xy

def main():
    root = Tk(); root.withdraw()

    print("=" * 52)
    print("      Two-Band Hall Fitting (with Optional rho_xx)  ")
    print("=" * 52)

    # --- 1. Ask for Zero-Field Resistivity Constraint ---
    rho_xx_0_input = input(
        "Enter zero-field resistivity rho_xx(0) in ohm cm\n"
        "(or press Enter to skip and run unconstrained): "
    ).strip()
    
    if rho_xx_0_input:
        try:
            rho_xx_0_cm = float(rho_xx_0_input)
            sigma_xx_0  = 1.0 / (rho_xx_0_cm * 1e-2)
            print(f"-> Using Constraint: rho_xx(0) = {rho_xx_0_cm:.4e} ohm cm")
        except ValueError:
            print("Invalid input. Constraint disabled.")
            sigma_xx_0 = None; rho_xx_0_cm = None
    else:
        sigma_xx_0 = None; rho_xx_0_cm = None

    # --- 2. Load Hall Data ---
    print("\nPlease select data file containing B (T) and rho_xy (ohm cm)...")
    fp_xy = filedialog.askopenfilename(
        title="1/2: Select Hall (rho_xy) data file",
        filetypes=(("Data files", "*.dat *.txt *.csv"), ("All files", "*.*"))
    )
    if not fp_xy:
        print("No Hall data file selected. Exiting."); return
        
    B_xy, rho_xy_cm = load_dat(fp_xy, 0, 1)
    rho_xy_m = rho_xy_cm * 1e-2
    print(f"-> Loaded rho_xy: {len(B_xy)} points from '{os.path.basename(fp_xy)}'")

    # --- 3. Optionally Load rho_xx Data ---
    print("\n(Optional) Select a longitudinal resistivity (rho_xx) file to evaluate and visually compare fit.\nPress Esc or Cancel in dialog to skip.")
    fp_xx = filedialog.askopenfilename(
        title="2/2: (Optional/Cancel to skip) Select rho_xx data file for comparison",
        filetypes=(("Data files", "*.dat *.txt *.csv"), ("All files", "*.*"))
    )
    if fp_xx:
        B_xx, rho_xx_cm = load_dat(fp_xx, 0, 1)
        print(f"-> Loaded rho_xx: {len(B_xx)} points from '{os.path.basename(fp_xx)}'")
        compare_rxx = True
        
        # Auto-extract rho_xx(0) if not provided manually
        if sigma_xx_0 is None:
            idx_zero = np.argmin(np.abs(B_xx))
            rho_xx_0_cm = rho_xx_cm[idx_zero]
            sigma_xx_0 = 1.0 / (rho_xx_0_cm * 1e-2)
            print(f"-> Auto-extracted Constraint: rho_xx(0) = {rho_xx_0_cm:.4e} ohm cm (at B = {B_xx[idx_zero]:.4f} T)")
    else:
        print("-> Skipped loading rho_xx data. Will plot Hall fit only.")
        compare_rxx = False

    # ===== Fit rho_xy data =====
    B_data   = B_xy
    rho_data = rho_xy_m

    print("\nRunning global optimisation (differential_evolution)...")
    popt, perr, r2_xy = fit_two_band(B_data, rho_data, sigma_xx_0)

    # Parameter Extraction
    n1  = popt[0] * 1e20; mu1 = popt[1]
    n2  = popt[2] * 1e20; mu2 = popt[3]
    n1_err  = perr[0] * 1e20; mu1_err = perr[1]
    n2_err  = perr[2] * 1e20; mu2_err = perr[3]

    sxx0 = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2
    rho_xx_0_fit_cm = 1.0 / sxx0 * 100

    print("\n=== Fit Results (SI Units) ===")
    print(f"Carrier 1 (n1): {n1:.4e} \u00b1 {n1_err:.4e} m^-3 ({'Hole' if n1 > 0 else 'Electron'})")
    print(f"Mobility 1 (mu1): {mu1:.4e} \u00b1 {mu1_err:.4e} m^2/(Vs)")
    print(f"Carrier 2 (n2): {n2:.4e} \u00b1 {n2_err:.4e} m^-3 ({'Hole' if n2 > 0 else 'Electron'})")
    print(f"Mobility 2 (mu2): {mu2:.4e} \u00b1 {mu2_err:.4e} m^2/(Vs)")
    if rho_xx_0_cm is not None:
        print(f"--- Constraint Check ---")
        print(f"Target rho_xx(0) : {rho_xx_0_cm:.6e} ohm cm")
    print(f"Fitted rho_xx(0) : {rho_xx_0_fit_cm:.6e} ohm cm")
    print(f"R^2 (rho_xy fit)  : {r2_xy:.4f}\n")

    # ===== Visualization & Export =====
    B_smooth_min = min(B_data.min(), B_xx.min()) if compare_rxx else B_data.min()
    B_smooth_max = max(B_data.max(), B_xx.max()) if compare_rxx else B_data.max()
    B_smooth = np.linspace(B_smooth_min, B_smooth_max, 600)
    
    rho_xy_fit_smooth_cm = model_rho_xy(B_smooth, *popt) * 100
    
    # Compose parameter text box
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
    
    # Draw logic depending on whether we want comparative rho_xx plot
    base_name = os.path.splitext(fp_xy)[0]
    out_dat = base_name + '_fit_result.dat'
    out_png = base_name + '_fit_plot.png'
    
    try:
        if compare_rxx:
            # Side-by-side Dual Plot
            fig, axes = plt.subplots(1, 2, figsize=(14, 6))
            fig.suptitle("Two-Band Fit: Hall vs Resistivity Comparison", fontsize=15, fontweight='bold')
            
            # Right Panel: rho_xy
            ax_xy = axes[1]
            ax_xy.scatter(B_data, rho_xy_cm, color='black', marker='o', facecolors='none', s=12, label='Raw $\\rho_{xy}$')
            ax_xy.plot(B_smooth, rho_xy_fit_smooth_cm, 'r-', lw=2, label='Two-band Fit')
            ax_xy.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
            ax_xy.set_ylabel('$\\rho_{xy}$ ($\\Omega\\cdot$cm)', fontsize=13)
            ax_xy.legend(fontsize=11, loc='best')
            ax_xy.annotate(f'$R^2$ = {r2_xy:.4f}', xy=(0.05, 0.94), xycoords='axes fraction', fontsize=11, color='blue', va='top')
            ax_xy.grid(True, ls='--', alpha=0.5)
            ax_xy.annotate(info, xy=(0.03, 0.04), xycoords='axes fraction', fontsize=9, color='blue', va='bottom', bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='gray', alpha=0.8))

            # Left Panel: rho_xx
            rho_xx_calc_cm = model_rho_xx(B_smooth, *popt) * 100
            rho_xx_calc_at_data = model_rho_xx(B_xx, *popt) * 100
            res_xx = rho_xx_cm - rho_xx_calc_at_data
            r2_xx  = 1 - np.sum(res_xx**2) / np.sum((rho_xx_cm - rho_xx_cm.mean())**2)

            ax_xx = axes[0]
            ax_xx.scatter(B_xx, rho_xx_cm, color='black', marker='o', facecolors='none', s=12, label='Measured $\\rho_{xx}$')
            ax_xx.plot(B_smooth, rho_xx_calc_cm, 'b-', lw=2, label='Calc. from fit params')
            ax_xx.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
            ax_xx.set_ylabel('$\\rho_{xx}$ ($\\Omega\\cdot$cm)', fontsize=13)
            ax_xx.legend(fontsize=11, loc='upper left')
            ax_xx.annotate(f'Compare $R^2$ = {r2_xx:.4f}', xy=(0.05, 0.94), xycoords='axes fraction', fontsize=11, color='blue', va='top')
            ax_xx.grid(True, ls='--', alpha=0.5)

            # Export logic for dual data
            fit_xy_at_raw = model_rho_xy(B_data, *popt) * 100
            with open(out_dat, 'w') as f:
                f.write("# Two-Band Hall Fit Results with rho_xx Comparison\n")
                f.write(f"# R2(rho_xy fit)={r2_xy:.6f}  R2(rho_xx compare)={r2_xx:.6f}\n")
                f.write(f"# Constraint rho_xx(0) = {rho_xx_0_cm if rho_xx_0_cm else 'None'} ohm cm\n")
                f.write(f"# Fitted  rho_xx(0) = {rho_xx_0_fit_cm:.8e} ohm cm\n")
                f.write("# --- Parameters ---\n")
                f.write(f"# n1 (m^-3) = {n1:.6e} +/- {n1_err:.6e} ({'Hole' if n1 > 0 else 'Electron'})\n")
                f.write(f"# mu1 (m^2/Vs) = {mu1:.6e} +/- {mu1_err:.6e}\n")
                f.write(f"# n2 (m^-3) = {n2:.6e} +/- {n2_err:.6e} ({'Hole' if n2 > 0 else 'Electron'})\n")
                f.write(f"# mu2 (m^2/Vs) = {mu2:.6e} +/- {mu2_err:.6e}\n")
                f.write("# ------------------\n")
                f.write("# [Hall Data @ Hall B grid]\n")
                f.write("# B(T)\trho_xy_raw(ohm_cm)\trho_xy_fit(ohm_cm)\n")
                for i in range(len(B_data)):
                    f.write(f"{B_data[i]:.6f}\t{rho_xy_cm[i]:.6e}\t{fit_xy_at_raw[i]:.6e}\n")
                f.write("# [rho_xx Data @ rho_xx B grid]\n")
                f.write("# B(T)\trho_xx_raw(ohm_cm)\trho_xx_calc(ohm_cm)\n")
                for i in range(len(B_xx)):
                    f.write(f"{B_xx[i]:.6f}\t{rho_xx_cm[i]:.6e}\t{rho_xx_calc_at_data[i]:.6e}\n")

        else:
            # Single Plot 
            fig, ax = plt.subplots(figsize=(8, 6))
            fig.suptitle("Two-Band Hall Fit", fontsize=15, fontweight='bold')
            ax.scatter(B_data, rho_xy_cm, color='black', marker='o', facecolors='none', s=12, label='Raw Data')
            ax.plot(B_smooth, rho_xy_fit_smooth_cm, 'r-', lw=2, label='Two-band Fit')
            ax.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
            ax.set_ylabel('$\\rho_{xy}$ ($\\Omega\\cdot$cm)', fontsize=13)
            ax.legend(fontsize=12, loc='best')
            ax.annotate(f'$R^2$ = {r2_xy:.4f}\n{info}', xy=(0.03, 0.96), xycoords='axes fraction', fontsize=11, color='blue', va='top', bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='gray', alpha=0.8))
            ax.grid(True, ls='--', alpha=0.5)
            
            # Export logic for single data
            fit_xy_at_raw = model_rho_xy(B_data, *popt) * 100
            with open(out_dat, 'w') as f:
                f.write("# Two-Band Hall Fit Results\n")
                f.write(f"# Constraint rho_xx(0) = {rho_xx_0_cm if rho_xx_0_cm else 'None'} ohm cm\n")
                f.write(f"# Fitted  rho_xx(0) = {rho_xx_0_fit_cm:.8e} ohm cm\n")
                f.write(f"# R-squared = {r2_xy:.6f}\n")
                f.write("# --- Parameters ---\n")
                f.write(f"# n1 (m^-3) = {n1:.6e} +/- {n1_err:.6e} ({'Hole' if n1 > 0 else 'Electron'})\n")
                f.write(f"# mu1 (m^2/Vs) = {mu1:.6e} +/- {mu1_err:.6e}\n")
                f.write(f"# n2 (m^-3) = {n2:.6e} +/- {n2_err:.6e} ({'Hole' if n2 > 0 else 'Electron'})\n")
                f.write(f"# mu2 (m^2/Vs) = {mu2:.6e} +/- {mu2_err:.6e}\n")
                f.write("# ------------------\n")
                f.write("# B(T)\trho_xy_raw(ohm_cm)\trho_xy_fit(ohm_cm)\n")
                for i in range(len(B_data)):
                    f.write(f"{B_data[i]:.6f}\t{rho_xy_cm[i]:.6e}\t{fit_xy_at_raw[i]:.6e}\n")

        print(f"\n=> Fit data exported: {out_dat}")
    except Exception as e:
        print(f"\nWarning: export failed. ({e})")

    try:
        plt.tight_layout()
        plt.savefig(out_png, dpi=300, bbox_inches='tight')
        print(f"=> Plot saved: {out_png}")
    except Exception as e:
        print(f"\nWarning: plot save failed. ({e})")

    plt.show()

if __name__ == "__main__":
    main()
