"""
Quick Gas Cap Determination Example

This is a simplified example showing how to quickly determine gas cap size.
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
    print("Quick Gas Cap Size Determination")
    print("=" * 60)
    
    # Simple PVT data
    pvt = PVTProperties(
        pressure=np.array([250, 240, 230, 220, 210, 200, 190, 180, 170]),
        Bo=np.array([1.25, 1.26, 1.27, 1.28, 1.29, 1.30, 1.31, 1.32, 1.33]),
        Rs=np.array([85, 82, 79, 76, 73, 70, 67, 64, 61]),
        Bg=np.array([0.001, 0.0011, 0.0012, 0.0013, 0.0014, 0.0015, 0.0016, 0.0017, 0.0018]),
        unit_system=UnitSystem.METRIC
    )
    
    # Production data
    production_data = ProductionData(
        time=np.array([0, 365, 730, 1095, 1460, 1825, 2190, 2555, 2920]),
        Np=np.array([0, 150000, 320000, 510000, 720000, 950000, 1200000, 1470000, 1760000]),
        Gp=np.array([0, 13e6, 28e6, 45e6, 64e6, 85e6, 108e6, 133e6, 160e6]),
        Wp=np.array([0, 5000, 12000, 21000, 32000, 45000, 60000, 77000, 96000]),
        pressure=np.array([250, 240, 230, 220, 210, 200, 190, 180, 170]),
        unit_system=UnitSystem.METRIC
    )
    
    # Initialize reservoir
    reservoir = OilReservoir(
        pvt_properties=pvt,
        initial_pressure=250.0,
        reservoir_temperature=90.0,
        m=0.0,
        unit_system=UnitSystem.METRIC
    )
    
    # Determine optimal m
    print("\nDetermining optimal gas cap size...")
    optimal_m, results = reservoir.determine_optimal_m(
        production_data=production_data,
        m_values=np.arange(0.1, 1.0, 0.05),
        show_plot=False
    )
    
    print(f"\n✓ Optimal m = {optimal_m:.3f}")
    print(f"✓ R² = {results['optimal_r_squared']:.6f}")
    
    # Recalculate STOIIP with optimal m
    reservoir_optimal = OilReservoir(
        pvt_properties=pvt,
        initial_pressure=250.0,
        reservoir_temperature=90.0,
        m=optimal_m,
        unit_system=UnitSystem.METRIC
    )
    
    N_values, stats = reservoir_optimal.calculate_STOIIP_from_production_data(
        production_data=production_data
    )
    
    print(f"\nSTOIIP Results:")
    print(f"  Mean:   {stats['mean']:,.0f} m³ std")
    print(f"  Median: {stats['median']:,.0f} m³ std")
    print(f"  Std:    {stats['std']:,.0f} m³ std")
    
    print("\n" + "=" * 60)
    print("Complete! Gas cap size successfully determined.")
    print("=" * 60)

if __name__ == "__main__":
    main()
