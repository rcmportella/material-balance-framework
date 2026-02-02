# Darcy Radial Flow Module

## Overview

This module implements Darcy's Law for radial flow in porous media, allowing calculation of oil flow rates and pressure drawdowns in reservoir systems. It supports both metric and field unit systems.

## Theory

### Radial Flow Equation

The steady-state radial flow equation for oil in porous media is:

**Field Units:**
```
q [STB/day] = 0.007082153 × k[mD] × h[ft] × (Pe - Pwf)[psi]
              ────────────────────────────────────────────
              μ[cp] × Bo × (ln(re/rw) + S)
```

**Metric Units:**
```
q [m³/day] = 0.543439 × k[mD] × h[m] × (Pe - Pwf)[kgf/cm²]
             ──────────────────────────────────────────────
             μ[cp] × Bo × (ln(re/rw) + S)
```

### Parameters

| Parameter | Description | Field Units | Metric Units |
|-----------|-------------|-------------|--------------|
| q | Oil flow rate | STB/day | m³/day |
| k | Permeability | mD | mD |
| h | Net pay thickness | ft | m |
| Pe | Outer boundary pressure | psia | kgf/cm² |
| Pwf | Bottomhole flowing pressure | psia | kgf/cm² |
| μ (mu) | Oil viscosity | cp | cp |
| Bo | Oil formation volume factor | dimensionless | dimensionless |
| re | Drainage radius | ft | m |
| rw | Well radius | ft | m |
| S | Skin factor | dimensionless | dimensionless |

### Skin Factor (S)

The skin factor represents near-wellbore formation damage or stimulation:

- **S > 0**: Formation damage (reduced permeability near wellbore)
  - S = 5-10: Light damage
  - S = 10-20: Moderate damage
  - S > 20: Severe damage

- **S = 0**: Perfect completion (no damage or stimulation)

- **S < 0**: Stimulation (enhanced permeability near wellbore)
  - S = -1 to -3: Acidization
  - S = -4 to -6: Hydraulic fracturing
  - S < -6: Highly fractured

### Productivity Index (PI)

```
PI = q / (Pe - Pwf)
```

Units:
- Field: STB/day/psi
- Metric: m³/day/(kgf/cm²)

## Usage

### Basic Import

```python
from material_balance import DarcyRadialFlow, DarcyFlowParameters, UnitSystem
```

### Example 1: Calculate Flow Rate (Metric Units)

```python
# Define parameters
params = DarcyFlowParameters(
    k=100,          # Permeability: 100 mD
    h=10,           # Thickness: 10 m
    Pe=200,         # Reservoir pressure: 200 kgf/cm²
    Pwf=150,        # Wellbore pressure: 150 kgf/cm²
    mu=2.0,         # Viscosity: 2 cp
    Bo=1.25,        # Formation volume factor: 1.25
    re=300,         # Drainage radius: 300 m
    rw=0.1,         # Well radius: 0.1 m
    S=0,            # No skin
    unit_system=UnitSystem.METRIC
)

# Calculate
calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)
results = calculator.calculate(params)

# Display results
calculator.print_results(results)

# Access specific values
flow_rate = results['q']
drawdown = results['dP']
PI = results['productivity_index']

print(f"Flow rate: {flow_rate:.2f} m³/day")
print(f"Drawdown: {drawdown:.2f} kgf/cm²")
print(f"PI: {PI:.4f} m³/day/(kgf/cm²)")
```

### Example 2: Calculate Bottomhole Pressure (Field Units)

```python
# Define parameters (note: q is given, Pwf will be calculated)
params = DarcyFlowParameters(
    k=50,           # Permeability: 50 mD
    h=30,           # Thickness: 30 ft
    Pe=3000,        # Reservoir pressure: 3000 psia
    q=500,          # Desired flow rate: 500 STB/day
    mu=1.5,         # Viscosity: 1.5 cp
    Bo=1.2,         # Formation volume factor: 1.2
    re=745,         # Drainage radius: 745 ft
    rw=0.3,         # Well radius: 0.3 ft (8-inch wellbore)
    S=0,            # No skin
    unit_system=UnitSystem.FIELD
)

# Calculate
calculator = DarcyRadialFlow(unit_system=UnitSystem.FIELD)
results = calculator.calculate(params)

# Get calculated pressure
Pwf = results['Pwf']
print(f"Required bottomhole pressure: {Pwf:.1f} psia")
```

### Example 3: Calculate Drawdown from Flow Rate

```python
# If you want to find required drawdown without specifying Pe or Pwf
params = DarcyFlowParameters(
    k=100,
    h=15,
    q=1000,         # Desired flow rate
    mu=2.0,
    Bo=1.25,
    re=300,
    rw=0.1,
    S=5,            # Damaged well
    unit_system=UnitSystem.METRIC
)

calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)
results = calculator.calculate(params)

required_drawdown = results['dP']
print(f"Required pressure drawdown: {required_drawdown:.2f} kgf/cm²")
```

### Example 4: Comparing Well Conditions

```python
# Base parameters
base = {
    'k': 80, 'h': 15, 'Pe': 200, 'Pwf': 150,
    'mu': 2.0, 'Bo': 1.25, 're': 300, 'rw': 0.1,
    'unit_system': UnitSystem.METRIC
}

calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)

# Compare different skin values
for name, skin in [('Damaged', 10), ('Ideal', 0), ('Stimulated', -3)]:
    params = DarcyFlowParameters(**{**base, 'S': skin})
    results = calculator.calculate(params)
    print(f"{name:12s} (S={skin:3d}): {results['q']:8.2f} m³/day")
```

### Example 5: Sensitivity Analysis

```python
import numpy as np

# Base parameters
base_params = DarcyFlowParameters(
    k=100, h=20, Pe=200, Pwf=150,
    mu=2.0, Bo=1.25, re=300, rw=0.1, S=0,
    unit_system=UnitSystem.METRIC
)

# Vary permeability
k_values = np.linspace(10, 200, 20)

calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)
sensitivity = calculator.sensitivity_analysis(base_params, 'k', k_values)

# Plot or analyze results
import matplotlib.pyplot as plt
plt.plot(sensitivity['k'], sensitivity['q'])
plt.xlabel('Permeability (mD)')
plt.ylabel('Flow Rate (m³/day)')
plt.show()
```

## Utility Functions

### Calculate Drainage Radius from Area

```python
from material_balance import calculate_drainage_radius, UnitSystem

# Field units (acres to ft)
re_ft = calculate_drainage_radius(40, UnitSystem.FIELD)  # 40-acre spacing
print(f"Drainage radius: {re_ft:.1f} ft")

# Metric units (m² to m)
re_m = calculate_drainage_radius(160000, UnitSystem.METRIC)  # 160,000 m²
print(f"Drainage radius: {re_m:.1f} m")
```

### Calculate Skin Factor from Measurements

```python
from material_balance import calculate_skin_factor

# If you have measured actual drawdown vs theoretical
S = calculate_skin_factor(
    k=100,           # mD
    h=10,            # m
    q=1000,          # m³/day
    dP_actual=60,    # kgf/cm² (measured)
    dP_ideal=45,     # kgf/cm² (calculated with S=0)
    mu=2.0,          # cp
    Bo=1.25,
    re=300,          # m
    rw=0.1,          # m
    unit_system=UnitSystem.METRIC
)

print(f"Calculated skin factor: {S:.2f}")
```

## Complete Workflow Example

```python
from material_balance import (
    DarcyRadialFlow, 
    DarcyFlowParameters, 
    UnitSystem,
    calculate_drainage_radius
)

# Step 1: Calculate drainage radius from well spacing
well_spacing_acres = 40
re = calculate_drainage_radius(well_spacing_acres, UnitSystem.FIELD)
print(f"Drainage radius: {re:.1f} ft")

# Step 2: Define well parameters
params = DarcyFlowParameters(
    k=75,            # From core analysis
    h=25,            # From logs
    Pe=2800,         # From RFT/pressure survey
    q=400,           # Target production rate
    mu=1.8,          # From PVT analysis
    Bo=1.22,         # From PVT analysis
    re=re,           # From step 1
    rw=0.328,        # 8-inch wellbore (4 inch radius)
    S=3,             # Estimated damage
    unit_system=UnitSystem.FIELD
)

# Step 3: Calculate required bottomhole pressure
calculator = DarcyRadialFlow(unit_system=UnitSystem.FIELD)
results = calculator.calculate(params)

# Step 4: Analyze results
print(f"\nTo produce {params.q} STB/day:")
print(f"  Required Pwf: {results['Pwf']:.1f} psia")
print(f"  Drawdown: {results['dP']:.1f} psi")
print(f"  PI: {results['productivity_index']:.3f} STB/day/psi")
print(f"  Skin pressure loss: {results['skin_effect_pressure']:.1f} psi")

# Step 5: Check if stimulation is beneficial
print(f"\nWithout skin (S=0):")
params_ideal = DarcyFlowParameters(**{**params.__dict__, 'S': 0})
results_ideal = calculator.calculate(params_ideal)
print(f"  Flow rate would be: {results_ideal['q']:.1f} STB/day")
print(f"  Increase: {(results_ideal['q']/params.q - 1)*100:.1f}%")
```

## Important Notes

### Input Validation

The module automatically validates:
- All parameters are positive
- re > rw (drainage radius larger than well radius)
- Pe > Pwf (reservoir pressure higher than wellbore pressure)
- Either (Pe and Pwf) or q is specified, but not both

### Unit Consistency

**Critical**: All parameters must use the same unit system. Do not mix field and metric units.

### Assumptions

This implementation assumes:
1. **Steady-state flow** (constant rate and pressures)
2. **Radial flow geometry** (circular drainage area)
3. **Homogeneous reservoir** (uniform properties)
4. **Single-phase oil flow** (no free gas or water)
5. **Slightly compressible fluid** (constant compressibility)
6. **Darcy flow** (laminar, not turbulent)

### Typical Well Parameters

| Parameter | Typical Range |
|-----------|---------------|
| Permeability (k) | 1-1000 mD (oil reservoirs) |
| Thickness (h) | 3-100 m or 10-300 ft |
| Well radius (rw) | 0.1 m or 0.3 ft (typical) |
| Drainage radius (re) | 100-500 m or 300-1500 ft |
| Skin factor (S) | -6 to +20 |
| Viscosity (μ) | 0.5-50 cp (most oils 1-10 cp) |
| FVF (Bo) | 1.0-2.0 |

## Error Handling

```python
try:
    params = DarcyFlowParameters(
        k=100, h=10, Pe=200, Pwf=150,
        mu=2.0, Bo=1.25, re=300, rw=0.1, S=0,
        unit_system=UnitSystem.METRIC
    )
    calculator = DarcyRadialFlow(unit_system=UnitSystem.METRIC)
    results = calculator.calculate(params)
except ValueError as e:
    print(f"Parameter error: {e}")
except Exception as e:
    print(f"Calculation error: {e}")
```

## References

1. Craft, B.C. & Hawkins, M.F. (1991). "Applied Petroleum Reservoir Engineering"
2. Dake, L.P. (1978). "Fundamentals of Reservoir Engineering"
3. Ahmed, T. (2010). "Reservoir Engineering Handbook"
4. Standing, M.B. (1952). "Volumetric and Phase Behavior of Oil Field Hydrocarbon Systems"

## See Also

- [Example: Darcy Flow](../examples/example_darcy_flow.py) - Comprehensive examples
- [Example: Quick Darcy](../examples/quick_darcy_example.py) - Simple usage
- [Material Balance Module](oil_reservoir.py) - STOIIP calculations
- [Unit System Guide](UNIT_SYSTEM_GUIDE.md) - Unit conversion details
