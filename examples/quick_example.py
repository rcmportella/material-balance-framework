"""
Quick Example: Using Both Unit Systems

This script demonstrates the flexibility of the unit system selection feature.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from material_balance import PVTProperties, UnitSystem

# Example 1: Using METRIC units (default)
print("="*60)
print("Example 1: Using METRIC Units (Default)")
print("="*60)

pvt_metric = PVTProperties(
    pressure=[210, 196, 182],     # kgf/cm²
    Bo=[1.25, 1.24, 1.23],        # m³/m³ std
    Rs=[89, 85, 81],              # m³/m³ std
    # unit_system=UnitSystem.METRIC  # Can be omitted (default)
)

print(f"Input pressure: [210, 196, 182] kgf/cm²")
print(f"Internal pressure: {pvt_metric.pressure}")
print(f"✓ No conversion needed (already metric)\n")


# Example 2: Using FIELD units
print("="*60)
print("Example 2: Using FIELD Units")
print("="*60)

pvt_field = PVTProperties(
    pressure=[3000, 2800, 2600],  # psia
    Bo=[1.25, 1.24, 1.23],        # rb/STB
    Rs=[500, 480, 460],            # SCF/STB
    unit_system=UnitSystem.FIELD   # Specify FIELD units
)

print(f"Input pressure: [3000, 2800, 2600] psia")
print(f"Internal pressure: {pvt_field.pressure} kgf/cm²")
print(f"✓ Automatically converted to metric!")
print()
print(f"Input Rs: [500, 480, 460] SCF/STB")
print(f"Internal Rs: {pvt_field.Rs} m³/m³ std")
print(f"✓ Automatically converted to metric!\n")


# Example 3: Compare properties at same pressure
print("="*60)
print("Example 3: Same Reservoir, Different Input Units")
print("="*60)

# 3000 psia = 210.92 kgf/cm²
props_metric = pvt_metric.get_properties_at_pressure(210.92)
props_field = pvt_field.get_properties_at_pressure(210.92)

print("Properties at 210.92 kgf/cm² (3000 psia):")
print(f"  From metric input: Bo = {props_metric['Bo']:.4f} m³/m³ std")
print(f"  From field input:  Bo = {props_field['Bo']:.4f} m³/m³ std")
print(f"  Difference: {abs(props_metric['Bo'] - props_field['Bo']):.6f}")
print(f"✓ Both give the same result!\n")


# Example 4: Unit conversion utility
print("="*60)
print("Example 4: Using UnitConverter Directly")
print("="*60)

from material_balance import UnitConverter

converter = UnitConverter()

# Convert some common values
print("Common conversions:")
print(f"  3000 psia = {converter.pressure_to_metric(3000, UnitSystem.FIELD):.2f} kgf/cm²")
print(f"  1,000,000 STB = {converter.oil_volume_to_metric(1e6, UnitSystem.FIELD):,.0f} m³ std")
print(f"  500 MMSCF = {converter.gas_volume_to_metric(500e6, UnitSystem.FIELD):,.0f} m³ std")
print(f"  180 °F = {converter.temperature_to_kelvin(180, UnitSystem.FIELD):.2f} K")
print(f"  500 SCF/STB = {converter.rs_to_metric(500, UnitSystem.FIELD):.4f} m³/m³ std")

print("\n" + "="*60)
print("KEY TAKEAWAY")
print("="*60)
print("Just add: unit_system=UnitSystem.FIELD")
print("Everything else is handled automatically!")
print("="*60)
