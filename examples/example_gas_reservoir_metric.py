"""
Example: Gas Reservoir Material Balance - Metric Units

This example demonstrates gas reservoir material balance calculations
with 4 pressure production points using metric units:
- Pressure in kgf/cm²
- Gas volumes in m³ (standard conditions)
- Water volumes in m³

The example shows:
1. GIIP calculation using standard material balance method
2. GIIP calculation using P/Z plot method
3. Visualization of P/Z vs Gp plot
4. Statistical analysis of results
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
from material_balance.gas_reservoir import GasReservoir, GasProductionData
from material_balance.pvt_properties import PVTProperties
from material_balance.units import UnitSystem

def main():
    """Example of gas reservoir material balance with 4 pressure points"""
    
    print("=" * 70)
    print("Gas Reservoir Material Balance Example - Metric Units")
    print("=" * 70)
    print("\nThis example uses metric units:")
    print("  - Pressure: kgf/cm²")
    print("  - Gas volume: m³ (standard conditions)")
    print("  - Water volume: m³")
    print("=" * 70)
    
    # ========================================================================
    # STEP 1: Define PVT Properties in METRIC UNITS
    # ========================================================================
    print("\n1. PVT Properties Definition")
    print("-" * 70)
    
    # PVT data for a gas reservoir
    pressure_data = [225, 205.7, 177.57, 149.44]  # kgf/cm²
    Bg_data = [0.0052622, 0.0057004, 0.0065311, 0.0077360]  # m³/m³ std
    z_data = [0.860, 0.870, 0.885, 0.905, 0.930]  # Gas compressibility factor
    mu_g_data = [0.0180, 0.0175, 0.0170, 0.0165, 0.0160]  # cP (optional)
    
    print("Pressure (kgf/cm²):", pressure_data)
    print("Bg (m³/m³ std):    ", Bg_data)
    print("Z-factor:          ", z_data)
    
    # Create PVT properties object
    pvt = PVTProperties(
        pressure=pressure_data,
        Bg=Bg_data,
        z=z_data,
        mu_g=mu_g_data,
        Bw=[1.0] * len(pressure_data),  # Water FVF (m³/m³)
        cw=[4.5e-5] * len(pressure_data),  # Water compressibility (1/kgf/cm²)
        cf=[6.0e-5] * len(pressure_data),  # Formation compressibility (1/kgf/cm²)
        unit_system=UnitSystem.METRIC
    )
    
    # ========================================================================
    # STEP 2: Define Initial Reservoir Conditions
    # ========================================================================
    print("\n2. Initial Reservoir Conditions")
    print("-" * 70)
    
    initial_pressure = 225.0  # kgf/cm²
    reservoir_temperature = 104.0  # °C
    aquifer_influx = False  # No water influx
    
    print(f"Initial pressure: {initial_pressure} kgf/cm²")
    print(f"Reservoir temperature: {reservoir_temperature} °C")
    print(f"Aquifer influx: {'Yes' if aquifer_influx else 'No'}")
    
    # Create gas reservoir object
    reservoir = GasReservoir(
        pvt_properties=pvt,
        initial_pressure=initial_pressure,
        reservoir_temperature=reservoir_temperature,
        aquifer_influx=aquifer_influx,
        unit_system=UnitSystem.METRIC
    )
    
    # ========================================================================
    # STEP 3: Define Production Data (3 pressure points)
    # ========================================================================
    print("\n3. Production Data (3 Pressure Points)")
    print("-" * 70)
    
    # Time points (days)
    times = np.array([0, 365, 730, 1095])
    
    # Cumulative gas production (m³ std)
    Gp = np.array([
        0,           # Initial (no production)
        2_237_000,  # 2.237 million m³ after 1 year
        6_258_000, # 6.258 million m³ after 2 years
        12_799_000, # 12.799 million m³ after 3 years
    ])
    
    # Cumulative water production (m³) - minimal for gas reservoir
    Wp = np.array([
        0,
        0,
        0,
        0,
    ])
    
    # Average reservoir pressures (kgf/cm²)
    pressures = np.array([225, 205.7, 177.57, 149.44])
    
    print(f"\n{'Time (days)':<15} {'Pressure (kgf/cm²)':<20} {'Gp (MM m³)':<15} {'Wp (m³)':<12}")
    print("-" * 70)
    for i in range(len(times)):
        print(f"{times[i]:<15.0f} {pressures[i]:<20.1f} {Gp[i]/1e6:<15.1f} {Wp[i]:<12.0f}")
    
    # Create production data object
    production_data = GasProductionData(
        time=times,
        Gp=Gp,
        Wp=Wp,
        pressure=pressures,
        unit_system=UnitSystem.METRIC
    )
    
    # ========================================================================
    # STEP 4: Calculate GIIP Using Standard Material Balance Method
    # ========================================================================
    print("\n4. GIIP Calculation - Standard Material Balance Method")
    print("-" * 70)
    
    G_values_std, stats_std = reservoir.calculate_GIIP_from_production_data(
        production_data=production_data,
        method='standard'
    )
    
    print("\nGIIP calculated at each pressure point:")
    print(f"\n{'Time (days)':<15} {'Pressure (kgf/cm²)':<20} {'GIIP (MM m³)':<20}")
    print("-" * 70)
    for i in range(1, len(times)):  # Skip initial point (no production)
        if not np.isnan(G_values_std[i]):
            print(f"{times[i]:<15.0f} {pressures[i]:<20.1f} {G_values_std[i]/1e6:<20.1f}")
    
    print("\nStatistical Summary:")
    print(f"  Mean GIIP:   {stats_std['mean']/1e6:,.1f} million m³")
    print(f"  Median GIIP: {stats_std['median']/1e6:,.1f} million m³")
    print(f"  Std Dev:     {stats_std['std']/1e6:,.1f} million m³")
    print(f"  Min GIIP:    {stats_std['min']/1e6:,.1f} million m³")
    print(f"  Max GIIP:    {stats_std['max']/1e6:,.1f} million m³")
    print(f"  CV:          {stats_std['coefficient_of_variation']:.4f}")
    
    # ========================================================================
    # STEP 5: Calculate GIIP Using P/Z Method
    # ========================================================================
    print("\n5. GIIP Calculation - P/Z Method")
    print("-" * 70)
    
    G_values_pz, stats_pz = reservoir.calculate_GIIP_from_production_data(
        production_data=production_data,
        method='pz'
    )
    
    print("\nGIIP calculated at each pressure point:")
    print(f"\n{'Time (days)':<15} {'Pressure (kgf/cm²)':<20} {'GIIP (MM m³)':<20}")
    print("-" * 70)
    for i in range(1, len(times)):  # Skip initial point
        if not np.isnan(G_values_pz[i]):
            print(f"{times[i]:<15.0f} {pressures[i]:<20.1f} {G_values_pz[i]/1e6:<20.1f}")
    
    print("\nStatistical Summary:")
    print(f"  Mean GIIP:   {stats_pz['mean']/1e6:,.1f} million m³")
    print(f"  Median GIIP: {stats_pz['median']/1e6:,.1f} million m³")
    print(f"  Std Dev:     {stats_pz['std']/1e6:,.1f} million m³")
    print(f"  Min GIIP:    {stats_pz['min']/1e6:,.1f} million m³")
    print(f"  Max GIIP:    {stats_pz['max']/1e6:,.1f} million m³")
    print(f"  CV:          {stats_pz['coefficient_of_variation']:.4f}")
    
    # ========================================================================
    # STEP 6: Create P/Z vs Gp Plot
    # ========================================================================
    print("\n6. Creating P/Z vs Gp Plot")
    print("-" * 70)
    
    fig, ax = reservoir.plot_pz_vs_gp(production_data)
    
    plt.savefig('gas_reservoir_pz_plot_metric.png', dpi=300, bbox_inches='tight')
    print("✓ Saved P/Z plot as 'gas_reservoir_pz_plot_metric.png'")
    
    # ========================================================================
    # STEP 7: Create Custom Visualization
    # ========================================================================
    print("\n7. Creating Additional Visualizations")
    print("-" * 70)
    
    # Create figure with multiple subplots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle('Gas Reservoir Material Balance Analysis - Metric Units', 
                 fontsize=14, fontweight='bold')
    
    # Plot 1: Pressure vs Time
    ax1 = axes[0, 0]
    ax1.plot(times/365, pressures, 'o-', linewidth=2, markersize=8, color='blue')
    ax1.set_xlabel('Time (years)', fontsize=11)
    ax1.set_ylabel('Pressure (kgf/cm²)', fontsize=11)
    ax1.set_title('Reservoir Pressure Decline', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Cumulative Production vs Time
    ax2 = axes[0, 1]
    ax2.plot(times/365, Gp/1e6, 'o-', linewidth=2, markersize=8, color='green')
    ax2.set_xlabel('Time (years)', fontsize=11)
    ax2.set_ylabel('Cumulative Gas Production (MM m³)', fontsize=11)
    ax2.set_title('Gas Production History', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: GIIP Comparison (Standard vs P/Z method)
    ax3 = axes[1, 0]
    valid_idx_std = ~np.isnan(G_values_std)
    valid_idx_pz = ~np.isnan(G_values_pz)
    ax3.plot(times[valid_idx_std]/365, G_values_std[valid_idx_std]/1e6, 
             'o-', linewidth=2, markersize=8, label='Standard Method', color='red')
    ax3.plot(times[valid_idx_pz]/365, G_values_pz[valid_idx_pz]/1e6, 
             's--', linewidth=2, markersize=8, label='P/Z Method', color='purple')
    ax3.axhline(y=stats_std['mean']/1e6, color='red', linestyle=':', alpha=0.5, 
                label=f"Mean (Std): {stats_std['mean']/1e6:.1f} MM m³")
    ax3.axhline(y=stats_pz['mean']/1e6, color='purple', linestyle=':', alpha=0.5,
                label=f"Mean (P/Z): {stats_pz['mean']/1e6:.1f} MM m³")
    ax3.set_xlabel('Time (years)', fontsize=11)
    ax3.set_ylabel('GIIP (MM m³)', fontsize=11)
    ax3.set_title('GIIP Calculation Results', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: P/Z vs Gp (simplified version)
    ax4 = axes[1, 1]
    pz_values = pressures / z_data
    ax4.plot(Gp/1e6, pz_values, 'o-', linewidth=2, markersize=8, color='orange')
    
    # Linear fit for extrapolation
    valid_points = ~np.isnan(pz_values) & (Gp > 0)
    if np.sum(valid_points) >= 2:
        coeffs = np.polyfit(Gp[valid_points], pz_values[valid_points], 1)
        x_fit = np.array([0, stats_pz['mean']])
        y_fit = coeffs[0] * x_fit + coeffs[1]
        ax4.plot(x_fit/1e6, y_fit, '--', color='gray', linewidth=1.5, 
                 label=f'Linear fit\nGIIP ≈ {stats_pz["mean"]/1e6:.0f} MM m³')
        ax4.axvline(x=stats_pz['mean']/1e6, color='red', linestyle=':', 
                   alpha=0.5, label='Estimated GIIP')
    
    ax4.set_xlabel('Cumulative Gas Production, Gp (MM m³)', fontsize=11)
    ax4.set_ylabel('P/Z (kgf/cm²)', fontsize=11)
    ax4.set_title('P/Z vs Gp Plot', fontsize=12, fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('gas_reservoir_analysis_metric.png', dpi=300, bbox_inches='tight')
    print("✓ Saved comprehensive analysis as 'gas_reservoir_analysis_metric.png'")
    
    # ========================================================================
    # STEP 8: Summary and Recommendations
    # ========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY AND RECOMMENDATIONS")
    print("=" * 70)
    
    print("\nEstimated Gas Initially In Place (GIIP):")
    print(f"  Standard Method: {stats_std['mean']/1e6:,.1f} ± {stats_std['std']/1e6:,.1f} million m³")
    print(f"  P/Z Method:      {stats_pz['mean']/1e6:,.1f} ± {stats_pz['std']/1e6:,.1f} million m³")
    
    # Calculate average of both methods
    avg_giip = (stats_std['mean'] + stats_pz['mean']) / 2
    print(f"\n  Recommended GIIP: {avg_giip/1e6:,.1f} million m³")
    print(f"  (Average of both methods)")
    
    # Calculate recovery factor
    current_production = Gp[-1]
    recovery_factor = (current_production / avg_giip) * 100
    print(f"\nCurrent Production Status:")
    print(f"  Total produced:   {current_production/1e6:,.1f} million m³")
    print(f"  Recovery factor:  {recovery_factor:.1f}%")
    print(f"  Remaining gas:    {(avg_giip - current_production)/1e6:,.1f} million m³")
    
    print("\nData Quality Assessment:")
    cv_std = stats_std['coefficient_of_variation']
    cv_pz = stats_pz['coefficient_of_variation']
    
    if cv_std < 0.05 and cv_pz < 0.05:
        quality = "EXCELLENT"
    elif cv_std < 0.10 and cv_pz < 0.10:
        quality = "GOOD"
    elif cv_std < 0.15 and cv_pz < 0.15:
        quality = "FAIR"
    else:
        quality = "POOR"
    
    print(f"  Coefficient of Variation (Standard): {cv_std:.4f}")
    print(f"  Coefficient of Variation (P/Z):      {cv_pz:.4f}")
    print(f"  Overall data quality: {quality}")
    
    if quality in ["EXCELLENT", "GOOD"]:
        print("\n  ✓ The GIIP estimates are reliable and consistent")
    else:
        print("\n  ⚠ Consider collecting more data points or reviewing PVT properties")
    
    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)
    
    # Display plots
    plt.show()


if __name__ == "__main__":
    main()
