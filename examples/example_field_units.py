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
from material_balance.utils import print_results_summary, format_number


def example_oil_reservoir_field_units():
    """
    Example: Oil reservoir with field units (US petroleum standard units)
    """
    print("\n" + "="*70)
    print("EXAMPLE: OIL RESERVOIR WITH FIELD UNITS")
    print("="*70 + "\n")
    
    print("Input units: psia, STB, SCF, °F, rb/STB, SCF/STB, 1/psi\n")
    
    # Define PVT properties in FIELD UNITS
    pressure_data = [3000, 2800, 2600, 2400, 2200, 2000, 1800]  # psia
    Bo_data = [1.25, 1.24, 1.23, 1.22, 1.21, 1.20, 1.19]        # rb/STB
    Rs_data = [500, 480, 460, 440, 420, 400, 380]               # SCF/STB
    Bg_data = [0.0008, 0.00085, 0.0009, 0.00095, 0.001, 0.00105, 0.0011]  # rb/SCF
    
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
        initial_pressure=3000,      # psia
        reservoir_temperature=180,  # °F
        m=0.2,                      # Small gas cap
        unit_system=UnitSystem.FIELD  # Specify FIELD units
    )
    
    print("Reservoir initialized with:")
    print(f"  - Initial pressure: 3000 psia")
    print(f"  - Temperature: 180 °F")
    print(f"  - Gas cap ratio (m): 0.2\n")
    
    # Production data in FIELD UNITS
    prod_data = ProductionData(
        time=[0, 365, 730, 1095, 1460, 1825, 2190],  # days
        Np=[0, 500e3, 1200e3, 2000e3, 2900e3, 3800e3, 4700e3],  # STB
        Gp=[0, 250e6, 600e6, 1000e6, 1450e6, 1900e6, 2350e6],   # SCF
        Wp=[0, 10e3, 25e3, 42e3, 61e3, 82e3, 105e3],            # STB
        pressure=[3000, 2800, 2600, 2400, 2200, 2000, 1800],    # psia
        unit_system=UnitSystem.FIELD  # Specify FIELD units
    )
    
    print("Production data provided in field units and converted automatically.\n")
    
    # Calculate STOIIP
    print("Calculating STOIIP from production history...")
    N_values, statistics = oil_res.calculate_STOIIP_from_production_data(prod_data)
    
    # Results are in metric units (m³ std)
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


def example_gas_reservoir_field_units():
    """
    Example: Gas reservoir with field units
    """
    print("\n" + "="*70)
    print("EXAMPLE: GAS RESERVOIR WITH FIELD UNITS")
    print("="*70 + "\n")
    
    print("Input units: psia, SCF, °F\n")
    
    # Define PVT properties for gas in FIELD UNITS
    pressure_data = [4000, 3800, 3600, 3400, 3200, 3000, 2800, 2600]  # psia
    z_data = [0.85, 0.84, 0.83, 0.82, 0.81, 0.80, 0.79, 0.78]          # dimensionless
    
    # Calculate Bg using gas law (simplified)
    T = 200  # °F
    T_R = T + 459.67  # Convert to Rankine
    Bg_data = []
    for i, P in enumerate(pressure_data):
        # Bg = 0.00504 * z * T_R / P (rb/SCF)
        Bg = 0.00504 * z_data[i] * T_R / P
        Bg_data.append(Bg)
    
    # Create PVT object with FIELD units
    pvt = PVTProperties(
        pressure=pressure_data,
        Bg=Bg_data,                                  # rb/SCF
        z=z_data,
        Bw=[1.02] * len(pressure_data),              # rb/STB
        cw=[3e-6] * len(pressure_data),              # 1/psi
        cf=[4e-6] * len(pressure_data),              # 1/psi
        unit_system=UnitSystem.FIELD  # Specify FIELD units
    )
    
    print("PVT properties created in field units.\n")
    
    # Initialize gas reservoir with FIELD units
    gas_res = GasReservoir(
        pvt_properties=pvt,
        initial_pressure=4000,      # psia
        reservoir_temperature=200,  # °F
        aquifer_influx=False,
        unit_system=UnitSystem.FIELD  # Specify FIELD units
    )
    
    print("Gas reservoir initialized with:")
    print(f"  - Initial pressure: 4000 psia")
    print(f"  - Temperature: 200 °F\n")
    
    # Production data in FIELD UNITS
    gas_prod_data = GasProductionData(
        time=[0, 365, 730, 1095, 1460, 1825, 2190, 2555],  # days
        Gp=[0, 5e9, 12e9, 20e9, 29e9, 39e9, 50e9, 62e9],   # SCF
        Wp=[0, 0, 0, 0, 0, 0, 0, 0],                       # STB (no water)
        pressure=[4000, 3800, 3600, 3400, 3200, 3000, 2800, 2600],  # psia
        unit_system=UnitSystem.FIELD  # Specify FIELD units
    )
    
    print("Gas production data provided in field units.\n")
    
    # Calculate GIIP using standard method
    print("Calculating GIIP using standard material balance method...")
    G_values, statistics = gas_res.calculate_GIIP_from_production_data(
        gas_prod_data, method='standard'
    )
    
    # Results are in metric units (m³ std)
    print("\n" + "="*70)
    print("RESULTS (Internal metric units)")
    print("="*70)
    print_results_summary(statistics, "gas")
    
    # Convert results back to field units
    mean_scf = statistics['mean'] * 35.3147  # m³ to SCF
    print("\n" + "="*70)
    print("RESULTS (Converted to field units)")
    print("="*70)
    print(f"Mean GIIP: {mean_scf:,.0f} SCF")
    print(f"           ({mean_scf/1e9:.2f} BCF)")
    print(f"           ({mean_scf/1e12:.4f} TCF)")
    
    # Recovery factor
    current_Gp_scf = gas_prod_data.Gp[-1] * 35.3147
    rf = current_Gp_scf / mean_scf
    print(f"\nCurrent Recovery Factor: {rf:.2%}")
    print(f"Cumulative Gas Production: {current_Gp_scf/1e9:.2f} BCF")
    print(f"Remaining Gas: {(mean_scf - current_Gp_scf)/1e9:.2f} BCF")
    
    # Try P/Z method
    print("\n" + "-"*70)
    print("Calculating GIIP using P/Z method...")
    G_values_pz, statistics_pz = gas_res.calculate_GIIP_from_production_data(
        gas_prod_data, method='pz'
    )
    
    mean_scf_pz = statistics_pz['mean'] * 35.3147
    print(f"Mean GIIP (P/Z method): {mean_scf_pz/1e9:.2f} BCF")
    
    return gas_res, statistics


def comparison_example():
    """
    Show that metric and field units give the same results
    """
    print("\n" + "="*70)
    print("UNIT CONVERSION VERIFICATION")
    print("="*70 + "\n")
    
    print("Testing that field units and metric units give equivalent results...\n")
    
    # Same reservoir, defined in both unit systems
    
    # Field units
    pvt_field = PVTProperties(
        pressure=[3000, 2500, 2000],
        Bo=[1.25, 1.23, 1.21],
        Rs=[500, 450, 400],
        Bg=[0.0008, 0.0009, 0.001],
        Bw=[1.02, 1.02, 1.02],
        cw=[3e-6, 3e-6, 3e-6],
        cf=[4e-6, 4e-6, 4e-6],
        unit_system=UnitSystem.FIELD
    )
    
    # Metric units (converted values)
    pvt_metric = PVTProperties(
        pressure=[210.92, 175.77, 140.61],  # psia to kgf/cm²
        Bo=[1.25, 1.23, 1.21],              # Same (ratio)
        Rs=[2.808, 2.527, 2.246],           # SCF/STB to m³/m³
        Bg=[0.2835, 0.3189, 0.3543],        # rb/SCF to m³/m³
        Bw=[1.02, 1.02, 1.02],              # Same (ratio)
        cw=[42.67e-6, 42.67e-6, 42.67e-6],  # 1/psi to 1/(kgf/cm²)
        cf=[56.89e-6, 56.89e-6, 56.89e-6],  # 1/psi to 1/(kgf/cm²)
        unit_system=UnitSystem.METRIC
    )
    
    # Calculate with field units
    oil_res_field = OilReservoir(
        pvt_properties=pvt_field,
        initial_pressure=3000,
        reservoir_temperature=180,
        m=0.0,
        unit_system=UnitSystem.FIELD
    )
    
    N_field = oil_res_field.calculate_STOIIP(
        Np=1000000, Gp=500e6, Wp=20000, pressure=2500
    )
    
    # Calculate with metric units
    oil_res_metric = OilReservoir(
        pvt_properties=pvt_metric,
        initial_pressure=210.92,
        reservoir_temperature=82.22,  # 180°F to °C
        m=0.0,
        unit_system=UnitSystem.METRIC
    )
    
    N_metric = oil_res_metric.calculate_STOIIP(
        Np=158987,      # 1 MMSTB to m³
        Gp=14158400,    # 500 MMSCF to m³
        Wp=3179.74,     # 20000 STB to m³
        pressure=175.77  # 2500 psia to kgf/cm²
    )
    
    print(f"STOIIP calculated with field units input: {N_field:,.0f} m³ std")
    print(f"STOIIP calculated with metric units input: {N_metric:,.0f} m³ std")
    print(f"Difference: {abs(N_field - N_metric):,.2f} m³ std ({abs(N_field - N_metric)/N_metric * 100:.4f}%)")
    
    if abs(N_field - N_metric) / N_metric < 0.01:
        print("\n✓ Unit conversion is working correctly! Results match within 1%.")
    else:
        print("\n✗ Warning: Results differ by more than 1%")


if __name__ == "__main__":
    # Run examples
    example_oil_reservoir_field_units()
    example_gas_reservoir_field_units()
    comparison_example()
    
    print("\n" + "="*70)
    print("Examples completed successfully!")
    print("="*70)
