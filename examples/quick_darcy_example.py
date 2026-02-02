"""
Quick Darcy Flow Example

Simple examples showing basic usage of the Darcy flow module.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from material_balance import DarcyRadialFlow, DarcyFlowParameters, UnitSystem


def example_calculate_rate():
    """Calculate flow rate from known pressures"""
    print("\n" + "="*60)
    print("Calculate Flow Rate from Pressures")
    print("="*60)
    
    params = DarcyFlowParameters(
        k=100,          # Permeability: 100 mD
        h=10,           # Thickness: 10 m
        Pe=200,         # Reservoir pressure: 200 kgf/cm²
        Pwf=150,        # Wellbore pressure: 150 kgf/cm²
        mu=2.0,         # Viscosity: 2 cp
        Bo=1.25,        # FVF: 1.25
        re=300,         # Drainage radius: 300 m
        rw=0.1,         # Well radius: 0.1 m
        S=0,            # No skin
        unit_system=UnitSystem.METRIC
    )
    
    calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)
    results = calculator.calculate(params)
    calculator.print_results(results)


def example_calculate_pressure():
    """Calculate bottomhole pressure from desired rate"""
    print("\n" + "="*60)
    print("Calculate Bottomhole Pressure from Flow Rate")
    print("="*60)
    
    params = DarcyFlowParameters(
        k=50,           # Permeability: 50 mD
        h=30,           # Thickness: 30 ft
        Pe=3000,        # Reservoir pressure: 3000 psia
        q=500,          # Desired rate: 500 STB/day
        mu=1.5,         # Viscosity: 1.5 cp
        Bo=1.2,         # FVF: 1.2
        re=745,         # Drainage radius: 745 ft (40 acres)
        rw=0.3,         # Well radius: 0.3 ft
        S=0,            # No skin
        unit_system=UnitSystem.FIELD
    )
    
    calculator = DarcyRadialFlow(unit_system=UnitSystem.FIELD)
    results = calculator.calculate(params)
    calculator.print_results(results)


if __name__ == "__main__":
    example_calculate_rate()
    example_calculate_pressure()
