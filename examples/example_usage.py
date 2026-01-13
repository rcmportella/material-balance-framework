"""
Example Usage Scripts for Material Balance Framework

This module demonstrates how to use the material balance framework
for both oil and gas reservoirs.
"""

import numpy as np
import sys
import os

# Add parent directory to path to import material_balance package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from material_balance import OilReservoir, GasReservoir, PVTProperties
from material_balance.oil_reservoir import ProductionData
from material_balance.gas_reservoir import GasProductionData
from material_balance.utils import print_results_summary, format_number


def example_oil_reservoir():
    """
    Example: Calculate STOIIP for an oil reservoir using material balance.
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: OIL RESERVOIR MATERIAL BALANCE")
    print("="*70 + "\n")
    
    # Define PVT properties at different pressures (metric units)
    pressure_data = [210, 196, 182, 168, 154, 140, 126]  # kgf/cm2
    Bo_data = [1.25, 1.24, 1.23, 1.22, 1.21, 1.20, 1.19]  # m3/m3 std
    Rs_data = [2.81, 2.69, 2.58, 2.47, 2.36, 2.25, 2.13]  # m3/m3 std (converted from SCF/STB)
    Bg_data = [0.00283, 0.00301, 0.00318, 0.00336, 0.00354, 0.00371, 0.00389]  # m3/m3 std
    
    pvt = PVTProperties(
        pressure=pressure_data,
        Bo=Bo_data,
        Rs=Rs_data,
        Bg=Bg_data,
        Bw=[1.02] * len(pressure_data),
        cw=[43e-6] * len(pressure_data),  # 1/(kgf/cm2)
        cf=[57e-6] * len(pressure_data)   # 1/(kgf/cm2)
    )
    
    # Initialize reservoir
    oil_res = OilReservoir(
        pvt_properties=pvt,
        initial_pressure=210,  # kgf/cm2
        reservoir_temperature=82,  # °C (converted from 180°F)
        m=0.2  # Small gas cap
    )
    
    # Production data (metric units)
    prod_data = ProductionData(
        time=[0, 365, 730, 1095, 1460, 1825, 2190],  # days
        Np=[0, 79500, 190800, 318000, 461100, 604200, 747300],  # m3 std
        Gp=[0, 7079e3, 16990e3, 28317e3, 41034e3, 53793e3, 66552e3],  # m3 std
        Wp=[0, 1590, 3975, 6678, 9700, 13038, 16695],  # m3 std
        pressure=[210, 196, 182, 168, 154, 140, 126]  # kgf/cm2
    )
    
    # Calculate STOIIP from all data points
    print("Calculating STOIIP from production history...")
    N_values, statistics = oil_res.calculate_STOIIP_from_production_data(prod_data)
    
    # Print results
    print_results_summary(statistics, "oil")
    
    # Calculate recovery factor
    current_Np = prod_data.Np[-1]
    rf = current_Np / statistics['mean']
    print(f"Current Recovery Factor: {rf:.2%}")
    print(f"Cumulative Oil Production: {format_number(current_Np, 'm3 std')}")
    print(f"Remaining Oil: {format_number(statistics['mean'] - current_Np, 'm3 std')}")
    
    # Plot material balance
    try:
        fig, ax = oil_res.plot_material_balance(prod_data)
        print("\nMaterial balance plot created successfully!")
        # Uncomment to display plot:
        # import matplotlib.pyplot as plt
        # plt.show()
    except ImportError:
        print("\nNote: Install matplotlib to generate plots (pip install matplotlib)")
    
    return oil_res, statistics


def example_gas_reservoir():
    """
    Example: Calculate GIIP for a gas reservoir using material balance.
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: GAS RESERVOIR MATERIAL BALANCE")
    print("="*70 + "\n")
    
    # Define PVT properties for gas (metric units)
    pressure_data = [281, 267, 253, 239, 225, 211, 196, 182]  # kgf/cm2
    z_data = [0.85, 0.84, 0.83, 0.82, 0.81, 0.80, 0.79, 0.78]  # dimensionless
    T = 366.5  # Temperature in Kelvin (200°F = 93.3°C = 366.5 K)
    
    # Calculate Bg from P, T, and z (metric units)
    Bg_data = [0.00351 * z * T / P for z, P in zip(z_data, pressure_data)]
    
    pvt = PVTProperties(
        pressure=pressure_data,
        Bg=Bg_data,
        z=z_data,
        Bw=[1.02] * len(pressure_data)
    )
    
    # Initialize gas reservoir
    gas_res = GasReservoir(
        pvt_properties=pvt,
        initial_pressure=281,  # kgf/cm2
        reservoir_temperature=T,  # K
        aquifer_influx=False
    )
    
    # Gas production data (metric units)
    gas_prod_data = GasProductionData(
        time=[0, 365, 730, 1095, 1460, 1825, 2190, 2555],  # days
        Gp=[0, 141.6e6, 339.6e6, 566.0e6, 820.7e6, 1103.6e6, 1415.0e6, 1754.6e6],  # m3 std
        Wp=[0, 0, 0, 0, 0, 0, 0, 0],  # No water production
        pressure=[281, 267, 253, 239, 225, 211, 196, 182]  # kgf/cm2
    )
    
    # Calculate GIIP using standard method
    print("Calculating GIIP using standard material balance...")
    G_values_std, statistics_std = gas_res.calculate_GIIP_from_production_data(
        gas_prod_data, 
        method='standard'
    )
    
    print_results_summary(statistics_std, "gas")
    
    # Calculate GIIP using P/Z method
    print("\nCalculating GIIP using P/Z method...")
    G_values_pz, statistics_pz = gas_res.calculate_GIIP_from_production_data(
        gas_prod_data, 
        method='pz'
    )
    
    print("\nP/Z Method Results:")
    print(f"  Mean GIIP: {format_number(statistics_pz['mean'], 'm3 std')}")
    print(f"  Std Dev:   {format_number(statistics_pz['std'], 'm3 std')}")
    
    # Calculate recovery factor
    current_Gp = gas_prod_data.Gp[-1]
    rf = current_Gp / statistics_std['mean']
    print(f"\nCurrent Recovery Factor: {rf:.2%}")
    print(f"Cumulative Gas Production: {format_number(current_Gp, 'm3 std')}")
    print(f"Remaining Gas: {format_number(statistics_std['mean'] - current_Gp, 'm3 std')}")
    
    # Generate plots
    try:
        # P/Z vs Gp plot
        fig1, ax1 = gas_res.plot_pz_vs_gp(gas_prod_data)
        print("\nP/Z vs Gp plot created successfully!")
        
        # Pressure history plot
        fig2, axes2 = gas_res.plot_pressure_history(gas_prod_data)
        print("Pressure history plots created successfully!")
        
        # Uncomment to display plots:
        # import matplotlib.pyplot as plt
        # plt.show()
    except ImportError:
        print("\nNote: Install matplotlib to generate plots (pip install matplotlib)")
    
    return gas_res, statistics_std


def example_with_correlations():
    """
    Example: Using PVT correlations when measured data is not available.
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: USING PVT CORRELATIONS")
    print("="*70 + "\n")
    
    from material_balance.pvt_properties import CorrelationsPVT
    
    # Fluid properties
    gamma_g = 0.65  # Gas specific gravity
    gamma_o = 0.85  # Oil specific gravity (water = 1)
    API = 35        # API gravity
    T = 82          # Temperature (°C)
    
    # Generate PVT data using correlations (metric units)
    pressures = np.linspace(70, 210, 11)  # kgf/cm2
    Bo_values = []
    Rs_values = []
    
    for P in pressures:
        Rs = CorrelationsPVT.standing_Rs(P, gamma_g, gamma_o, T)
        Bo = CorrelationsPVT.standing_Bo(Rs, gamma_g, gamma_o, T)
        Rs_values.append(Rs)
        Bo_values.append(Bo)
    
    print("Generated PVT data using Standing correlations:")
    print("\nPressure (kgf/cm2) | Rs (m3/m3) | Bo (m3/m3)")
    print("-" * 55)
    for P, Rs, Bo in zip(pressures, Rs_values, Bo_values):
        print(f"  {P:6.1f}           |  {Rs:7.4f}   | {Bo:6.4f}")
    
    # Calculate z-factor for gas
    T_kelvin = T + 273.15  # Convert to Kelvin
    z_values = [CorrelationsPVT.gas_z_factor_hall_yarborough(P, T_kelvin, gamma_g) 
                for P in pressures]
    Bg_values = [CorrelationsPVT.gas_Bg(P, T_kelvin, z) 
                 for P, z in zip(pressures, z_values)]
    
    print(f"\nGas properties at {T}°C:")
    print("\nPressure (kgf/cm2) | Z-factor | Bg (m3/m3)")
    print("-" * 55)
    for P, z, Bg in zip(pressures, z_values, Bg_values):
        print(f"  {P:6.1f}           | {z:7.4f}  | {Bg:10.6f}")
    
    return pressures, Bo_values, Rs_values, z_values, Bg_values


def run_all_examples():
    """Run all examples."""
    print("\n" + "#"*70)
    print("# MATERIAL BALANCE FRAMEWORK - EXAMPLES")
    print("#"*70)
    
    # Example 1: Oil Reservoir
    oil_res, oil_stats = example_oil_reservoir()
    
    # Example 2: Gas Reservoir
    gas_res, gas_stats = example_gas_reservoir()
    
    # Example 3: PVT Correlations
    example_with_correlations()
    
    print("\n" + "#"*70)
    print("# ALL EXAMPLES COMPLETED SUCCESSFULLY")
    print("#"*70 + "\n")


if __name__ == "__main__":
    run_all_examples()
