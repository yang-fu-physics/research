"""
twobandfit_sigma_joint_range.py

A directly usable GUI wrapper program that imports the core joint conductivity-fitting
logic from `twobandfit_sigma_joint.py`, but allows you to restrict the fitting range
to a specified absolute magnetic field window (e.g., 2.5 T to 9.0 T).

Joint fitting simultaneously minimises residuals for both sigma_xx(B) and sigma_xy(B).
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from tkinter import Tk, filedialog

# Import core physics and fitting logic from the joint fitting program
from twobandfit_sigma_joint import (
    load_dat, rho_to_sigma, resample_uniform,
    fit_two_band_sigma_joint, model_sigma_xy, model_sigma_xx,
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

    print("=" * 65)
    print(f"  Joint Two-Band Fit (Restricted Range: {B_MIN_FIT} T to {B_MAX_FIT} T)")
    print("=" * 65)

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

    print(f"-> Loaded rho_xx: {len(B_xx)} points from '{os.path.basename(fp_xx)}'")
    print(f"-> Loaded rho_xy: {len(B_xy)} points from '{os.path.basename(fp_xy)}'")

    # 3. Resample to common uniform grid (full range), convert to conductivity
    B_fit_full, rxx_fit, rxy_fit = resample_uniform(B_xx, rho_xx_m, B_xy, rho_xy_m)
    sigma_xx_full, sigma_xy_full = rho_to_sigma(rxx_fit, rxy_fit)

    print(f"-> Full Uniform Grid: {len(B_fit_full)} points in "
          f"[{B_fit_full.min():.2f}, {B_fit_full.max():.2f}] T")

    # 4. Apply B-field Range Restriction
    mask = (np.abs(B_fit_full) >= B_MIN_FIT) & (np.abs(B_fit_full) <= B_MAX_FIT)
    B_filtered      = B_fit_full[mask]
    sxx_filtered    = sigma_xx_full[mask]
    sxy_filtered    = sigma_xy_full[mask]

    print(f"-> Filtered Grid    : {len(B_filtered)} points with |B| in "
          f"[{B_MIN_FIT}, {B_MAX_FIT}] T")
    print(f"-> sigma_xx range: {sxx_filtered.min():.3e} to {sxx_filtered.max():.3e} S/m")
    print(f"-> sigma_xy range: {sxy_filtered.min():.3e} to {sxy_filtered.max():.3e} S/m")

    if len(B_filtered) < 10:
        print("Error: Too few points in the restricted range. "
              "Please adjust B_MIN_FIT/B_MAX_FIT.")
        return

    # 5. Joint Fit on the Restricted Range
    print("\nRunning joint optimisation on restricted range...")
    popt, perr, r2_xx, r2_xy = fit_two_band_sigma_joint(
        B_filtered, sxx_filtered, sxy_filtered
    )

    # 6. Extract Parameters
    n1  = popt[0] * 1e20; mu1 = popt[1]
    n2  = popt[2] * 1e20; mu2 = popt[3]
    n1_err  = perr[0] * 1e20; mu1_err = perr[1]
    n2_err  = perr[2] * 1e20; mu2_err = perr[3]

    sigma_xx_0_fit = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2
    idx_zero = np.argmin(np.abs(B_xx))
    sigma_xx_0_data = 1.0 / (rho_xx_cm[idx_zero] * 1e-2)

    print(f"\n=== Fit Results (SI Units) ===")
    print(f"Carrier 1 (n1): {n1:.4e} +/- {n1_err:.4e} m^-3 "
          f"({'Hole' if n1 > 0 else 'Electron'})")
    print(f"Mobility 1 (mu1): {mu1:.4e} +/- {mu1_err:.4e} m^2/(Vs)")
    print(f"Carrier 2 (n2): {n2:.4e} +/- {n2_err:.4e} m^-3 "
          f"({'Hole' if n2 > 0 else 'Electron'})")
    print(f"Mobility 2 (mu2): {mu2:.4e} +/- {mu2_err:.4e} m^2/(Vs)")
    print(f"--- Zero-Field Check ---")
    print(f"sigma_xx(0) data : {sigma_xx_0_data:.6e} S/m")
    print(f"sigma_xx(0) fit  : {sigma_xx_0_fit:.6e} S/m")
    print(f"R^2 (sigma_xx joint, restricted) : {r2_xx:.6f}")
    print(f"R^2 (sigma_xy joint, restricted) : {r2_xy:.6f}")

    # 7. Full-range extrapolation R^2
    sxx_pred_full = model_sigma_xx(B_fit_full, *popt)
    sxy_pred_full = model_sigma_xy(B_fit_full, *popt)
    r2_xx_full = 1 - (np.sum((sxx_pred_full - sigma_xx_full)**2) /
                       np.sum((sigma_xx_full - sigma_xx_full.mean())**2))
    r2_xy_full = 1 - (np.sum((sxy_pred_full - sigma_xy_full)**2) /
                       np.sum((sigma_xy_full - sigma_xy_full.mean())**2))
    print(f"\nR^2 (sigma_xx) extrapolated full range : {r2_xx_full:.6f}")
    print(f"R^2 (sigma_xy) extrapolated full range : {r2_xy_full:.6f}")

    # 8. Visualization
    B_smooth = np.linspace(B_fit_full.min(), B_fit_full.max(), 600)
    sxx_smooth = model_sigma_xx(B_smooth, *popt)
    sxy_smooth = model_sigma_xy(B_smooth, *popt)

    t1 = 'h' if n1 > 0 else 'e'
    t2 = 'h' if n2 > 0 else 'e'
    info = (
        f"Carrier 1 ({t1}): n1 = {n1:.2e} m$^{{-3}}$\n"
        f"  $\\mu_1$ = {mu1:.3e} m$^2$/Vs\n"
        f"Carrier 2 ({t2}): n2 = {n2:.2e} m$^{{-3}}$\n"
        f"  $\\mu_2$ = {mu2:.3e} m$^2$/Vs\n"
        f"$\\sigma_{{xx}}(0)$ fit = {sigma_xx_0_fit:.3e} S/m\n"
        f"$\\sigma_{{xx}}(0)$ data = {sigma_xx_0_data:.3e} S/m"
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Joint Two-Band Fit (|B| $\\in$ [{B_MIN_FIT}, {B_MAX_FIT}] T)",
                 fontsize=15, fontweight='bold')

    # Left: sigma_xx
    ax = axes[0]
    ax.scatter(B_fit_full[~mask], sigma_xx_full[~mask], color='lightgray',
               marker='x', s=12, label='Ignored Data')
    ax.scatter(B_filtered, sxx_filtered, color='black', marker='o',
               facecolors='none', s=12, label='Fitted Data ($\\sigma_{xx}$)')
    ax.plot(B_smooth, sxx_smooth, 'b-', lw=2, label='Fit & Extrapolation')
    ax.axvspan(-B_MIN_FIT, B_MIN_FIT, color='gray', alpha=0.08)
    ax.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax.set_ylabel('$\\sigma_{xx}$ (S/m)', fontsize=13)
    ax.annotate(f'$R^2$ (range) = {r2_xx:.4f}\n$R^2$ (full) = {r2_xx_full:.4f}',
                xy=(0.05, 0.94), xycoords='axes fraction', fontsize=11,
                color='blue', va='top')
    ax.legend(fontsize=10); ax.grid(True, ls='--', alpha=0.5)

    # Right: sigma_xy
    ax = axes[1]
    ax.scatter(B_fit_full[~mask], sigma_xy_full[~mask], color='lightgray',
               marker='x', s=12, label='Ignored Data')
    ax.scatter(B_filtered, sxy_filtered, color='black', marker='o',
               facecolors='none', s=12, label='Fitted Data ($\\sigma_{xy}$)')
    ax.plot(B_smooth, sxy_smooth, 'r-', lw=2, label='Fit & Extrapolation')
    ax.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax.set_ylabel('$\\sigma_{xy}$ (S/m)', fontsize=13)
    ax.annotate(f'$R^2$ (range) = {r2_xy:.4f}\n$R^2$ (full) = {r2_xy_full:.4f}',
                xy=(0.05, 0.94), xycoords='axes fraction', fontsize=11,
                color='blue', va='top')
    ax.annotate(info, xy=(0.03, 0.42), xycoords='axes fraction', fontsize=9.5,
                color='blue', va='bottom',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='gray', alpha=0.8))
    ax.legend(fontsize=10); ax.grid(True, ls='--', alpha=0.5)

    plt.tight_layout()

    # 9. Export
    base_name = os.path.splitext(fp_xx)[0]
    tag = f'_sigma_joint_range_{B_MIN_FIT}T_{B_MAX_FIT}T'
    out_png = base_name + tag + '_plot.png'
    out_dat = base_name + tag + '_result.dat'

    try:
        plt.savefig(out_png, dpi=300, bbox_inches='tight')
        print(f"\n=> Plot saved: {out_png}")
    except Exception as e:
        print(f"Warning: plot save failed. ({e})")

    try:
        with open(out_dat, 'w') as f:
            f.write(f"# Joint Two-Band Conductivity Fit "
                    f"(Restricted Range {B_MIN_FIT}-{B_MAX_FIT} T)\n")
            f.write(f"# R2(sigma_xx restricted)={r2_xx:.6f}  "
                    f"R2(sigma_xy restricted)={r2_xy:.6f}\n")
            f.write(f"# R2(sigma_xx full extrap)={r2_xx_full:.6f}  "
                    f"R2(sigma_xy full extrap)={r2_xy_full:.6f}\n")
            f.write(f"# sigma_xx(0) from data = {sigma_xx_0_data:.6e} S/m\n")
            f.write(f"# sigma_xx(0) from fit  = {sigma_xx_0_fit:.6e} S/m\n")
            f.write("# --- Parameters ---\n")
            f.write(f"# n1 (m^-3) = {n1:.6e} +/- {n1_err:.6e} "
                    f"({'Hole' if n1 > 0 else 'Electron'})\n")
            f.write(f"# mu1 (m^2/Vs) = {mu1:.6e} +/- {mu1_err:.6e}\n")
            f.write(f"# n2 (m^-3) = {n2:.6e} +/- {n2_err:.6e} "
                    f"({'Hole' if n2 > 0 else 'Electron'})\n")
            f.write(f"# mu2 (m^2/Vs) = {mu2:.6e} +/- {mu2_err:.6e}\n")
            f.write("# ------------------\n")
            f.write("# [Full-range extrapolation]\n")
            f.write("# B(T)\tsxx_data\tsxx_fit\tsxy_data\tsxy_fit\n")
            for i in range(len(B_fit_full)):
                f.write(f"{B_fit_full[i]:.6f}\t{sigma_xx_full[i]:.6e}\t"
                        f"{sxx_pred_full[i]:.6e}\t{sigma_xy_full[i]:.6e}\t"
                        f"{sxy_pred_full[i]:.6e}\n")
        print(f"=> Fit data exported: {out_dat}")
    except Exception as e:
        print(f"Warning: data export failed. ({e})")

    plt.show()

if __name__ == "__main__":
    main()
