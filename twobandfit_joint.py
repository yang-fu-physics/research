import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, differential_evolution
from tkinter import Tk, filedialog
import os

# Physical constants
e_charge = 1.602176634e-19  # Elementary charge in C

# ===== Two-Band Model Functions =====

def two_band_conductivity(B, n1, mu1, n2, mu2):
    """Compute sigma_xx and sigma_xy for the two-band model."""
    mu1 = np.abs(mu1)
    mu2 = np.abs(mu2)
    s_xx = (e_charge * np.abs(n1) * mu1 / (1 + (mu1 * B)**2)
            + e_charge * np.abs(n2) * mu2 / (1 + (mu2 * B)**2))
    s_xy = (e_charge * n1 * mu1**2 * B / (1 + (mu1 * B)**2)
            + e_charge * n2 * mu2**2 * B / (1 + (mu2 * B)**2))
    return s_xx, s_xy

def two_band_rho_xx(B, n1, mu1, n2, mu2):
    """Longitudinal resistivity rho_xx in ohm*m."""
    s_xx, s_xy = two_band_conductivity(B, n1, mu1, n2, mu2)
    return s_xx / (s_xx**2 + s_xy**2)

def two_band_rho_xy(B, n1, mu1, n2, mu2):
    """Hall resistivity rho_xy in ohm*m."""
    s_xx, s_xy = two_band_conductivity(B, n1, mu1, n2, mu2)
    return s_xy / (s_xx**2 + s_xy**2)

def model_rho_xx(B, n1s, mu1, n2s, mu2):
    """Scaled rho_xx: n_scale in units of 1e20 m^-3."""
    return two_band_rho_xx(B, n1s * 1e20, mu1, n2s * 1e20, mu2)

def model_rho_xy(B, n1s, mu1, n2s, mu2):
    """Scaled rho_xy: n_scale in units of 1e20 m^-3."""
    return two_band_rho_xy(B, n1s * 1e20, mu1, n2s * 1e20, mu2)


# ===== Data Loading =====

def load_single_dat(filepath, col_B=0, col_rho=1):
    """Load a .dat file, return (B, rho) arrays."""
    data = pd.read_csv(filepath, sep='\t', header=0,
                       usecols=[col_B, col_rho]).dropna()
    data = data.drop_duplicates(subset=data.columns[0])
    B   = data.iloc[:, 0].values.astype(float)
    rho = data.iloc[:, 1].values.astype(float)
    return B, rho


def align_data(B_xx, rho_xx_cm, B_xy, rho_xy_cm):
    """
    Interpolate rho_xy onto the B grid of rho_xx (or vice versa)
    and return a common, ordered B grid with both arrays.
    """
    B_min = max(B_xx.min(), B_xy.min())
    B_max = min(B_xx.max(), B_xy.max())

    # Use the denser grid as reference
    mask_xx = (B_xx >= B_min) & (B_xx <= B_max)
    mask_xy = (B_xy >= B_min) & (B_xy <= B_max)
    if mask_xx.sum() >= mask_xy.sum():
        B_common = B_xx[mask_xx]
        rho_xx_aligned = rho_xx_cm[mask_xx]
        rho_xy_aligned = np.interp(B_common, B_xy, rho_xy_cm)
    else:
        B_common = B_xy[mask_xy]
        rho_xy_aligned = rho_xy_cm[mask_xy]
        rho_xx_aligned = np.interp(B_common, B_xx, rho_xx_cm)

    return B_common, rho_xx_aligned, rho_xy_aligned


# ===== Initial Parameter Estimation =====

def estimate_p0(B, rho_xy_cm, rho_xx_cm):
    """Auto-estimate initial parameters from the data."""
    # Low-field Hall slope -> dominant carrier density
    mask = (np.abs(B) > 0.3) & (np.abs(B) < 1.5)
    if mask.sum() > 4:
        slope = np.polyfit(B[mask], rho_xy_cm[mask] * 1e-2, 1)[0]
    else:
        slope = (rho_xy_cm[-1] - rho_xy_cm[0]) / (B[-1] - B[0]) * 1e-2

    n_guess_m3 = 1.0 / (e_charge * abs(slope))
    n_sign = -1.0 if slope < 0 else 1.0
    n_scale = n_sign * n_guess_m3 / 1e20

    # rho_xx(0) -> total sigma -> mobility guess
    rho_xx_0_m = rho_xx_cm[np.argmin(np.abs(B))] * 1e-2
    sigma_0 = 1.0 / rho_xx_0_m
    mu_guess = 0.5

    n_abs = abs(n_scale)
    p0 = [n_sign * n_abs,     mu_guess,
          n_sign * n_abs * 0.8, mu_guess * 0.3]
    return p0, n_abs, sigma_0


# ===== Joint Fitting Core =====

def joint_residual(params, B, rho_xx_m, rho_xy_m, w_xx, w_xy):
    """
    Weighted joint residual for differential_evolution.
    w_xx, w_xy are inverse-variance normalisation factors.
    """
    try:
        n1s, mu1, n2s, mu2 = params
        pred_xx = model_rho_xx(B, n1s, mu1, n2s, mu2)
        pred_xy = model_rho_xy(B, n1s, mu1, n2s, mu2)
        return (w_xx * np.sum((pred_xx - rho_xx_m)**2)
                + w_xy * np.sum((pred_xy - rho_xy_m)**2))
    except Exception:
        return 1e30


def joint_model(B_doubled, n1s, mu1, n2s, mu2):
    """
    Combined model for curve_fit.
    B_doubled = [B, B] (first half for rho_xx, second half for rho_xy).
    sigma_joint contains the per-point uncertainties (for weighting).
    """
    N = len(B_doubled) // 2
    B = B_doubled[:N]
    xx = model_rho_xx(B, n1s, mu1, n2s, mu2)
    xy = model_rho_xy(B, n1s, mu1, n2s, mu2)
    return np.concatenate([xx, xy])


def run_fit(B, rho_xx_m, rho_xy_m):
    """Run differential_evolution + curve_fit joint optimisation."""
    # Normalisation weights (inverse variance)
    var_xx = np.var(rho_xx_m)
    var_xy = np.var(rho_xy_m)
    w_xx = 1.0 / var_xx if var_xx > 0 else 1.0
    w_xy = 1.0 / var_xy if var_xy > 0 else 1.0

    # Estimate initial guess
    rho_xx_cm = rho_xx_m * 100
    rho_xy_cm = rho_xy_m * 100
    p0, n_abs, _ = estimate_p0(B, rho_xy_cm, rho_xx_cm)

    n_hi = max(n_abs * 1000, 1000.0)
    bounds_de = [
        (-n_hi, n_hi),
        (1e-5, 1e3),
        (-n_hi, n_hi),
        (1e-5, 1e3),
    ]

    print("\nRunning global optimisation (differential_evolution)...")
    de_res = differential_evolution(
        joint_residual,
        bounds_de,
        args=(B, rho_xx_m, rho_xy_m, w_xx, w_xy),
        seed=42, maxiter=2000, tol=1e-14,
        mutation=(0.5, 1.5), recombination=0.9, popsize=15, workers=1
    )
    print(f"Global optimum found  (fun={de_res.fun:.3e})")

    # Refine with curve_fit using weighted points
    print("Refining with curve_fit...")
    B_doubled = np.concatenate([B, B])
    y_joint   = np.concatenate([rho_xx_m, rho_xy_m])

    # sigma: standard deviation per point (smaller -> tighter constraint)
    sigma_joint = np.concatenate([
        np.full(len(B), np.sqrt(var_xx)),
        np.full(len(B), np.sqrt(var_xy))
    ])

    bounds_cf = (
        [-np.inf, 1e-5, -np.inf, 1e-5],
        [ np.inf, 1e3,   np.inf, 1e3]
    )
    popt, pcov = curve_fit(
        joint_model, B_doubled, y_joint,
        p0=de_res.x, bounds=bounds_cf,
        sigma=sigma_joint, absolute_sigma=True,
        maxfev=200000, ftol=1e-14, xtol=1e-14, gtol=1e-14
    )
    perr = np.sqrt(np.diag(pcov))
    return popt, perr


# ===== Main =====

def main():
    root = Tk()
    root.withdraw()

    print("=" * 48)
    print("   Two-Band Joint Fit: rho_xx(B) + rho_xy(B)  ")
    print("=" * 48)

    # --- Load rho_xx file ---
    print("\nSelect file containing B (T) and rho_xx (ohm cm)...")
    fp_xx = filedialog.askopenfilename(
        title="Select rho_xx data file",
        filetypes=(("Data files", "*.dat *.txt *.csv"), ("All files", "*.*"))
    )
    if not fp_xx:
        print("No file selected. Exiting.")
        return
    B_xx, rho_xx_cm = load_single_dat(fp_xx, col_B=0, col_rho=1)
    print(f"Loaded rho_xx from: {fp_xx}  ({len(B_xx)} points)")

    # --- Load rho_xy file ---
    print("Select file containing B (T) and rho_xy (ohm cm)...")
    fp_xy = filedialog.askopenfilename(
        title="Select rho_xy (Hall) data file",
        filetypes=(("Data files", "*.dat *.txt *.csv"), ("All files", "*.*"))
    )
    if not fp_xy:
        print("No file selected. Exiting.")
        return
    B_xy, rho_xy_cm = load_single_dat(fp_xy, col_B=0, col_rho=1)
    print(f"Loaded rho_xy from: {fp_xy}  ({len(B_xy)} points)")

    # --- Align grids ---
    B, rho_xx_cm, rho_xy_cm = align_data(B_xx, rho_xx_cm, B_xy, rho_xy_cm)
    print(f"\nData aligned: {len(B)} common B points "
          f"[{B.min():.2f} T, {B.max():.2f} T]")

    # Convert to SI (ohm m)
    rho_xx_m = rho_xx_cm * 1e-2
    rho_xy_m = rho_xy_cm * 1e-2

    # --- Run fit ---
    try:
        popt, perr = run_fit(B, rho_xx_m, rho_xy_m)

        # Extract parameters
        n1 = popt[0] * 1e20;  mu1 = popt[1]
        n2 = popt[2] * 1e20;  mu2 = popt[3]
        n1_err = perr[0] * 1e20; mu1_err = perr[1]
        n2_err = perr[2] * 1e20; mu2_err = perr[3]

        # Compute fitted rho_xx(0)
        sxx0 = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2
        rho_xx_0_fit_cm = 1.0 / sxx0 * 100

        # R² for each channel
        res_xx = rho_xx_m - model_rho_xx(B, *popt)
        res_xy = rho_xy_m - model_rho_xy(B, *popt)
        r2_xx = 1 - np.sum(res_xx**2) / np.sum((rho_xx_m - rho_xx_m.mean())**2)
        r2_xy = 1 - np.sum(res_xy**2) / np.sum((rho_xy_m - rho_xy_m.mean())**2)

        print("\n=== Fit Results (SI Units) ===")
        print(f"Carrier 1 (n1): {n1:.4e} \u00b1 {n1_err:.4e} m^-3 "
              f"(Type: {'Hole' if n1 > 0 else 'Electron'})")
        print(f"Mobility 1 (mu1): {mu1:.4e} \u00b1 {mu1_err:.4e} m^2/(V\u00b7s)")
        print(f"Carrier 2 (n2): {n2:.4e} \u00b1 {n2_err:.4e} m^-3 "
              f"(Type: {'Hole' if n2 > 0 else 'Electron'})")
        print(f"Mobility 2 (mu2): {mu2:.4e} \u00b1 {mu2_err:.4e} m^2/(V\u00b7s)")
        print(f"--- Fitted rho_xx(0): {rho_xx_0_fit_cm:.6e} ohm cm ---")
        print(f"R\u00b2 (rho_xx): {r2_xx:.4f}")
        print(f"R\u00b2 (rho_xy): {r2_xy:.4f}")

        # --- Plot ---
        B_smooth = np.linspace(B.min(), B.max(), 600)
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle("Two-Band Joint Fit", fontsize=16, fontweight='bold')

        for ax, (y_raw_cm, pred_fn, ylabel, r2) in zip(axes, [
            (rho_xx_cm,
             lambda Bs: model_rho_xx(Bs, *popt) * 100,
             r'$\rho_{{xx}}$ ($\Omega\cdot$cm)',
             r2_xx),
            (rho_xy_cm,
             lambda Bs: model_rho_xy(Bs, *popt) * 100,
             r'$\rho_{{xy}}$ ($\Omega\cdot$cm)',
             r2_xy),
        ]):
            ax.scatter(B, y_raw_cm, color='black', marker='o',
                       facecolors='none', s=10, label='Raw Data')
            ax.plot(B_smooth, pred_fn(B_smooth), 'r-', lw=2, label='Two-band Fit')
            ax.set_xlabel('Magnetic Field $B$ (T)', fontsize=13)
            ax.set_ylabel(ylabel, fontsize=13)
            ax.tick_params(labelsize=11)
            ax.legend(fontsize=11, loc='best')
            ax.grid(True, ls='--', alpha=0.5)
            ax.annotate(f'$R^2$ = {r2:.4f}', xy=(0.05, 0.95),
                        xycoords='axes fraction', fontsize=11, color='blue',
                        va='top')

        # Add parameters text on the Hall plot (right panel)
        type1 = 'h' if n1 > 0 else 'e'
        type2 = 'h' if n2 > 0 else 'e'
        info = (f"Carrier 1 ({type1}): $n_1$=({n1:.2e}$\\pm${n1_err:.1e}) m$^{{-3}}$, "
                f"$\\mu_1$={mu1:.3e}$\\pm${mu1_err:.1e} m$^2$/Vs\n"
                f"Carrier 2 ({type2}): $n_2$=({n2:.2e}$\\pm${n2_err:.1e}) m$^{{-3}}$, "
                f"$\\mu_2$={mu2:.3e}$\\pm${mu2_err:.1e} m$^2$/Vs\n"
                f"Fitted $\\rho_{{xx}}(0)$={rho_xx_0_fit_cm:.4e} $\\Omega\\cdot$cm")
        axes[1].annotate(info, xy=(0.03, 0.05), xycoords='axes fraction',
                         fontsize=9.5, color='blue', va='bottom',
                         bbox=dict(boxstyle='round,pad=0.3', fc='white',
                                   ec='gray', alpha=0.8))

        plt.tight_layout()

        # --- Export ---
        base_name = os.path.splitext(fp_xx)[0]
        out_dat  = base_name + '_joint_fit_result.dat'
        out_png  = base_name + '_joint_fit_plot.png'

        try:
            # Build fit at raw B points
            fit_xx = model_rho_xx(B, *popt) * 100
            fit_xy = model_rho_xy(B, *popt) * 100
            with open(out_dat, 'w') as f:
                f.write("# Two-Band Joint Fit Results\n")
                f.write(f"# rho_xx file: {fp_xx}\n")
                f.write(f"# rho_xy file: {fp_xy}\n")
                f.write(f"# R2(rho_xx)={r2_xx:.6f}  R2(rho_xy)={r2_xy:.6f}\n")
                f.write(f"# Fitted rho_xx(0) = {rho_xx_0_fit_cm:.8e} ohm cm\n")
                f.write("# --- Parameters ---\n")
                f.write(f"# n1 (m^-3) = {n1:.6e} +/- {n1_err:.6e} "
                        f"({'Hole' if n1 > 0 else 'Electron'})\n")
                f.write(f"# mu1 (m^2/Vs) = {mu1:.6e} +/- {mu1_err:.6e}\n")
                f.write(f"# n2 (m^-3) = {n2:.6e} +/- {n2_err:.6e} "
                        f"({'Hole' if n2 > 0 else 'Electron'})\n")
                f.write(f"# mu2 (m^2/Vs) = {mu2:.6e} +/- {mu2_err:.6e}\n")
                f.write("# ------------------\n")
                f.write("# B(T)\trho_xx_raw(ohm_cm)\trho_xx_fit(ohm_cm)"
                        "\trho_xy_raw(ohm_cm)\trho_xy_fit(ohm_cm)\n")
                for i in range(len(B)):
                    f.write(f"{B[i]:.6f}\t{rho_xx_cm[i]:.6e}\t{fit_xx[i]:.6e}"
                            f"\t{rho_xy_cm[i]:.6e}\t{fit_xy[i]:.6e}\n")
            print(f"\n=> Data exported to: {out_dat}")
        except Exception as e:
            print(f"\nWarning: could not save data. ({e})")

        try:
            plt.savefig(out_png, dpi=300, bbox_inches='tight')
            print(f"=> Plot saved to: {out_png}")
        except Exception as e:
            print(f"\nWarning: could not save plot. ({e})")

        plt.show()

    except Exception as e:
        print(f"Fitting failed: {e}")
        raise


if __name__ == "__main__":
    main()
