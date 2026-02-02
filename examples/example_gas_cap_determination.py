"""
Example: Gas Cap Size Determination

This example demonstrates how to use the gas cap determination methods
to identify the optimal gas cap size (m) for an oil reservoir with an
unknown gas cap.

The method plots F vs (Eo + m*Eg) for different values of m and identifies
the m value that produces the straightest line (best R² value).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
from material_balance.oil_reservoir import OilReservoir, ProductionData
from material_balance.pvt_properties import PVTProperties
from material_balance.units import UnitSystem

def main():
    """Example of gas cap size determination"""
    
    print("=" * 70)
    print("Gas Cap Size Determination Example")
    print("=" * 70)
    
    # Define PVT properties in FIELD UNITS
    pressure_data = [3330, 3150, 3000, 2850, 2700, 2550, 2400]  # psia
    Bo_data = [1.2511, 1.2353, 1.2222, 1.2122, 1.2022, 1.1922, 1.1822]        # rb/STB
    Rs_data = [510, 477, 450, 425, 401, 375, 352]               # SCF/STB
    Bg_data = [0.00087, 0.00092, 0.00096, 0.00101, 0.00107, 0.00113, 0.00120]  # rb/SCF
    
    # Create PVT object with FIELD unit system
    pvt = PVTProperties(
        pressure=pressure_data,
        Bo=Bo_data,
        Rs=Rs_data,
        Bg=Bg_data,
        Bw=[1.02] * len(pressure_data),          # rb/STB
        cw=[3e-6] * len(pressure_data),          # 1/psi
        cf=[4e-6] * len(pressure_data),          # 1/psi
        unit_system=UnitSystem.FIELD  # Specify FIELD units
    )
    
    # Initial reservoir conditions
    initial_pressure = 250.0  # kgf/cm2
    temperature = 90.0  # °C
    
    # Create production data
    # This represents cumulative production at different times
    times = np.array([0, 365, 730, 1095, 1460, 1825, 2190, 2555, 2920, 3285])  # days
    Np = np.array([0, 150000, 320000, 510000, 720000, 950000, 1200000, 1470000, 1760000, 2070000])  # m3
    Gp = np.array([0, 13000000, 28000000, 45000000, 64000000, 85000000, 108000000, 133000000, 160000000, 189000000])  # m3
    Wp = np.array([0, 5000, 12000, 21000, 32000, 45000, 60000, 77000, 96000, 117000])  # m3
    pressures_prod = np.array([250, 240, 230, 220, 210, 200, 190, 180, 170, 160])  # kgf/cm2
    
    production_data = ProductionData(
        time=times,
        Np=Np,
        Gp=Gp,
        Wp=Wp,
        pressure=pressures_prod,
        unit_system=UnitSystem.METRIC
    )
    
    # Initialize reservoir with m = 0 (we will test different values)
    # Note: The actual m value doesn't matter here since we'll test multiple values
    reservoir = OilReservoir(
        pvt_properties=pvt,
        initial_pressure=initial_pressure,
        reservoir_temperature=temperature,
        m=0.0,  # Initial guess
        unit_system=UnitSystem.METRIC
    )
    
    print("\n1. Testing different m values (0.1 to 0.9)...")
    print("-" * 70)
    
    # Method 1: Create visual plots for m values from 0.1 to 0.9
    m_test_values = np.arange(0.1, 1.0, 0.1)
    fig1, axes1, r_squared_dict = reservoir.plot_gas_cap_determination(
        production_data=production_data,
        m_values=m_test_values
    )
    
    print("\nR² values for different m:")
    for m, r2 in r_squared_dict.items():
        print(f"  m = {m:.1f}: R² = {r2:.6f}")
    
    plt.savefig('gas_cap_determination_plots.png', dpi=300, bbox_inches='tight')
    print("\n✓ Saved gas_cap_determination_plots.png")
    
    # Method 2: Automatically determine optimal m with finer resolution
    print("\n2. Finding optimal m value with fine resolution...")
    print("-" * 70)
    
    optimal_m, results = reservoir.determine_optimal_m(
        production_data=production_data,
        m_values=np.arange(0.1, 1.0, 0.01),  # Test with finer resolution
        show_plot=True
    )
    
    plt.savefig('optimal_m_determination.png', dpi=300, bbox_inches='tight')
    print("✓ Saved optimal_m_determination.png")
    
    # Now recalculate STOIIP with the optimal m
    print("\n3. Calculating STOIIP with optimal m...")
    print("-" * 70)
    
    reservoir_optimal = OilReservoir(
        pvt_properties=pvt,
        initial_pressure=initial_pressure,
        reservoir_temperature=temperature,
        m=optimal_m,
        unit_system=UnitSystem.METRIC
    )
    
    N_values, statistics = reservoir_optimal.calculate_STOIIP_from_production_data(
        production_data=production_data
    )
    
    print(f"\nSTOIIP Statistics with m = {optimal_m:.3f}:")
    print(f"  Mean:     {statistics['mean']:,.0f} m³ std")
    print(f"  Median:   {statistics['median']:,.0f} m³ std")
    print(f"  Std Dev:  {statistics['std']:,.0f} m³ std")
    print(f"  Min:      {statistics['min']:,.0f} m³ std")
    print(f"  Max:      {statistics['max']:,.0f} m³ std")
    print(f"  CoV:      {statistics['coefficient_of_variation']:.4f}")
    
    # Create final material balance plot with optimal m
    print("\n4. Creating material balance plot with optimal m...")
    print("-" * 70)
    
    fig2, ax2 = reservoir_optimal.plot_material_balance(
        production_data=production_data
    )
    
    plt.savefig('material_balance_plot_optimal_m.png', dpi=300, bbox_inches='tight')
    print("✓ Saved material_balance_plot_optimal_m.png")
    
    print("\n" + "=" * 70)
    print("Analysis Complete!")
    print("=" * 70)
    print(f"\nKey Results:")
    print(f"  - Optimal gas cap size: m = {optimal_m:.3f}")
    print(f"  - R² for optimal m: {results['optimal_r_squared']:.6f}")
    print(f"  - STOIIP with optimal m: {statistics['mean']:,.0f} m³ std")
    print(f"\nInterpretation:")
    print(f"  The gas cap volume is {optimal_m:.3f} times the initial oil volume.")
    print(f"  Gas cap volume = {optimal_m:.3f} × STOIIP × Boi")
    
    plt.show()

if __name__ == "__main__":
    main()
