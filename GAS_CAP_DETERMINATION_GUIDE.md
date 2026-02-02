# Gas Cap Size Determination Guide

## Overview

When working with oil reservoirs that have a gas cap, the size of the gas cap (represented by the parameter `m`) is often unknown. The material balance equation can be used to determine this parameter through graphical analysis.

## The Gas Cap Parameter (m)

The parameter `m` represents the ratio of the initial gas cap volume to the initial oil zone volume:

```
m = (G × Bgi) / (N × Boi)
```

Where:
- `G` = Initial gas in place in the gas cap (m³ std)
- `N` = Initial oil in place (m³ std)
- `Bgi` = Initial gas formation volume factor (m³/m³ std)
- `Boi` = Initial oil formation volume factor (m³/m³ std)

## Graphical Method for Determining m

The method is based on plotting the underground withdrawal `F` versus the expansion term `(Eo + m×Eg)` for different values of `m`. The correct value of `m` should produce the straightest line through the data points (highest R² value).

### Mathematical Background

The material balance equation can be rearranged as:

```
F = N × (Eo + m×Eg + Efw)
```

Where:
- `F` = Underground withdrawal (m³)
- `Eo` = Oil expansion term (m³/m³ std)
- `Eg` = Gas cap expansion term (m³/m³ std)
- `Efw` = Water and formation expansion term (m³/m³ std)
- `N` = Initial oil in place (m³ std)

By plotting `F` vs `(Eo + m×Eg)`, we get a straight line with slope `N` if the correct value of `m` is used.

## New Methods in OilReservoir Class

### 1. `plot_gas_cap_determination()`

Creates subplots showing F vs (Eo + m×Eg) for multiple values of m.

**Parameters:**
- `production_data`: ProductionData object with time series
- `m_values`: Array of m values to test (default: 0.1 to 0.9 in steps of 0.1)
- `We_values`: Water influx values (optional)

**Returns:**
- `fig`: Figure object
- `axes`: Array of axes objects
- `r_squared_dict`: Dictionary with R² values for each m

**Example:**
```python
# Test m values from 0.1 to 0.9
m_values = np.arange(0.1, 1.0, 0.1)
fig, axes, r_squared = reservoir.plot_gas_cap_determination(
    production_data=production_data,
    m_values=m_values
)

# Display results
for m, r2 in r_squared.items():
    print(f"m = {m:.1f}: R² = {r2:.6f}")
```

### 2. `determine_optimal_m()`

Automatically finds the optimal m value by testing multiple values and selecting the one with the highest R².

**Parameters:**
- `production_data`: ProductionData object with time series
- `m_values`: Array of m values to test (default: 0.1 to 0.9 in steps of 0.01)
- `We_values`: Water influx values (optional)
- `show_plot`: Whether to display R² vs m plot (default: True)

**Returns:**
- `optimal_m`: The m value with the highest R²
- `results_dict`: Dictionary with all m values and their R² values

**Example:**
```python
# Find optimal m automatically
optimal_m, results = reservoir.determine_optimal_m(
    production_data=production_data,
    m_values=np.arange(0.1, 1.0, 0.01),  # Fine resolution
    show_plot=True
)

print(f"Optimal m = {optimal_m:.3f}")
print(f"R² = {results['optimal_r_squared']:.6f}")
```

## Complete Workflow Example

```python
import numpy as np
from material_balance.oil_reservoir import OilReservoir, ProductionData
from material_balance.pvt_properties import PVTProperties
from material_balance.units import UnitSystem

# 1. Define PVT properties
pvt = PVTProperties(
    pressure=np.array([250, 240, 230, 220, 210]),  # kgf/cm2
    Bo=np.array([1.25, 1.26, 1.27, 1.28, 1.29]),
    Rs=np.array([85, 82, 79, 76, 73]),
    Bg=np.array([0.001, 0.0011, 0.0012, 0.0013, 0.0014]),
    unit_system=UnitSystem.METRIC
)

# 2. Define production data
production_data = ProductionData(
    time=np.array([0, 365, 730, 1095, 1460]),
    Np=np.array([0, 150000, 320000, 510000, 720000]),
    Gp=np.array([0, 13e6, 28e6, 45e6, 64e6]),
    Wp=np.array([0, 5000, 12000, 21000, 32000]),
    pressure=np.array([250, 240, 230, 220, 210]),
    unit_system=UnitSystem.METRIC
)

# 3. Initialize reservoir (m will be determined)
reservoir = OilReservoir(
    pvt_properties=pvt,
    initial_pressure=250.0,
    reservoir_temperature=90.0,
    m=0.0,  # Initial value (will be optimized)
    unit_system=UnitSystem.METRIC
)

# 4. Visual analysis: Test multiple m values
fig1, axes1, r_squared_dict = reservoir.plot_gas_cap_determination(
    production_data=production_data,
    m_values=np.arange(0.1, 1.0, 0.1)
)
plt.savefig('gas_cap_analysis.png')

# 5. Find optimal m automatically
optimal_m, results = reservoir.determine_optimal_m(
    production_data=production_data,
    show_plot=True
)

# 6. Recalculate with optimal m
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

print(f"Optimal gas cap size: m = {optimal_m:.3f}")
print(f"STOIIP: {stats['mean']:,.0f} m³ std")
```

## Interpretation of Results

### R² Values
- **R² > 0.99**: Excellent fit, high confidence in the m value
- **R² = 0.95-0.99**: Good fit, reasonable confidence
- **R² < 0.95**: Poor fit, may indicate data quality issues or aquifer influx

### Physical Interpretation

If the optimal `m = 0.3`, this means:
- The initial gas cap volume is 30% of the initial oil zone volume
- For every 1 m³ of initial oil reservoir volume, there is 0.3 m³ of gas cap volume

### Common m Values

- **m = 0**: No gas cap (undersaturated reservoir)
- **m = 0.1 - 0.3**: Small gas cap
- **m = 0.3 - 0.7**: Moderate gas cap
- **m > 0.7**: Large gas cap

## Troubleshooting

### All m values give the same R²

This can occur when:
1. The Eg term is very small compared to Eo
2. Insufficient pressure decline in the data
3. The reservoir is primarily undersaturated

**Solution**: Check that your PVT data includes gas properties (Bg) and that there is significant pressure decline.

### Poor R² for all m values

Possible causes:
1. Data quality issues (inconsistent measurements)
2. Aquifer influx not accounted for
3. Reservoir heterogeneity
4. Pressure maintenance operations

**Solution**: 
- Review and validate production data
- Consider aquifer influx using `We_values` parameter
- Check for systematic trends in residuals

## References

- Dake, L.P. (1978). "Fundamentals of Reservoir Engineering"
- Craft, B.C. & Hawkins, M.F. (1991). "Applied Petroleum Reservoir Engineering"
- Ahmed, T. (2010). "Reservoir Engineering Handbook"

## See Also

- [Example: Gas Cap Determination](../examples/example_gas_cap_determination.py)
- [Material Balance Guide](UNIT_SYSTEM_GUIDE.md)
- [Input Files Guide](INPUT_FILES_GUIDE.md)
