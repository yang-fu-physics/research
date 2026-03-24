"""
twobandfit_batch.py

Batch processing script for two-band Hall fitting.
- Scans a data folder (default: rawdata/) for paired R-{T}K.dat and hall-{T}K.dat files
- Performs Hall fitting (twobandfit.py approach) with rho_xx(0) auto-constraint for each temperature
- Exports per-temperature fit results (data + plot)
- Generates a summary table and summary plots of all fitted parameters vs temperature

Usage:
    python twobandfit_batch.py                      # scan rawdata/
    python twobandfit_batch.py path/to/data_folder  # specify folder
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import differential_evolution, minimize, approx_fprime
import os
import sys
import re
import glob
import traceback

# ===== Physical Constants =====
e_charge = 1.602176634e-19  # Elementary charge in C

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
    return two_band_rho_xy(B, n1s * 1e20, mu1, n2s * 1e20, mu2)

def model_rho_xx(B, n1s, mu1, n2s, mu2):
    return two_band_rho_xx(B, n1s * 1e20, mu1, n2s * 1e20, mu2)

from twobandfit import fit_two_band

# ===== Data Loading =====

def load_dat(filepath, col_B=0, col_rho=1):
    data = pd.read_csv(filepath, sep='\t', header=0,
                       usecols=[col_B, col_rho]).dropna()
    data = data.drop_duplicates(subset=data.columns[0])
    B   = data.iloc[:, 0].values.astype(float)
    rho = data.iloc[:, 1].values.astype(float)
    return B, rho

# ===== File Discovery =====

def discover_data_pairs(data_dir):
    """
    Scan data_dir for paired R-{T}K.dat and hall-{T}K.dat files.
    Returns list of (temperature_float, temperature_str, rxx_path, hall_path)
    sorted by temperature.
    """
    # Find all hall files
    hall_files = glob.glob(os.path.join(data_dir, 'hall-*.dat'))
    rxx_files  = glob.glob(os.path.join(data_dir, 'R-*.dat'))

    # Extract temperatures from hall files
    hall_temps = {}
    for f in hall_files:
        basename = os.path.basename(f)
        m = re.match(r'hall-(.+)\.dat$', basename, re.IGNORECASE)
        if m:
            temp_str = m.group(1)  # e.g. "2.0K"
            # Remove trailing K if present
            temp_num_str = temp_str.rstrip('Kk')
            try:
                temp_val = float(temp_num_str)
                hall_temps[temp_str] = f
            except ValueError:
                pass

    # Extract temperatures from R files
    rxx_temps = {}
    for f in rxx_files:
        basename = os.path.basename(f)
        m = re.match(r'R-(.+)\.dat$', basename, re.IGNORECASE)
        if m:
            temp_str = m.group(1)
            temp_num_str = temp_str.rstrip('Kk')
            try:
                temp_val = float(temp_num_str)
                rxx_temps[temp_str] = f
            except ValueError:
                pass

    # Find matching pairs
    pairs = []
    all_temps = set(hall_temps.keys()) | set(rxx_temps.keys())
    for temp_str in all_temps:
        if temp_str in hall_temps and temp_str in rxx_temps:
            temp_num_str = temp_str.rstrip('Kk')
            pairs.append((float(temp_num_str), temp_str, rxx_temps[temp_str], hall_temps[temp_str]))
        else:
            if temp_str in hall_temps:
                print(f"  [WARNING] hall-{temp_str}.dat found but no matching R-{temp_str}.dat -- skipped")
            else:
                print(f"  [WARNING] R-{temp_str}.dat found but no matching hall-{temp_str}.dat -- skipped")

    pairs.sort(key=lambda x: x[0])
    return pairs

# ===== Single Temperature Fitting =====

def fit_single_temperature(hall_path, rxx_path, temp_str, output_dir):
    """
    Fit Hall data for a single temperature using twobandfit.py approach
    (Hall fit with rho_xx(0) auto-constraint).
    Returns dict of fit results, or None on failure.
    """
    # Load Hall data
    B_xy, rho_xy_cm = load_dat(hall_path, 0, 1)
    rho_xy_m = rho_xy_cm * 1e-2

    # Load rho_xx data
    B_xx, rho_xx_cm = load_dat(rxx_path, 0, 1)

    # Auto-extract rho_xx(0) constraint
    idx_zero = np.argmin(np.abs(B_xx))
    rho_xx_0_cm = rho_xx_cm[idx_zero]
    sigma_xx_0 = 1.0 / (rho_xx_0_cm * 1e-2)

    # Fitting
    B_data   = B_xy
    rho_data = rho_xy_m

    popt, perr, r2_xy = fit_two_band(B_data, rho_data, sigma_xx_0)

    # Extract parameters
    n1  = popt[0] * 1e20; mu1 = popt[1]
    n2  = popt[2] * 1e20; mu2 = popt[3]
    n1_err  = perr[0] * 1e20; mu1_err = perr[1]
    n2_err  = perr[2] * 1e20; mu2_err = perr[3]

    sxx0 = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2
    rho_xx_0_fit_cm = 1.0 / sxx0 * 100

    # r2_xy is returned directly from fit_two_band (no need to recalculate)

    # R^2 for rho_xx (comparison)
    rho_xx_calc_at_data = model_rho_xx(B_xx, *popt) * 100
    res_xx = rho_xx_cm - rho_xx_calc_at_data
    r2_xx  = 1 - np.sum(res_xx**2) / np.sum((rho_xx_cm - rho_xx_cm.mean())**2)

    # ===== Plot =====
    B_smooth_min = min(B_data.min(), B_xx.min())
    B_smooth_max = max(B_data.max(), B_xx.max())
    B_smooth = np.linspace(B_smooth_min, B_smooth_max, 600)

    rho_xy_fit_smooth_cm = model_rho_xy(B_smooth, *popt) * 100
    rho_xx_calc_cm = model_rho_xx(B_smooth, *popt) * 100

    t1 = 'h' if n1 > 0 else 'e'
    t2 = 'h' if n2 > 0 else 'e'
    info = (
        f"Carrier 1 ({t1}): $n_1$=({n1:.2e}$\\pm${n1_err:.1e}) m$^{{-3}}$\n"
        f"  $\\mu_1$=({mu1:.3e}$\\pm${mu1_err:.1e}) m$^2$/Vs\n"
        f"Carrier 2 ({t2}): $n_2$=({n2:.2e}$\\pm${n2_err:.1e}) m$^{{-3}}$\n"
        f"  $\\mu_2$=({mu2:.3e}$\\pm${mu2_err:.1e}) m$^2$/Vs\n"
        f"Fitted $\\rho_{{xx}}(0)$={rho_xx_0_fit_cm:.4e} $\\Omega\\cdot$cm\n"
        f"Target  $\\rho_{{xx}}(0)$={rho_xx_0_cm:.4e} $\\Omega\\cdot$cm"
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Two-Band Hall Fit: T = {temp_str}", fontsize=15, fontweight='bold')

    # Left: rho_xx
    ax_xx = axes[0]
    ax_xx.scatter(B_xx, rho_xx_cm, color='black', marker='o', facecolors='none', s=12, label='Measured $\\rho_{xx}$')
    ax_xx.plot(B_smooth, rho_xx_calc_cm, 'b-', lw=2, label='Calc. from fit params')
    ax_xx.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax_xx.set_ylabel('$\\rho_{xx}$ ($\\Omega\\cdot$cm)', fontsize=13)
    ax_xx.legend(fontsize=11, loc='upper left')
    ax_xx.annotate(f'Compare $R^2$ = {r2_xx:.4f}', xy=(0.05, 0.94), xycoords='axes fraction', fontsize=11, color='blue', va='top')
    ax_xx.grid(True, ls='--', alpha=0.5)

    # Right: rho_xy
    ax_xy = axes[1]
    ax_xy.scatter(B_data, rho_xy_cm, color='black', marker='o', facecolors='none', s=12, label='Raw $\\rho_{xy}$')
    ax_xy.plot(B_smooth, rho_xy_fit_smooth_cm, 'r-', lw=2, label='Two-band Fit')
    ax_xy.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax_xy.set_ylabel('$\\rho_{xy}$ ($\\Omega\\cdot$cm)', fontsize=13)
    ax_xy.legend(fontsize=11, loc='best')
    ax_xy.annotate(f'$R^2$ = {r2_xy:.4f}', xy=(0.05, 0.94), xycoords='axes fraction', fontsize=11, color='blue', va='top')
    ax_xy.grid(True, ls='--', alpha=0.5)
    ax_xy.annotate(info, xy=(0.03, 0.04), xycoords='axes fraction', fontsize=9, color='blue', va='bottom',
                   bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='gray', alpha=0.8))

    plt.tight_layout()

    # Save plot
    out_png = os.path.join(output_dir, f'{temp_str}_fit_plot.png')
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close(fig)

    # ===== Export data =====
    out_dat = os.path.join(output_dir, f'{temp_str}_fit_result.dat')
    fit_xy_at_raw = model_rho_xy(B_data, *popt) * 100

    with open(out_dat, 'w') as f:
        f.write(f"# Two-Band Hall Fit Results - T = {temp_str}\n")
        f.write(f"# R2(rho_xy fit)={r2_xy:.6f}  R2(rho_xx compare)={r2_xx:.6f}\n")
        f.write(f"# Constraint rho_xx(0) = {rho_xx_0_cm:.6e} ohm cm\n")
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

    return {
        'temp_str': temp_str,
        'temp_val': float(temp_str.rstrip('Kk')),
        'n1': n1, 'n1_err': n1_err, 'mu1': mu1, 'mu1_err': mu1_err,
        'n2': n2, 'n2_err': n2_err, 'mu2': mu2, 'mu2_err': mu2_err,
        'r2_xy': r2_xy, 'r2_xx': r2_xx,
        'rho_xx_0_target': rho_xx_0_cm,
        'rho_xx_0_fit': rho_xx_0_fit_cm,
        'type1': 'Hole' if n1 > 0 else 'Electron',
        'type2': 'Hole' if n2 > 0 else 'Electron',
        'out_dat': out_dat,
        'out_png': out_png,
    }

# ===== Summary Output =====

def export_summary(results, output_dir):
    """Export summary table and summary plot."""
    if not results:
        print("\n[WARNING] No successful fits to summarize.")
        return

    # Sort by temperature
    results.sort(key=lambda r: r['temp_val'])

    # --- Summary Table (DAT) ---
    summary_path = os.path.join(output_dir, 'batch_summary.dat')
    with open(summary_path, 'w') as f:
        f.write("# Two-Band Hall Fit Batch Summary\n")
        f.write("# Columns: T(K)\tn1(m^-3)\tn1_err\tType1\tmu1(m^2/Vs)\tmu1_err\t"
                "n2(m^-3)\tn2_err\tType2\tmu2(m^2/Vs)\tmu2_err\t"
                "R2_xy\tR2_xx\trho_xx(0)_target(ohm_cm)\trho_xx(0)_fit(ohm_cm)\n")
        for r in results:
            f.write(f"{r['temp_val']}\t{r['n1']:.6e}\t{r['n1_err']:.6e}\t{r['type1']}\t"
                    f"{r['mu1']:.6e}\t{r['mu1_err']:.6e}\t"
                    f"{r['n2']:.6e}\t{r['n2_err']:.6e}\t{r['type2']}\t"
                    f"{r['mu2']:.6e}\t{r['mu2_err']:.6e}\t"
                    f"{r['r2_xy']:.6f}\t{r['r2_xx']:.6f}\t"
                    f"{r['rho_xx_0_target']:.6e}\t{r['rho_xx_0_fit']:.6e}\n")
    print(f"\n=> Summary table saved: {summary_path}")

    # --- Console Summary ---
    print("\n" + "=" * 120)
    print("  BATCH FIT SUMMARY")
    print("=" * 120)
    header = (f"{'T(K)':>8s}  {'n1(m^-3)':>12s}  {'mu1(m^2/Vs)':>12s}  {'Type1':>8s}  "
              f"{'n2(m^-3)':>12s}  {'mu2(m^2/Vs)':>12s}  {'Type2':>8s}  "
              f"{'R2_xy':>8s}  {'R2_xx':>8s}")
    print(header)
    print("-" * 120)
    for r in results:
        print(f"{r['temp_val']:8.2f}  {r['n1']:12.4e}  {r['mu1']:12.4e}  {r['type1']:>8s}  "
              f"{r['n2']:12.4e}  {r['mu2']:12.4e}  {r['type2']:>8s}  "
              f"{r['r2_xy']:8.4f}  {r['r2_xx']:8.4f}")
    print("=" * 120)

    # --- Summary Plot (only if multiple temperatures) ---
    if len(results) > 1:
        temps = [r['temp_val'] for r in results]
        n1_vals = [abs(r['n1']) for r in results]
        n2_vals = [abs(r['n2']) for r in results]
        mu1_vals = [r['mu1'] for r in results]
        mu2_vals = [r['mu2'] for r in results]
        n1_errs = [r['n1_err'] for r in results]
        n2_errs = [r['n2_err'] for r in results]
        mu1_errs = [r['mu1_err'] for r in results]
        mu2_errs = [r['mu2_err'] for r in results]

        # Helper to cap error bars for log scale (prevent negative lower bounds, clip upper bounds)
        def cap_errors(vals, errs, val_name):
            err_lower = np.array(errs)
            
            # For lower error bound, prevent log(negative) by clipping to 99% of the value
            # This means the error bar goes down to 1% of the value on the log scale
            mask_large_lower = err_lower >= np.array(vals)
            err_lower[mask_large_lower] = np.array(vals)[mask_large_lower] * 0.99
            
            # Optional: clip upper error to avoid axis scaling blowing up (e.g. max 1000x the value)
            err_upper = np.array(errs)
            mask_large_upper = err_upper > 100 * np.array(vals)
            err_upper[mask_large_upper] = 100 * np.array(vals)[mask_large_upper]
            
            return [err_lower, err_upper]

        n1_err_adj = cap_errors(n1_vals, n1_errs, 'n1')
        n2_err_adj = cap_errors(n2_vals, n2_errs, 'n2')
        mu1_err_adj = cap_errors(mu1_vals, mu1_errs, 'mu1')
        mu2_err_adj = cap_errors(mu2_vals, mu2_errs, 'mu2')

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle("Two-Band Fit: Parameters vs Temperature", fontsize=16, fontweight='bold')

        # Left: Carrier concentrations
        ax_n = axes[0]
        ax_n.errorbar(temps, n1_vals, yerr=n1_err_adj, fmt='o-', color='#d62728', 
                      markersize=7, linewidth=2, capsize=4, capthick=1.5,
                      label=f'|n$_1$| ({results[0]["type1"][0]})')
        ax_n.errorbar(temps, n2_vals, yerr=n2_err_adj, fmt='s-', color='#1f77b4', 
                      markersize=7, linewidth=2, capsize=4, capthick=1.5,
                      label=f'|n$_2$| ({results[0]["type2"][0]})')
        ax_n.set_xlabel('Temperature (K)', fontsize=14)
        ax_n.set_ylabel('Carrier Concentration (m$^{-3}$)', fontsize=14)
        ax_n.set_yscale('log')
        ax_n.tick_params(axis='both', which='major', labelsize=12)
        ax_n.legend(fontsize=12, framealpha=0.9)
        ax_n.grid(True, which="major", ls='--', alpha=0.6)
        ax_n.grid(True, which="minor", ls=':', alpha=0.3)

        # Right: Mobilities
        ax_mu = axes[1]
        ax_mu.errorbar(temps, mu1_vals, yerr=mu1_err_adj, fmt='o-', color='#d62728', 
                       markersize=7, linewidth=2, capsize=4, capthick=1.5,
                       label=f'$\\mu_1$ ({results[0]["type1"][0]})')
        ax_mu.errorbar(temps, mu2_vals, yerr=mu2_err_adj, fmt='s-', color='#1f77b4', 
                       markersize=7, linewidth=2, capsize=4, capthick=1.5,
                       label=f'$\\mu_2$ ({results[0]["type2"][0]})')
        ax_mu.set_xlabel('Temperature (K)', fontsize=14)
        ax_mu.set_ylabel('Mobility (m$^2$/V$\\cdot$s)', fontsize=14)
        ax_mu.set_yscale('log')
        ax_mu.tick_params(axis='both', which='major', labelsize=12)
        ax_mu.legend(fontsize=12, framealpha=0.9)
        ax_mu.grid(True, which="major", ls='--', alpha=0.6)
        ax_mu.grid(True, which="minor", ls=':', alpha=0.3)

        plt.tight_layout()
        summary_png = os.path.join(output_dir, 'batch_summary_plot.png')
        plt.savefig(summary_png, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"=> Summary plot saved: {summary_png}")
    else:
        print("(Only 1 temperature -- skipping summary plot)")


# ===== Main =====

def main():
    print("=" * 60)
    print("   Two-Band Hall Fitting -- Batch Processing")
    print("=" * 60)

    # Determine data directory
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rawdata')

    if not os.path.isdir(data_dir):
        print(f"[ERROR] Data directory not found: {data_dir}")
        sys.exit(1)

    print(f"\nScanning: {data_dir}")

    # Discover paired data files
    pairs = discover_data_pairs(data_dir)
    if not pairs:
        print("[ERROR] No matched R-{T}K.dat / hall-{T}K.dat pairs found.")
        sys.exit(1)

    print(f"\nFound {len(pairs)} temperature(s):")
    for temp_val, temp_str, rxx_path, hall_path in pairs:
        print(f"  {temp_str}: R={os.path.basename(rxx_path)}, Hall={os.path.basename(hall_path)}")

    # Create output directory
    output_dir = os.path.join(data_dir, 'results')
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    # Process each temperature
    results = []
    for idx, (temp_val, temp_str, rxx_path, hall_path) in enumerate(pairs):
        print(f"\n{'='*60}")
        print(f"  [{idx+1}/{len(pairs)}] Fitting T = {temp_str}")
        print(f"{'='*60}")
        try:
            result = fit_single_temperature(hall_path, rxx_path, temp_str, output_dir)
            results.append(result)
            print(f"  => OK  R2(xy)={result['r2_xy']:.4f}  R2(xx)={result['r2_xx']:.4f}")
            print(f"  => Saved: {os.path.basename(result['out_dat'])}, {os.path.basename(result['out_png'])}")
        except Exception as e:
            print(f"  => FAILED: {e}")
            traceback.print_exc()

    # Export summary
    export_summary(results, output_dir)

    print(f"\nBatch processing complete. {len(results)}/{len(pairs)} temperature(s) fitted successfully.")


if __name__ == "__main__":
    main()
