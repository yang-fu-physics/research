"""
twobandfit_sigma_range.py

A directly usable GUI wrapper program that imports the core conductivity-fitting logic
from `twobandfit_sigma.py`, but allows you to restrict the fitting range to high
magnetic fields (e.g., 2.5 T to 9.0 T) to avoid low-field anomalies.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog

# Import core physics and fitting logic from your main program
from twobandfit_sigma import (
    load_dat, rho_to_sigma, resample_uniform, 
    fit_two_band_sigma, model_sigma_xy, model_sigma_xx, 
    e_charge
)

# ==========================================
# CONFIGURATION PARAMETERS (User editable)
# ==========================================
B_MIN_FIT = 2.5   # Minimum absolute magnetic field to include in fit (T)
B_MAX_FIT = 9.0   # Maximum absolute magnetic field to include in fit (T)
# ==========================================

def main():
    root = Tk(); root.withdraw()

    print("=" * 60)
    print(f"  Two-Band Hall Fit (Restricted Range: {B_MIN_FIT} T to {B_MAX_FIT} T)")
    print("=" * 60)

    # 1. Select files via GUI
    print("\nPlease select the longitudinal resistivity file (rho_xx vs B)...")
    fp_xx = filedialog.askopenfilename(
        title="1/2: Select rho_xx data file (B in T, rho in ohm cm)",
        filetypes=(("Data files", "*.dat *.txt *.csv"), ("All files", "*.*"))
    )
    if not fp_xx:
        print("No rho_xx file selected. Exiting."); return

    print("\nPlease select the Hall resistivity file (rho_xy vs B)...")
    fp_xy = filedialog.askopenfilename(
        title="2/2: Select Hall (rho_xy) data file (B in T, rho in ohm cm)",
        filetypes=(("Data files", "*.dat *.txt *.csv"), ("All files", "*.*"))
    )
    if not fp_xy:
        print("No Hall file selected. Exiting."); return

    # 2. Load Data
    B_xx, rho_xx_cm = load_dat(fp_xx, 0, 1)
    B_xy, rho_xy_cm = load_dat(fp_xy, 0, 1)
    
    rho_xx_m = rho_xx_cm * 1e-2
    rho_xy_m = rho_xy_cm * 1e-2

    # 3. Extract sigma_xx(0) from FULL data (before filtering)
    idx_zero = np.argmin(np.abs(B_xx))
    rho_xx_0_cm = rho_xx_cm[idx_zero]
    sigma_xx_0  = 1.0 / (rho_xx_0_cm * 1e-2)
    print(f"-> Auto-extracted constraint: rho_xx(0) = {rho_xx_0_cm:.4e} ohm cm "
          f"→ sigma_xx(0) = {sigma_xx_0:.4e} S/m")

    # 4. Resample to common uniform grid (full range)
    B_fit_full, rho_xx_fit, rho_xy_fit = resample_uniform(B_xx, rho_xx_m, B_xy, rho_xy_m)
    _, sigma_xy_data_full = rho_to_sigma(rho_xx_fit, rho_xy_fit)
    
    # Keep original Hall B axis separate for sigma_xx comparison
    B_xy_orig = B_xy
    B_xy_orig_rho = rho_xy_m

    # 5. Apply B-field Range Restriction
    mask = (np.abs(B_fit_full) >= B_MIN_FIT) & (np.abs(B_fit_full) <= B_MAX_FIT)
    B_filtered = B_fit_full[mask]
    sigma_xy_filtered = sigma_xy_data_full[mask]
    
    print(f"-> Full Grid     : {len(B_fit_full)} points in [{B_fit_full.min():.2f}, {B_fit_full.max():.2f}] T")
    print(f"-> Filtered Grid : {len(B_filtered)} points in |B| ∈ [{B_MIN_FIT}, {B_MAX_FIT}] T")

    if len(B_filtered) < 10:
        print("Error: Too few points in the restricted range. Please adjust B_MIN_FIT/B_MAX_FIT.")
        return

    # 6. Perform the Fit on the Restricted Range
    print("\nRunning global optimisation (differential_evolution) on restricted range...")
    popt, perr, r2_xy = fit_two_band_sigma(B_filtered, sigma_xy_filtered, sigma_xx_0)

    # 7. Extract Parameters
    n1  = popt[0] * 1e20; mu1 = popt[1]
    n2  = popt[2] * 1e20; mu2 = popt[3]
    n1_err  = perr[0] * 1e20; mu1_err = perr[1]
    n2_err  = perr[2] * 1e20; mu2_err = perr[3]
    
    sigma_xx_0_fit = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2

    print("\n=== Fit Results (SI Units) ===")
    print(f"Carrier 1 (n1): {n1:.4e} +/- {n1_err:.4e} m^-3 ({'Hole' if n1 > 0 else 'Electron'})")
    print(f"Mobility 1 (mu1): {mu1:.4e} +/- {mu1_err:.4e} m^2/(Vs)")
    print(f"Carrier 2 (n2): {n2:.4e} +/- {n2_err:.4e} m^-3 ({'Hole' if n2 > 0 else 'Electron'})")
    print(f"Mobility 2 (mu2): {mu2:.4e} +/- {mu2_err:.4e} m^2/(Vs)")
    print(f"--- Constraint Check ---")
    print(f"sigma_xx(0) data : {sigma_xx_0:.6e} S/m")
    print(f"sigma_xx(0) fit  : {sigma_xx_0_fit:.6e} S/m")
    print(f"R^2 (sigma_xy fit) over [{B_MIN_FIT}, {B_MAX_FIT}] T : {r2_xy:.6f}\n")

    # 8. Visualization (Comparison of whole range)
    # Calculate R2 on the full range for reference
    sxy_fit_full = model_sigma_xy(B_fit_full, *popt)
    r2_full = 1 - np.sum((sxy_fit_full - sigma_xy_data_full)**2) / np.sum((sigma_xy_data_full - sigma_xy_data_full.mean())**2)
    print(f"R^2 (sigma_xy) Extrapolated over FULL range: {r2_full:.6f}")

    # Calculate actual sigma_xx directly from data for plotting
    rho_xy_at_xx = np.interp(B_xx, np.sort(B_xy_orig), B_xy_orig_rho[np.argsort(B_xy_orig)])
    sigma_xx_data_comp, _ = rho_to_sigma(rho_xx_m, rho_xy_at_xx)
    
    B_smooth = np.linspace(min(B_fit_full.min(), B_xx.min()), max(B_fit_full.max(), B_xx.max()), 600)
    sxy_fit_smooth = model_sigma_xy(B_smooth, *popt)
    sxx_fit_smooth = model_sigma_xx(B_smooth, *popt)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Two-Band Conductivity Fit (Restricted |B| $\\in$ [{B_MIN_FIT}, {B_MAX_FIT}] T)", fontsize=15, fontweight='bold')

    # Left: sigma_xx
    ax_xx = axes[0]
    ax_xx.scatter(B_xx, sigma_xx_data_comp, color='black', marker='o', facecolors='none', s=12, label='Data ($\\sigma_{xx}$)')
    ax_xx.plot(B_smooth, sxx_fit_smooth, 'b-', lw=2, label='Calc. from fit params')
    ax_xx.axvspan(-B_MIN_FIT, B_MIN_FIT, color='gray', alpha=0.1, label=f'Ignored in fit (<{B_MIN_FIT}T)')
    ax_xx.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax_xx.set_ylabel('$\\sigma_{xx}$ (S/m)', fontsize=13)
    ax_xx.legend()
    ax_xx.grid(True, ls='--', alpha=0.5)

    # Right: sigma_xy
    ax_xy = axes[1]
    ax_xy.scatter(B_fit_full[~mask], sigma_xy_data_full[~mask], color='lightgray', marker='x', s=12, label='Ignored Data')
    ax_xy.scatter(B_filtered, sigma_xy_filtered, color='black', marker='o', facecolors='none', s=12, label='Fitted Data')
    ax_xy.plot(B_smooth, sxy_fit_smooth, 'r-', lw=2, label='Fit & Extrapolation')
    ax_xy.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax_xy.set_ylabel('$\\sigma_{xy}$ (S/m)', fontsize=13)
    
    t1 = 'h' if n1 > 0 else 'e'
    t2 = 'h' if n2 > 0 else 'e'
    info = (
        f"Carrier 1 ({t1}): n1 = {n1:.2e} m^{{-3}}\n  $\\mu_1$ = {mu1:.3e} m$^2$/Vs\n"
        f"Carrier 2 ({t2}): n2 = {n2:.2e} m^{{-3}}\n  $\\mu_2$ = {mu2:.3e} m$^2$/Vs\n"
        f"$\\sigma_{{xx}}(0)$ fit  = {sigma_xx_0_fit:.3e} S/m\n"
        f"$\\sigma_{{xx}}(0)$ data = {sigma_xx_0:.3e} S/m\n"
        f"$R^2$ (range) = {r2_xy:.6f}"
    )
    ax_xy.annotate(info, xy=(0.03, 0.45), xycoords='axes fraction', fontsize=10,
                   bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='gray', alpha=0.8))
    ax_xy.legend()
    ax_xy.grid(True, ls='--', alpha=0.5)

    plt.tight_layout()

    # 9. Export
    base_name = os.path.splitext(fp_xx)[0]
    out_png = base_name + f'_sigma_range_{B_MIN_FIT}T_{B_MAX_FIT}T_plot.png'
    out_dat = base_name + f'_sigma_range_{B_MIN_FIT}T_{B_MAX_FIT}T_result.dat'

    try:
        plt.savefig(out_png, dpi=300, bbox_inches='tight')
        print(f"=> Plot saved: {out_png}")
    except Exception as e:
        print(f"Warning: plot save failed. ({e})")

    try:
        with open(out_dat, 'w') as f:
            f.write(f"# Two-Band Hall Conductivity Fit (Restricted Range {B_MIN_FIT}-{B_MAX_FIT} T)\n")
            f.write(f"# R2(sigma_xy restricted fit)={r2_xy:.6f}  R2(sigma_xy full extrap)={r2_full:.6f}\n")
            f.write(f"# sigma_xx(0) from data = {sigma_xx_0:.6e} S/m\n")
            f.write(f"# sigma_xx(0) from fit  = {sigma_xx_0_fit:.6e} S/m\n")
            f.write("# --- Parameters ---\n")
            f.write(f"# n1 (m^-3) = {n1:.6e} +/- {n1_err:.6e} ({'Hole' if n1 > 0 else 'Electron'})\n")
            f.write(f"# mu1 (m^2/Vs) = {mu1:.6e} +/- {mu1_err:.6e}\n")
            f.write(f"# n2 (m^-3) = {n2:.6e} +/- {n2_err:.6e} ({'Hole' if n2 > 0 else 'Electron'})\n")
            f.write(f"# mu2 (m^2/Vs) = {mu2:.6e} +/- {mu2_err:.6e}\n")
            f.write("# ------------------\n")
            f.write("# [Hall conductivity extrapolation @ Full grid]\n")
            f.write("# B(T)\tsigma_xy_data(S/m)\tsigma_xy_fit(S/m)\n")
            for i in range(len(B_fit_full)):
                f.write(f"{B_fit_full[i]:.6f}\t{sigma_xy_data_full[i]:.6e}\t{sxy_fit_full[i]:.6e}\n")
        print(f"=> Fit data exported: {out_dat}")
    except Exception as e:
        print(f"Warning: data export failed. ({e})")

    plt.show()

if __name__ == "__main__":
    main()
