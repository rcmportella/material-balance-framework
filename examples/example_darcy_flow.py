"""
Example: Darcy Radial Flow Calculations

This example demonstrates how to use the Darcy flow module to calculate
oil flow rates and pressure drawdowns in radial flow systems.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import matplotlib.pyplot as plt
from material_balance import DarcyRadialFlow, DarcyFlowParameters, UnitSystem, calculate_drainage_radius


def example_1_calculate_flow_rate_metric():
    """
    Example 1: Calculate flow rate given pressures (METRIC units)
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Calculate Flow Rate (Metric Units)")
    print("="*70)
    
    # Given parameters
    params = DarcyFlowParameters(
        k=100,          # Permeability: 100 mD
        h=10,           # Thickness: 10 m
        Pe=200,         # Outer boundary pressure: 200 kgf/cm²
        Pwf=150,        # Bottomhole pressure: 150 kgf/cm²
        mu=2.0,         # Viscosity: 2.0 cp
        Bo=1.25,        # Formation volume factor: 1.25
        re=300,         # Drainage radius: 300 m
        rw=0.1,         # Well radius: 0.1 m
        S=5,            # Skin factor: 5 (damaged well)
        unit_system=UnitSystem.METRIC
    )
    
    # Calculate
    calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)
    results = calculator.calculate(params)
    
    # Print results
    calculator.print_results(results)
    
    print("\nInterpretation:")
    print(f"  - The well can produce {results['q']:.2f} m³/day under these conditions")
    print(f"  - Skin factor of {params.S} causes {results['skin_effect_pressure']:.2f} kgf/cm² additional pressure drop")
    print(f"  - Without skin damage, flow rate would be higher")
    
    return results


def example_2_calculate_pressure_field():
    """
    Example 2: Calculate bottomhole pressure given flow rate (FIELD units)
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Calculate Bottomhole Pressure (Field Units)")
    print("="*70)
    
    # Calculate drainage radius from 40-acre spacing
    drainage_area = 40  # acres
    re = calculate_drainage_radius(drainage_area, UnitSystem.FIELD)
    print(f"\nDrainage radius for {drainage_area}-acre spacing: {re:.1f} ft")
    
    # Given parameters
    params = DarcyFlowParameters(
        k=50,           # Permeability: 50 mD
        h=30,           # Thickness: 30 ft
        Pe=3000,        # Outer boundary pressure: 3000 psia
        q=500,          # Desired flow rate: 500 STB/day
        mu=1.5,         # Viscosity: 1.5 cp
        Bo=1.2,         # Formation volume factor: 1.2
        re=re,          # Drainage radius from 40 acres
        rw=0.3,         # Well radius: 0.3 ft (typical 8-inch wellbore)
        S=0,            # No skin (perfect completion)
        unit_system=UnitSystem.FIELD
    )
    
    # Calculate
    calculator = DarcyRadialFlow(unit_system=UnitSystem.FIELD)
    results = calculator.calculate(params)
    
    # Print results
    calculator.print_results(results)
    
    print("\nInterpretation:")
    print(f"  - To produce {params.q:.0f} STB/day, bottomhole pressure must be {results['Pwf']:.1f} psia")
    print(f"  - Pressure drawdown required: {results['dP']:.1f} psi")
    print(f"  - Productivity index: {results['productivity_index']:.2f} STB/day/psi")
    
    return results


def example_3_damaged_vs_stimulated_well():
    """
    Example 3: Compare damaged, ideal, and stimulated wells
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Effect of Skin on Well Performance")
    print("="*70)
    
    # Base parameters
    base_params = {
        'k': 80,
        'h': 15,
        'Pe': 250,
        'Pwf': 180,
        'mu': 2.5,
        'Bo': 1.3,
        're': 400,
        'rw': 0.1,
        'unit_system': UnitSystem.METRIC
    }
    
    calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)
    
    # Three cases: damaged, ideal, stimulated
    cases = [
        ('Damaged Well', 10),      # Positive skin
        ('Ideal Well', 0),         # Zero skin
        ('Stimulated Well', -3)    # Negative skin (acidized/fractured)
    ]
    
    print("\nComparison of well conditions:")
    print("-" * 70)
    
    results_list = []
    for name, skin in cases:
        params = DarcyFlowParameters(**{**base_params, 'S': skin})
        results = calculator.calculate(params)
        results_list.append(results)
        
        print(f"\n{name} (S = {skin}):")
        print(f"  Flow Rate: {results['q']:,.2f} m³/day")
        print(f"  Productivity Index: {results['productivity_index']:.4f} m³/day/(kgf/cm²)")
        print(f"  Skin Pressure Loss: {results['skin_effect_pressure']:.2f} kgf/cm²")
    
    # Calculate improvement factors
    ideal_q = results_list[1]['q']
    damaged_q = results_list[0]['q']
    stimulated_q = results_list[2]['q']
    
    print("\n" + "-" * 70)
    print("Performance Comparison:")
    print(f"  Damaged well produces {(damaged_q/ideal_q - 1)*100:.1f}% less than ideal")
    print(f"  Stimulated well produces {(stimulated_q/ideal_q - 1)*100:.1f}% more than ideal")
    print(f"  Stimulation improvement: {(stimulated_q/damaged_q - 1)*100:.1f}% increase")
    
    return results_list


def example_4_sensitivity_to_permeability():
    """
    Example 4: Sensitivity analysis - effect of permeability
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Sensitivity to Permeability")
    print("="*70)
    
    # Base case
    base_params = DarcyFlowParameters(
        k=100,
        h=20,
        Pe=200,
        Pwf=150,
        mu=2.0,
        Bo=1.25,
        re=300,
        rw=0.1,
        S=2,
        unit_system=UnitSystem.METRIC
    )
    
    # Test range of permeabilities
    k_values = np.linspace(10, 200, 20)  # 10 to 200 mD
    
    calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)
    sensitivity = calculator.sensitivity_analysis(base_params, 'k', k_values)
    
    print("\nPermeability vs Flow Rate:")
    print("-" * 70)
    for k, q in zip(k_values[::4], sensitivity['q'][::4]):  # Print every 4th value
        print(f"  k = {k:6.1f} mD  →  q = {q:8.2f} m³/day")
    
    # Create plot
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Flow rate vs permeability
    ax1.plot(k_values, sensitivity['q'], 'b-', linewidth=2)
    ax1.scatter([base_params.k], [sensitivity['q'][np.argmin(np.abs(k_values - base_params.k))]], 
                color='red', s=100, zorder=5, label='Base Case')
    ax1.set_xlabel('Permeability, k (mD)', fontsize=11)
    ax1.set_ylabel('Flow Rate, q (m³/day)', fontsize=11)
    ax1.set_title('Flow Rate vs Permeability', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Productivity Index vs permeability
    ax2.plot(k_values, sensitivity['PI'], 'g-', linewidth=2)
    ax2.scatter([base_params.k], [sensitivity['PI'][np.argmin(np.abs(k_values - base_params.k))]], 
                color='red', s=100, zorder=5, label='Base Case')
    ax2.set_xlabel('Permeability, k (mD)', fontsize=11)
    ax2.set_ylabel('Productivity Index (m³/day/(kgf/cm²))', fontsize=11)
    ax2.set_title('Productivity Index vs Permeability', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    
    plt.tight_layout()
    plt.savefig('darcy_sensitivity_permeability.png', dpi=300, bbox_inches='tight')
    print("\n✓ Saved plot: darcy_sensitivity_permeability.png")
    
    return sensitivity


def example_5_sensitivity_to_skin():
    """
    Example 5: Sensitivity analysis - effect of skin factor
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Sensitivity to Skin Factor")
    print("="*70)
    
    # Base case
    base_params = DarcyFlowParameters(
        k=100,
        h=20,
        Pe=200,
        Pwf=150,
        mu=2.0,
        Bo=1.25,
        re=300,
        rw=0.1,
        S=0,
        unit_system=UnitSystem.METRIC
    )
    
    # Test range of skin factors
    S_values = np.linspace(-5, 15, 30)  # From -5 (stimulated) to +15 (damaged)
    
    calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)
    sensitivity = calculator.sensitivity_analysis(base_params, 'S', S_values)
    
    print("\nSkin Factor vs Flow Rate:")
    print("-" * 70)
    print("  Negative skin = Stimulated well (fractured, acidized)")
    print("  Zero skin = Ideal well (no damage)")
    print("  Positive skin = Damaged well (drilling damage, scale, etc.)")
    print()
    for s, q in zip(S_values[::6], sensitivity['q'][::6]):
        condition = "Stimulated" if s < 0 else "Ideal" if s == 0 else "Damaged"
        print(f"  S = {s:6.1f} ({condition:11s})  →  q = {q:8.2f} m³/day")
    
    # Create plot
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(S_values, sensitivity['q'], 'b-', linewidth=2)
    ax.axvline(0, color='green', linestyle='--', alpha=0.5, label='Ideal Well (S=0)')
    ax.fill_between(S_values, 0, sensitivity['q'], where=(S_values < 0), 
                     alpha=0.2, color='green', label='Stimulated Zone')
    ax.fill_between(S_values, 0, sensitivity['q'], where=(S_values > 0), 
                     alpha=0.2, color='red', label='Damaged Zone')
    
    ax.set_xlabel('Skin Factor, S (dimensionless)', fontsize=11)
    ax.set_ylabel('Flow Rate, q (m³/day)', fontsize=11)
    ax.set_title('Impact of Skin Factor on Well Performance', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig('darcy_sensitivity_skin.png', dpi=300, bbox_inches='tight')
    print("\n✓ Saved plot: darcy_sensitivity_skin.png")
    
    return sensitivity


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("DARCY RADIAL FLOW - COMPREHENSIVE EXAMPLES")
    print("="*70)
    
    # Run examples
    example_1_calculate_flow_rate_metric()
    example_2_calculate_pressure_field()
    example_3_damaged_vs_stimulated_well()
    example_4_sensitivity_to_permeability()
    example_5_sensitivity_to_skin()
    
    print("\n" + "="*70)
    print("ALL EXAMPLES COMPLETED SUCCESSFULLY")
    print("="*70)
    print("\nGenerated files:")
    print("  - darcy_sensitivity_permeability.png")
    print("  - darcy_sensitivity_skin.png")
    
    # Show plots
    plt.show()


if __name__ == "__main__":
    main()
