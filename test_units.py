"""
Simple test to verify unit system conversions work correctly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from material_balance import UnitSystem, UnitConverter

def test_conversions():
    """Test basic unit conversions"""
    print("Testing Unit Conversions\n" + "="*50)
    
    converter = UnitConverter()
    
    # Test pressure
    psia = 3000
    kgf_cm2 = converter.pressure_to_metric(psia, UnitSystem.FIELD)
    psia_back = converter.pressure_from_metric(kgf_cm2, UnitSystem.FIELD)
    print(f"\nPressure: {psia} psia = {kgf_cm2:.2f} kgf/cm² = {psia_back:.2f} psia")
    assert abs(psia - psia_back) < 0.1, "Pressure conversion failed"
    
    # Test oil volume
    stb = 1000000
    m3 = converter.oil_volume_to_metric(stb, UnitSystem.FIELD)
    stb_back = converter.oil_volume_from_metric(m3, UnitSystem.FIELD)
    print(f"Oil Volume: {stb:,.0f} STB = {m3:,.2f} m³ std = {stb_back:,.0f} STB")
    assert abs(stb - stb_back) < 10, "Oil volume conversion failed"
    
    # Test gas volume
    scf = 500e6
    m3_gas = converter.gas_volume_to_metric(scf, UnitSystem.FIELD)
    scf_back = converter.gas_volume_from_metric(m3_gas, UnitSystem.FIELD)
    print(f"Gas Volume: {scf:,.0f} SCF = {m3_gas:,.2f} m³ std = {scf_back:,.0f} SCF")
    assert abs(scf - scf_back) < 1000, "Gas volume conversion failed"
    
    # Test temperature
    fahrenheit = 180
    kelvin = converter.temperature_to_kelvin(fahrenheit, UnitSystem.FIELD)
    fahrenheit_back = converter.temperature_from_kelvin(kelvin, UnitSystem.FIELD)
    print(f"Temperature: {fahrenheit} °F = {kelvin:.2f} K = {fahrenheit_back:.2f} °F")
    assert abs(fahrenheit - fahrenheit_back) < 0.01, "Temperature conversion failed"
    
    # Test GOR
    scf_stb = 500
    m3_m3 = converter.rs_to_metric(scf_stb, UnitSystem.FIELD)
    scf_stb_back = converter.rs_from_metric(m3_m3, UnitSystem.FIELD)
    print(f"GOR: {scf_stb} SCF/STB = {m3_m3:.4f} m³/m³ std = {scf_stb_back:.2f} SCF/STB")
    assert abs(scf_stb - scf_stb_back) < 0.1, "GOR conversion failed"
    
    # Test Bg
    bg_field = 0.0009  # rb/SCF
    bg_metric = converter.bg_to_metric(bg_field, UnitSystem.FIELD)
    bg_field_back = converter.bg_from_metric(bg_metric, UnitSystem.FIELD)
    print(f"Bg: {bg_field} rb/SCF = {bg_metric:.4f} m³/m³ std = {bg_field_back:.6f} rb/SCF")
    assert abs(bg_field - bg_field_back) < 1e-6, "Bg conversion failed"
    
    # Test compressibility
    comp_psi = 3e-6  # 1/psi
    comp_kgf = converter.compressibility_to_metric(comp_psi, UnitSystem.FIELD)
    comp_psi_back = converter.compressibility_from_metric(comp_kgf, UnitSystem.FIELD)
    print(f"Compressibility: {comp_psi} 1/psi = {comp_kgf:.6e} 1/(kgf/cm²) = {comp_psi_back:.6e} 1/psi")
    assert abs(comp_psi - comp_psi_back) < 1e-9, "Compressibility conversion failed"
    
    print("\n" + "="*50)
    print("✓ All conversion tests passed!")
    return True

def test_pvt_conversion():
    """Test PVT properties with unit conversion"""
    from material_balance import PVTProperties, UnitSystem
    
    print("\n\nTesting PVT Properties Conversion\n" + "="*50)
    
    # Create PVT in field units
    pvt_field = PVTProperties(
        pressure=[3000, 2500, 2000],  # psia
        Bo=[1.25, 1.23, 1.21],        # rb/STB
        Rs=[500, 450, 400],            # SCF/STB
        unit_system=UnitSystem.FIELD
    )
    
    print(f"\nInput (Field Units):")
    print(f"  Pressure: [3000, 2500, 2000] psia")
    print(f"  Bo: [1.25, 1.23, 1.21] rb/STB")
    print(f"  Rs: [500, 450, 400] SCF/STB")
    
    print(f"\nConverted to Internal (Metric Units):")
    print(f"  Pressure: [{pvt_field.pressure[0]:.2f}, {pvt_field.pressure[1]:.2f}, {pvt_field.pressure[2]:.2f}] kgf/cm²")
    print(f"  Bo: [{pvt_field.Bo[0]:.2f}, {pvt_field.Bo[1]:.2f}, {pvt_field.Bo[2]:.2f}] m³/m³ std")
    print(f"  Rs: [{pvt_field.Rs[0]:.4f}, {pvt_field.Rs[1]:.4f}, {pvt_field.Rs[2]:.4f}] m³/m³ std")
    
    # Verify conversions
    expected_pressure = [210.92, 175.77, 140.61]
    expected_rs = [89.05, 80.15, 71.24]  # Corrected values
    
    for i in range(3):
        assert abs(pvt_field.pressure[i] - expected_pressure[i]) < 0.1, f"Pressure conversion failed at index {i}"
        assert abs(pvt_field.Rs[i] - expected_rs[i]) < 0.1, f"Rs conversion failed at index {i}"
    
    print("\n✓ PVT conversion test passed!")
    return True

if __name__ == "__main__":
    try:
        test_conversions()
        test_pvt_conversion()
        print("\n" + "="*50)
        print("ALL TESTS PASSED! ✓")
        print("="*50)
        print("\nUnit system selection is working correctly.")
        print("You can now use both FIELD and METRIC units in your calculations!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
