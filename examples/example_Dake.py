"""
Example: Using Field Units (English Units)

This example demonstrates how to use the material balance framework
with field units (psia, STB, SCF, °F, rb) instead of metric units.

The framework automatically converts field units to internal metric units,
performs calculations, and returns results in metric units.
"""

import numpy as np
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from material_balance import OilReservoir, GasReservoir, PVTProperties, UnitSystem
from material_balance.oil_reservoir import ProductionData
from material_balance.gas_reservoir import GasProductionData
from material_balance.utils import print_results_summary, format_number, save_results_to_csv, save_production_analysis_to_csv


def example_oil_reservoir_field_units():
    """
    Example: Oil reservoir with field units (US petroleum standard units)
    """
    print("\n" + "="*70)
    print("EXAMPLE: GAS CAP OIL RESERVOIR WITH FIELD UNITS FROM DAKE")
    print("="*70 + "\n")
    
    print("Input units: psia, STB, SCF, °F, rb/STB, SCF/STB, 1/psi\n")
    
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
    
    print("PVT properties converted to internal metric units automatically.\n")
    
    # Initialize reservoir with FIELD units
    oil_res = OilReservoir(
        pvt_properties=pvt,
        initial_pressure=3330,      # psia
        reservoir_temperature=180,  # °F
        m=0.5,                      # Small gas cap
        unit_system=UnitSystem.FIELD  # Specify FIELD units
    )
    
    print("Reservoir initialized with:")
    print(f"  - Initial pressure: 3330 psia")
    print(f"  - Temperature: 180 °F")
    print(f"  - Gas cap ratio (m): 0.4\n")
    
    # Production data in FIELD UNITS
    prod_data = ProductionData(
        time=[0, 365, 730, 1095, 1460, 1825, 2190],  # days
        Np=[0, 3.295e6, 5.903e6, 8.852e6, 11.503e6, 14.513e6, 17.730e6],  # STB
        Gp=[0, 3.45975e9, 6.257180e9, 1.026832E+10, 1.420621e10, 1.835895e10, 2.304900e10],   # SCF
        Wp=[0,0,0,0,0,0,0],            # STB
        pressure=[3330, 3150, 3000, 2850, 2700, 2550, 2400],    # psia
        unit_system=UnitSystem.FIELD  # Specify FIELD units
    )
    
    print("Production data provided in field units and converted automatically.\n")
    
    # Calculate STOIIP
    print("Calculating STOIIP from production history...")
    N_values, statistics = oil_res.calculate_STOIIP_from_production_data(prod_data)
    
    # Access expansion terms for ALL points
    print("\nExpansion Terms for All Pressure Points:")
    for i in range(len(oil_res.pressure_values)):
        print(f"\nPoint {i+1}:")
        print(f"  Pressure: {oil_res.pressure_values[i]:.2f} kgf/cm²")
        print(f"  Eo: {oil_res.Eo_values[i]:.6f}")
        print(f"  Eg: {oil_res.Eg_values[i]:.6f}")
        print(f"  Efw: {oil_res.Efw_values[i]:.6f}")
        print(f"  Et: {oil_res.Et_values[i]:.6f}")
        print(f"  F: {oil_res.F_values[i]:.2f}")

    # Save everything to CSV (includes all expansion terms)
    """""
    save_production_analysis_to_csv(
        production_data=prod_data,
        N_values=N_values,
        filename='production_analysis.csv',
        reservoir_obj=oil_res,  # Pass reservoir to include expansion terms
        print_to_console=True
    )    # Optional: Save detailed production analysis
    """
    save_results_to_csv(statistics, filename='stoiip_results_field_units.csv', print_to_console=True)  # Save summary results
    save_results_to_csv(statistics, 'results.csv', oil_res) # Optional: Save detailed results with reservoir info
    save_production_analysis_to_csv(production_data=prod_data, N_values=N_values, filename='production_analysis.csv', print_to_console=True)    # Results are in metric units (m³ std)

    print("\n" + "="*70)
    print("RESULTS (Internal metric units)")
    print("="*70)
    print_results_summary(statistics, "oil")
    
    # Convert results back to field units for display
    mean_stb = statistics['mean'] * 6.28981  # m³ to STB
    print("\n" + "="*70)
    print("RESULTS (Converted to field units)")
    print("="*70)
    print(f"Mean STOIIP: {mean_stb:,.0f} STB")
    print(f"             ({mean_stb/1e6:.2f} MMSTB)")
    
    # Recovery factor
    current_Np_stb = prod_data.Np[-1] * 6.28981  # Convert back for display
    rf = current_Np_stb / mean_stb
    print(f"\nCurrent Recovery Factor: {rf:.2%}")
    print(f"Cumulative Oil Production: {current_Np_stb:,.0f} STB")
    print(f"Remaining Oil: {mean_stb - current_Np_stb:,.0f} STB")
    
    return oil_res, statistics



if __name__ == "__main__":
    # Run examples
    example_oil_reservoir_field_units()
    
    print("\n" + "="*70)
    print("Dake example completed successfully!")
    print("="*70)
