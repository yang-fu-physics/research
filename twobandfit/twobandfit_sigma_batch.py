"""
twobandfit_sigma_batch.py

Batch processing script for two-band conductivity fitting.
- Scans a data folder (default: rawdata/) for paired R-{T}K.dat and hall-{T}K.dat files
- Converts rho_xx / rho_xy -> sigma_xx / sigma_xy, then fits BOTH simultaneously
- Exports per-temperature fit results (data + plot)
- Generates a summary table and summary plots of all fitted parameters vs temperature

Usage:
    python twobandfit_sigma_batch.py                      # scan rawdata/
    python twobandfit_sigma_batch.py path/to/data_folder  # specify folder
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

# ===== Import core fitting function from single-file script =====
# (Keep models self-contained here to avoid tight coupling)

def two_band_sigma(B, n1, mu1, n2, mu2):
    mu1, mu2 = abs(mu1), abs(mu2)
    s_xx = (e_charge * abs(n1) * mu1 / (1 + (mu1 * B)**2)
            + e_charge * abs(n2) * mu2 / (1 + (mu2 * B)**2))
    s_xy = (e_charge * n1 * mu1**2 * B / (1 + (mu1 * B)**2)
            + e_charge * n2 * mu2**2 * B / (1 + (mu2 * B)**2))
    return s_xx, s_xy

def model_sigma_xx(B, n1s, mu1, n2s, mu2):
    s_xx, _ = two_band_sigma(B, n1s * 1e20, mu1, n2s * 1e20, mu2)
    return s_xx

def model_sigma_xy(B, n1s, mu1, n2s, mu2):
    _, s_xy = two_band_sigma(B, n1s * 1e20, mu1, n2s * 1e20, mu2)
    return s_xy

def rho_to_sigma(rho_xx, rho_xy):
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
        n_pts = round((B_max - B_min) / min_spacing)
    where min_spacing is the finest adjacent-point spacing among all B arrays
    (clipped to the common B range). This preserves the resolution of the
    densest dataset without over- or under-sampling.
    """
    pairs = [(arrays_B_and_data[i], arrays_B_and_data[i + 1])
             for i in range(0, len(arrays_B_and_data), 2)]

    B_min = max(B.min() for B, _ in pairs)
    B_max = min(B.max() for B, _ in pairs)

    def min_spacing_in(B):
        mask = (B >= B_min) & (B <= B_max)
        B_in = np.sort(B[mask])
        if len(B_in) < 2:
            return B_max - B_min
        return np.min(np.diff(B_in))

    finest_spacing = min(min_spacing_in(B) for B, _ in pairs)
    n_pts = max(10, round((B_max - B_min) / finest_spacing) + 1)

    B_uniform = np.linspace(B_min, B_max, n_pts)
    resampled = []
    for B, data in pairs:
        sort_idx = np.argsort(B)
        resampled.append(np.interp(B_uniform, B[sort_idx], data[sort_idx]))
    return (B_uniform, *resampled)

# ===== Core Fitting Function =====

def fit_two_band_sigma(B_data, sigma_xx_data, sigma_xy_data):
    """Fit sigma_xx and sigma_xy simultaneously. Returns popt, perr, r2_xx, r2_xy."""

    mask = (np.abs(B_data) > 0.3) & (np.abs(B_data) < 1.5)
    if mask.sum() > 4:
        slope = np.polyfit(B_data[mask], sigma_xy_data[mask], 1)[0]
    else:
        slope = (sigma_xy_data[-1] - sigma_xy_data[0]) / (B_data[-1] - B_data[0] + 1e-30)

    sigma0 = np.max(np.abs(sigma_xx_data))
    n_sign = -1.0 if slope < 0 else 1.0
    mu_guess = abs(slope) / (sigma0 + 1e-30)
    mu_guess = np.clip(mu_guess, 1e-4, 100.0)
    n_guess  = sigma0 / (e_charge * mu_guess)
    n_scale  = n_sign * n_guess / 1e20
    n_abs = max(abs(n_scale), 1e-3)

    scale_xx = np.std(sigma_xx_data) if np.std(sigma_xx_data) > 0 else 1.0
    scale_xy = np.std(sigma_xy_data) if np.std(sigma_xy_data) > 0 else 1.0

    def residual(params):
        try:
            sx_pred = model_sigma_xx(B_data, *params)
            sy_pred = model_sigma_xy(B_data, *params)
            return (np.sum(((sx_pred - sigma_xx_data) / scale_xx)**2) +
                    np.sum(((sy_pred - sigma_xy_data) / scale_xy)**2))
        except Exception:
            return 1e30

    n_hi = max(n_abs * 1000, 1000.0)
    bounds_de = [(-n_hi, n_hi), (1e-5, 1e3), (-n_hi, n_hi), (1e-5, 1e3)]

    de_res = differential_evolution(
        residual, bounds_de, seed=42, maxiter=3000, tol=1e-14,
        mutation=(0.5, 1.5), recombination=0.9, popsize=15, workers=1
    )

    bounds_min = [(None, None), (1e-5, 1e3), (None, None), (1e-5, 1e3)]
    opt_res = minimize(residual, x0=de_res.x, method='L-BFGS-B',
                       bounds=bounds_min, options={'maxiter': 200000, 'ftol': 1e-15})
    popt = opt_res.x

    eps = 1e-8
    n_params = len(popt)
    hessian = np.zeros((n_params, n_params))
    for i in range(n_params):
        def grad_i(x, _i=i):
            return approx_fprime(x, residual, eps * np.ones(n_params))[_i]
        hessian[i] = approx_fprime(popt, grad_i, eps * np.ones(n_params))
    hessian = 0.5 * (hessian + hessian.T)
    n_pts = len(B_data)
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

# ===== File Discovery =====

def discover_data_pairs(data_dir):
    """
    Scan data_dir for paired R-{T}K.dat and hall-{T}K.dat files.
    Returns list of (temperature_float, temperature_str, rxx_path, hall_path)
    sorted by temperature.
    """
    hall_files = glob.glob(os.path.join(data_dir, 'hall-*.dat'))
    rxx_files  = glob.glob(os.path.join(data_dir, 'R-*.dat'))

    hall_temps = {}
    for f in hall_files:
        basename = os.path.basename(f)
        m = re.match(r'hall-(.+)\.dat$', basename, re.IGNORECASE)
        if m:
            temp_str = m.group(1)
            try:
                float(temp_str.rstrip('Kk'))
                hall_temps[temp_str] = f
            except ValueError:
                pass

    rxx_temps = {}
    for f in rxx_files:
        basename = os.path.basename(f)
        m = re.match(r'R-(.+)\.dat$', basename, re.IGNORECASE)
        if m:
            temp_str = m.group(1)
            try:
                float(temp_str.rstrip('Kk'))
                rxx_temps[temp_str] = f
            except ValueError:
                pass

    pairs = []
    all_temps = set(hall_temps.keys()) | set(rxx_temps.keys())
    for temp_str in all_temps:
        if temp_str in hall_temps and temp_str in rxx_temps:
            pairs.append((float(temp_str.rstrip('Kk')), temp_str,
                          rxx_temps[temp_str], hall_temps[temp_str]))
        elif temp_str in hall_temps:
            print(f"  [WARNING] hall-{temp_str}.dat found but no matching R-{temp_str}.dat -- skipped")
        else:
            print(f"  [WARNING] R-{temp_str}.dat found but no matching hall-{temp_str}.dat -- skipped")

    pairs.sort(key=lambda x: x[0])
    return pairs

# ===== Single Temperature Fitting =====

def fit_single_temperature(hall_path, rxx_path, temp_str, output_dir):
    """
    Fit sigma_xx & sigma_xy for a single temperature.
    Returns dict of fit results, or None on failure.
    """
    # Load resistivity data (ohm cm)
    B_xy, rho_xy_cm = load_dat(hall_path, 0, 1)
    B_xx, rho_xx_cm = load_dat(rxx_path,  0, 1)

    # Convert to SI ohm m
    rho_xy_m = rho_xy_cm * 1e-2
    rho_xx_m = rho_xx_cm * 1e-2

    # Resample to common uniform B grid and invert to conductivity
    B_fit, rho_xx_fit, rho_xy_fit = resample_uniform(B_xx, rho_xx_m, B_xy, rho_xy_m)
    sigma_xx_data, sigma_xy_data = rho_to_sigma(rho_xx_fit, rho_xy_fit)

    # Reference sigma_xx(0) from rho_xx data
    idx_zero = np.argmin(np.abs(B_xx))
    sigma_xx_0_data = 1.0 / (rho_xx_cm[idx_zero] * 1e-2)  # S/m

    # Fit
    popt, perr, r2_xx, r2_xy = fit_two_band_sigma(B_fit, sigma_xx_data, sigma_xy_data)

    n1  = popt[0] * 1e20; mu1 = popt[1]
    n2  = popt[2] * 1e20; mu2 = popt[3]
    n1_err  = perr[0] * 1e20; mu1_err = perr[1]
    n2_err  = perr[2] * 1e20; mu2_err = perr[3]

    sigma_xx_0_fit = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2
    rho_xx_0_fit_cm = 1.0 / sigma_xx_0_fit * 100
    rho_xx_0_data_cm = rho_xx_cm[idx_zero]

    # ===== Plot =====
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
        f"$\\sigma_{{xx}}(0)$ fit={sigma_xx_0_fit:.3e} S/m\n"
        f"$\\sigma_{{xx}}(0)$ data={sigma_xx_0_data:.3e} S/m"
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle(f"Two-Band Conductivity Fit: T = {temp_str}", fontsize=15, fontweight='bold')

    ax_xx = axes[0]
    ax_xx.scatter(B_fit, sigma_xx_data, color='black', marker='o', facecolors='none',
                  s=12, label='From data ($\\sigma_{xx}$)')
    ax_xx.plot(B_smooth, sxx_smooth, 'b-', lw=2, label='Two-band Fit')
    ax_xx.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
    ax_xx.set_ylabel('$\\sigma_{xx}$ (S/m)', fontsize=13)
    ax_xx.legend(fontsize=11, loc='best')
    ax_xx.annotate(f'$R^2$ = {r2_xx:.4f}', xy=(0.05, 0.94), xycoords='axes fraction',
                   fontsize=11, color='blue', va='top')
    ax_xx.grid(True, ls='--', alpha=0.5)

    ax_xy = axes[1]
    ax_xy.scatter(B_fit, sigma_xy_data, color='black', marker='o', facecolors='none',
                  s=12, label='From data ($\\sigma_{xy}$)')
    ax_xy.plot(B_smooth, sxy_smooth, 'r-', lw=2, label='Two-band Fit')
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
    out_png = os.path.join(output_dir, f'{temp_str}_sigma_fit_plot.png')
    plt.savefig(out_png, dpi=300, bbox_inches='tight')
    plt.close(fig)

    # ===== Export data =====
    out_dat = os.path.join(output_dir, f'{temp_str}_sigma_fit_result.dat')
    sxx_at_data = model_sigma_xx(B_fit, *popt)
    sxy_at_data = model_sigma_xy(B_fit, *popt)

    with open(out_dat, 'w') as f:
        f.write(f"# Two-Band Conductivity Fit Results - T = {temp_str}\n")
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

    return {
        'temp_str': temp_str,
        'temp_val': float(temp_str.rstrip('Kk')),
        'n1': n1, 'n1_err': n1_err, 'mu1': mu1, 'mu1_err': mu1_err,
        'n2': n2, 'n2_err': n2_err, 'mu2': mu2, 'mu2_err': mu2_err,
        'r2_xx': r2_xx, 'r2_xy': r2_xy,
        'sigma_xx_0_data': sigma_xx_0_data, 'sigma_xx_0_fit': sigma_xx_0_fit,
        'rho_xx_0_data': rho_xx_0_data_cm, 'rho_xx_0_fit': rho_xx_0_fit_cm,
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

    results.sort(key=lambda r: r['temp_val'])

    # --- Summary Table ---
    summary_path = os.path.join(output_dir, 'batch_sigma_summary.dat')
    with open(summary_path, 'w') as f:
        f.write("# Two-Band Conductivity Fit Batch Summary\n")
        f.write("# Columns: T(K)\tn1(m^-3)\tn1_err\tType1\tmu1(m^2/Vs)\tmu1_err\t"
                "n2(m^-3)\tn2_err\tType2\tmu2(m^2/Vs)\tmu2_err\t"
                "R2_sxx\tR2_sxy\tsigma_xx(0)_data(S/m)\tsigma_xx(0)_fit(S/m)\n")
        for r in results:
            f.write(f"{r['temp_val']}\t{r['n1']:.6e}\t{r['n1_err']:.6e}\t{r['type1']}\t"
                    f"{r['mu1']:.6e}\t{r['mu1_err']:.6e}\t"
                    f"{r['n2']:.6e}\t{r['n2_err']:.6e}\t{r['type2']}\t"
                    f"{r['mu2']:.6e}\t{r['mu2_err']:.6e}\t"
                    f"{r['r2_xx']:.6f}\t{r['r2_xy']:.6f}\t"
                    f"{r['sigma_xx_0_data']:.6e}\t{r['sigma_xx_0_fit']:.6e}\n")
    print(f"\n=> Summary table saved: {summary_path}")

    # --- Console Summary ---
    print("\n" + "=" * 130)
    print("  BATCH CONDUCTIVITY FIT SUMMARY")
    print("=" * 130)
    header = (f"{'T(K)':>8s}  {'n1(m^-3)':>12s}  {'mu1(m^2/Vs)':>12s}  {'Type1':>8s}  "
              f"{'n2(m^-3)':>12s}  {'mu2(m^2/Vs)':>12s}  {'Type2':>8s}  "
              f"{'R2_sxx':>8s}  {'R2_sxy':>8s}")
    print(header)
    print("-" * 130)
    for r in results:
        print(f"{r['temp_val']:8.2f}  {r['n1']:12.4e}  {r['mu1']:12.4e}  {r['type1']:>8s}  "
              f"{r['n2']:12.4e}  {r['mu2']:12.4e}  {r['type2']:>8s}  "
              f"{r['r2_xx']:8.4f}  {r['r2_xy']:8.4f}")
    print("=" * 130)

    # --- Summary Plot ---
    if len(results) > 1:
        temps    = [r['temp_val'] for r in results]
        n1_vals  = [abs(r['n1'])  for r in results]
        n2_vals  = [abs(r['n2'])  for r in results]
        mu1_vals = [r['mu1'] for r in results]
        mu2_vals = [r['mu2'] for r in results]
        n1_errs  = [r['n1_err']  for r in results]
        n2_errs  = [r['n2_err']  for r in results]
        mu1_errs = [r['mu1_err'] for r in results]
        mu2_errs = [r['mu2_err'] for r in results]

        def cap_errors(vals, errs):
            err_lower = np.array(errs, dtype=float)
            mask_lower = err_lower >= np.array(vals)
            err_lower[mask_lower] = np.array(vals)[mask_lower] * 0.99
            err_upper = np.array(errs, dtype=float)
            mask_upper = err_upper > 100 * np.array(vals)
            err_upper[mask_upper] = 100 * np.array(vals)[mask_upper]
            return [err_lower, err_upper]

        n1_err_adj  = cap_errors(n1_vals,  n1_errs)
        n2_err_adj  = cap_errors(n2_vals,  n2_errs)
        mu1_err_adj = cap_errors(mu1_vals, mu1_errs)
        mu2_err_adj = cap_errors(mu2_vals, mu2_errs)

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle("Two-Band Conductivity Fit: Parameters vs Temperature",
                     fontsize=16, fontweight='bold')

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
        summary_png = os.path.join(output_dir, 'batch_sigma_summary_plot.png')
        plt.savefig(summary_png, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close(fig)
        print(f"=> Summary plot saved: {summary_png}")
    else:
        print("(Only 1 temperature -- skipping summary plot)")


# ===== Main =====

def main():
    print("=" * 60)
    print("   Two-Band Conductivity Fitting -- Batch Processing")
    print("=" * 60)

    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    else:
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rawdata')

    if not os.path.isdir(data_dir):
        print(f"[ERROR] Data directory not found: {data_dir}")
        sys.exit(1)

    print(f"\nScanning: {data_dir}")

    pairs = discover_data_pairs(data_dir)
    if not pairs:
        print("[ERROR] No matched R-{T}K.dat / hall-{T}K.dat pairs found.")
        sys.exit(1)

    print(f"\nFound {len(pairs)} temperature(s):")
    for temp_val, temp_str, rxx_path, hall_path in pairs:
        print(f"  {temp_str}: R={os.path.basename(rxx_path)}, Hall={os.path.basename(hall_path)}")

    output_dir = os.path.join(data_dir, 'results_sigma')
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    results = []
    for idx, (temp_val, temp_str, rxx_path, hall_path) in enumerate(pairs):
        print(f"\n{'='*60}")
        print(f"  [{idx+1}/{len(pairs)}] Fitting T = {temp_str}")
        print(f"{'='*60}")
        try:
            result = fit_single_temperature(hall_path, rxx_path, temp_str, output_dir)
            results.append(result)
            print(f"  => OK  R2(sxx)={result['r2_xx']:.4f}  R2(sxy)={result['r2_xy']:.4f}")
            print(f"  => Saved: {os.path.basename(result['out_dat'])}, {os.path.basename(result['out_png'])}")
        except Exception as e:
            print(f"  => FAILED: {e}")
            traceback.print_exc()

    export_summary(results, output_dir)

    print(f"\nBatch processing complete. {len(results)}/{len(pairs)} temperature(s) fitted successfully.")


if __name__ == "__main__":
    main()
