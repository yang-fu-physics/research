import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit, differential_evolution
from tkinter import Tk, filedialog
import os

# Physical constants
e_charge = 1.602176634e-19  # Elementary charge in C

def two_band_rho_xy(B, n1, mu1, n2, mu2):
    """
    Two-band model for Hall resistivity.
    B: Magnetic field in Tesla (T)
    n1, n2: Carrier concentrations in m^-3 (negative for electrons, positive for holes)
    mu1, mu2: Carrier mobilities in m^2/(Vs)
    
    Returns:
    rho_xy: Hall resistivity in ohm*m
    """
    # Force mobilities to be positive for physical meaning
    mu1 = np.abs(mu1)
    mu2 = np.abs(mu2)
    
    # Conductivity tensor components
    s_xx = e_charge * np.abs(n1) * mu1 / (1 + (mu1 * B)**2) + e_charge * np.abs(n2) * mu2 / (1 + (mu2 * B)**2)
    s_xy = e_charge * n1 * (mu1**2) * B / (1 + (mu1 * B)**2) + e_charge * n2 * (mu2**2) * B / (1 + (mu2 * B)**2)
    
    # Hall resistivity
    rho_xy = s_xy / (s_xx**2 + s_xy**2)
    return rho_xy

def model_to_fit(B, n1_scale, mu1, n2_scale, mu2):
    """
    Scaled function for curve_fit.
    n_scale is carrier concentration in units of 1e20 m^-3.
    This helps the optimizer deal with values around 1 instead of 1e20.
    """
    n1 = n1_scale * 1e20
    n2 = n2_scale * 1e20
    return two_band_rho_xy(B, n1, mu1, n2, mu2)

def main():
    # Setup tkinter to open file dialog
    root = Tk()
    root.withdraw() # Hide the main window
    
    print("========================================")
    print("       Two-Band Model Fitting           ")
    print("========================================")
    
    # Prompt user for optional zero-field resistivity
    # This acts as a strong constraint on n1*mu1 + n2*mu2
    rho_xx_0_input = input("Enter zero-field resistivity rho_xx(0) in ohm cm (or press Enter to skip): ").strip()
    if rho_xx_0_input:
        try:
            rho_xx_0_cm = float(rho_xx_0_input)
            rho_xx_0_m = rho_xx_0_cm * 1e-2
            sigma_xx_0 = 1.0 / rho_xx_0_m
            print(f"Using constraint: rho_xx(0) = {rho_xx_0_cm:.4e} ohm cm")
        except ValueError:
            print("Invalid input for rho_xx(0). Constraint disabled.")
            sigma_xx_0 = None
    else:
        sigma_xx_0 = None
        
    print("Please select the data file containing B (T) and rho_xy (ohm cm)...")
    
    # Prompt user for file
    filepath = filedialog.askopenfilename(
        title="Select Data File (B in T, rho_xy in ohm cm)",
        filetypes=(("Data files", "*.txt *.csv *.dat"), ("All files", "*.*"))
    )
    
    if not filepath:
        print("No file selected. Exiting.")
        return
        
    print(f"Loading data from: {filepath}")
    
    try:
        # usecols=[0,1] avoids spurious NaN column from trailing tab in .dat files
        data = pd.read_csv(filepath, sep='\t', engine='python', comment='#',
                           header=0, usecols=[0, 1])
        data = data.dropna()
        # Drop duplicate B=0 rows (e.g. two zero-field points)
        data = data.drop_duplicates(subset=data.columns[0])
        B_data = data.iloc[:, 0].values.astype(float)
        rho_xy_ohm_cm = data.iloc[:, 1].values.astype(float)
    except Exception as ex:
        # Fallback to numpy loadtxt (assumes no header)
        try:
            data = np.loadtxt(filepath)
            # Remove duplicate rows based on first column
            _, unique_idx = np.unique(data[:, 0], return_index=True)
            data = data[unique_idx]
            B_data = data[:, 0]
            rho_xy_ohm_cm = data[:, 1]
        except Exception as ex2:
            print(f"Error loading file. Make sure it contains at least two numerical columns.\nPandas error: {ex}\nNumpy error: {ex2}")
            return
            
    # Convert rho_xy from ohm cm to ohm m (SI units)
    rho_xy_ohm_m = rho_xy_ohm_cm * 1e-2
    
    # ---------------- INITIAL GUESSES ----------------
    # Estimate net carrier density from low-field linear slope: rho_xy ~ B/(n_net * e)
    # Use points with |B| between 0.3 and 1.5 T for a robust slope estimate
    mask_lf = (np.abs(B_data) > 0.3) & (np.abs(B_data) < 1.5)
    if mask_lf.sum() >= 4:
        coeffs = np.polyfit(B_data[mask_lf], rho_xy_ohm_m[mask_lf], 1)
        slope_ohm_m_per_T = coeffs[0]   # drho_xy/dB at low field
    else:
        # fallback: use outermost points
        slope_ohm_m_per_T = (rho_xy_ohm_m[-1] - rho_xy_ohm_m[0]) / (B_data[-1] - B_data[0])
    
    # In single-band limit: slope = 1/(n*e)  ->  n_guess = 1/(e * |slope|)
    n_guess_m3 = 1.0 / (e_charge * abs(slope_ohm_m_per_T))
    n_sign = -1.0 if slope_ohm_m_per_T < 0 else 1.0  # sign of dominant carrier
    n_scale_guess = n_sign * n_guess_m3 / 1e20  # in units of 1e20 m^-3
    
    # Mobility guess: mu*B_knee ~ 1;  estimate B_knee from where curvature is most visible
    # default to 0.5 m^2/Vs which works for B_knee ~ 2T
    mu_guess = 0.5
    
    # Initial parameters for the fit: [n1_scale, mu1, n2_scale, mu2]
    # n_scale = concentration / 1e20  (negative = electrons, positive = holes)
    # Two-electron-band model: both n1, n2 are negative (electrons)
    n_abs = abs(n_scale_guess)
    p0 = [-n_abs, mu_guess, -n_abs * 0.8, mu_guess * 0.3]
    print(f"Auto-estimated p0 (two electrons): n1_scale={p0[0]:.2f}, mu1={p0[1]:.3f}, "
          f"n2_scale={p0[2]:.2f}, mu2={p0[3]:.3f}")
    
    # Search bounds for differential_evolution: both electrons
    # n_scale (in 1e20 m^-3): allow a broad range from data-estimated n
    n_abs = abs(n_scale_guess)
    n_lo = max(n_abs * 0.001, 1.0)    # at least 1e20 m^-3
    n_hi = n_abs * 1000
    bounds_de = [
        (-n_hi, -n_lo),   # n1_scale: electron (negative)
        (1e-4,  1e3),     # mu1  [m^2/Vs]
        (-n_hi, -n_lo),   # n2_scale: electron (negative)
        (1e-4,  1e3),     # mu2  [m^2/Vs]
    ]

    def residual_de(params):
        try:
            pred = model_to_fit(B_data, *params)
            err_rxy = np.sum((pred - rho_xy_ohm_m)**2)
            
            if sigma_xx_0 is not None:
                # Calculate sigma_xx(B=0) for these params
                n1s, mu1, n2s, mu2 = params
                n1, n2 = n1s * 1e20, n2s * 1e20
                sigma_xx_pred = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2
                # Weight the constraint heavily relative to the rxy residual
                weight = 100 * np.sum((rho_xy_ohm_m - np.mean(rho_xy_ohm_m))**2) / (sigma_xx_0**2)
                err_constraint = weight * (sigma_xx_pred - sigma_xx_0)**2
                return err_rxy + err_constraint
            return err_rxy
        except Exception:
            return 1e30

    print("\nRunning global optimization (differential_evolution)...")
    de_result = differential_evolution(
        residual_de, bounds_de, seed=42, maxiter=2000, tol=1e-14, workers=1,
        mutation=(0.5, 1.5), recombination=0.9, popsize=15
    )
    p0_refined = de_result.x
    print(f"Global optimum found  (fun={de_result.fun:.3e})")

    print("Refining with curve_fit...")
    bounds_cf = ([-np.inf, 1e-5, -np.inf, 1e-5], [np.inf, 1e3, np.inf, 1e3])
    try:
        if sigma_xx_0 is not None:
            # Joint fitting for curve_fit: append B=0 constraint
            B_fit_data = np.append(B_data, np.array([0.0]))
            rho_fit_target = np.append(rho_xy_ohm_m, np.array([1.0 / sigma_xx_0]))
            
            def combined_model(B_array, n1s, mu1, n2s, mu2):
                B_real = B_array[:-1]  # all except the last fake B=0 point
                rho_xy_pred = model_to_fit(B_real, n1s, mu1, n2s, mu2)
                # constraint portion
                n1, n2 = n1s * 1e20, n2s * 1e20
                sigma_xx_pred = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2
                rho_xx_pred = 1.0 / sigma_xx_pred
                return np.append(rho_xy_pred, rho_xx_pred)
            
            # Use high weight for the last point (constraint)
            sigma = np.ones(len(B_fit_data))
            sigma[-1] = 1e-8
            popt, pcov = curve_fit(combined_model, B_fit_data, rho_fit_target,
                                   p0=p0_refined, bounds=bounds_cf, sigma=sigma, maxfev=200000,
                                   ftol=1e-14, xtol=1e-14, gtol=1e-14)
        else:
            popt, pcov = curve_fit(model_to_fit, B_data, rho_xy_ohm_m,
                                   p0=p0_refined, bounds=bounds_cf, maxfev=200000,
                                   ftol=1e-14, xtol=1e-14, gtol=1e-14)
        
        # Extract fitted parameters properly scaled
        n1 = popt[0] * 1e20
        mu1 = popt[1]
        n2 = popt[2] * 1e20
        mu2 = popt[3]

        # Extract standard errors from covariance matrix
        perr = np.sqrt(np.diag(pcov))
        n1_err = perr[0] * 1e20
        mu1_err = perr[1]
        n2_err = perr[2] * 1e20
        mu2_err = perr[3]
        
        print("\n=== Fit Results (SI Units) ===")
        print(f"Carrier 1 (n1): {n1:.4e} ± {n1_err:.4e} m^-3 (Type: {'Hole' if n1 > 0 else 'Electron'})")
        print(f"Mobility 1 (mu1): {mu1:.4e} ± {mu1_err:.4e} m^2/(V·s)")
        print(f"Carrier 2 (n2): {n2:.4e} ± {n2_err:.4e} m^-3 (Type: {'Hole' if n2 > 0 else 'Electron'})")
        print(f"Mobility 2 (mu2): {mu2:.4e} ± {mu2_err:.4e} m^2/(V·s)")
        
        if sigma_xx_0 is not None:
            sigma_xx_fit = e_charge * abs(n1) * mu1 + e_charge * abs(n2) * mu2
            rho_xx_fit_cm = 1.0 / sigma_xx_fit * 100
            print(f"--- Constraint Check ---")
            print(f"Target rho_xx(0): {1.0 / sigma_xx_0 * 100:.4e} ohm cm")
            print(f"Fitted rho_xx(0): {rho_xx_fit_cm:.4e} ohm cm")
            
        print("==============================\n")
        
        # Generate fitted curve for plotting
        B_fit = np.linspace(min(B_data), max(B_data), 500)
        rho_xy_fit_m = model_to_fit(B_fit, *popt)
        rho_xy_fit_cm = rho_xy_fit_m * 100 # Convert back to ohm cm
        
        # Calculate R-squared or some goodness of fit proxy (excluding fake point if used)
        residuals = rho_xy_ohm_m - model_to_fit(B_data, *popt)
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((rho_xy_ohm_m - np.mean(rho_xy_ohm_m))**2)
        r_squared = 1 - (ss_res / ss_tot)
        print(f"R-squared: {r_squared:.4f}")

        # Plot raw data and fitted curve
        plt.figure(figsize=(8, 6))
        
        # Plot styling
        plt.scatter(B_data, rho_xy_ohm_cm, color='black', marker='o', facecolors='none', s=15, label='Raw Data')
        plt.plot(B_fit, rho_xy_fit_cm, color='red', linewidth=2, label='Two-band Fit')
        
        plt.xlabel('Magnetic Field $B$ (T)', fontsize=14, fontweight='bold')
        plt.ylabel('Hall Resistivity $\\rho_{xy}$ ($\\Omega\\cdot$cm)', fontsize=14, fontweight='bold')
        plt.title('Two-Band Model Fit', fontsize=16, fontweight='bold')
        
        # Add fit text to the plot
        fit_info = (
            f"Carrier 1 ({'h' if n1 > 0 else 'e'}): $n_1$ = ({n1:.2e} $\\pm$ {n1_err:.2e}) m$^{{-3}}$, $\\mu_1$ = {mu1:.4e} $\\pm$ {mu1_err:.1e} m$^2$/Vs\n"
            f"Carrier 2 ({'h' if n2 > 0 else 'e'}): $n_2$ = ({n2:.2e} $\\pm$ {n2_err:.2e}) m$^{{-3}}$, $\\mu_2$ = {mu2:.4e} $\\pm$ {mu2_err:.1e} m$^2$/Vs\n"
        )
        if sigma_xx_0 is not None:
            fit_info += f"Constrained $\\rho_{{xx}}(0)$: {rho_xx_fit_cm:.2e} $\\Omega\\cdot$cm\n"
        fit_info += f"$R^2$ = {r_squared:.4f}"
        
        # Place text box in the upper or lower corner
        plt.annotate(fit_info, xy=(0.03, 0.95), xycoords='axes fraction', 
                     fontsize=11, color='blue',
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8),
                     verticalalignment='top')
        
        plt.legend(fontsize=12, loc='lower right')
        plt.grid(True, linestyle='--', alpha=0.6)
        
        # Make ticks larger
        plt.xticks(fontsize=12)
        plt.yticks(fontsize=12)
        
        plt.tight_layout()
        
        # --- Export Data to File ---
        try:
            # Construct output filename based on input
            base_name = os.path.splitext(filepath)[0]
            out_filename = base_name + '_fit_result.dat'
            
            with open(out_filename, 'w') as f:
                f.write("# Two-Band Model Fit Results\n")
                f.write(f"# Input file: {filepath}\n")
                f.write(f"# R-squared: {r_squared:.6f}\n")
                if sigma_xx_0 is not None:
                    f.write(f"# Constrained rho_xx(0): {rho_xx_fit_cm:.6e} ohm cm\n")
                f.write("# --- Parameters ---\n")
                f.write(f"# n1 (m^-3) = {n1:.6e} +/- {n1_err:.6e} ({'Hole' if n1 > 0 else 'Electron'})\n")
                f.write(f"# mu1 (m^2/Vs) = {mu1:.6e} +/- {mu1_err:.6e}\n")
                f.write(f"# n2 (m^-3) = {n2:.6e} +/- {n2_err:.6e} ({'Hole' if n2 > 0 else 'Electron'})\n")
                f.write(f"# mu2 (m^2/Vs) = {mu2:.6e} +/- {mu2_err:.6e}\n")
                f.write("# ------------------\n")
                f.write("# B(T)\trho_xy_raw(ohm_cm)\trho_xy_fit(ohm_cm)\n")
                
                # To align raw and fit data, we calculate the fit *at the raw B points*
                rho_xy_fit_at_raw_m = model_to_fit(B_data, *popt)
                rho_xy_fit_at_raw_cm = rho_xy_fit_at_raw_m * 100
                
                for i in range(len(B_data)):
                    f.write(f"{B_data[i]:.6f}\t{rho_xy_ohm_cm[i]:.6e}\t{rho_xy_fit_at_raw_cm[i]:.6e}\n")
            
            print(f"\n=> Fit results and data exported to: {out_filename}")
        except Exception as e:
            print(f"\nWarning: Could not save output data to file. ({e})")
        
        plt.show()
        
    except Exception as e:
        print(f"Fitting failed: {e}")
        print("Tip: If the fit fails, try modifying the initial guesses (p0) in the script based on the physical properties of your material.")

if __name__ == "__main__":
    main()
